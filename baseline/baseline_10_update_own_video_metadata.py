#!/usr/bin/env python3
"""Baseline 10: Normal update of own video metadata"""
import argparse, sys, time, random
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests, yaml

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def login(base_url: str, email: str, password: str, timeout: float = 15) -> Optional[str]:
    try:
        r = requests.post(f"{base_url.rstrip('/')}/identity/api/auth/login",
                         json={"email": email, "password": password}, timeout=timeout)
        return r.json().get("token") or r.json().get("access_token")
    except:
        return None

def get_dashboard(base_url: str, token: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        return requests.get(f"{base_url.rstrip('/')}/identity/api/v2/user/dashboard",
                           headers=headers, timeout=timeout).json()
    except:
        return None

def update_video_metadata(base_url: str, token: str, video_name: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"video_name": video_name}
    try:
        return requests.put(f"{base_url.rstrip('/')}/identity/api/v2/user/video_name",
                           json=payload, headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Baseline 10: Update Own Video Metadata")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg.get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 10: Update Own Video Metadata\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    dashboard = get_dashboard(base_url, token)
    if not dashboard or not dashboard.get("video_id"):
        print("[+] User has no videos (skipping update)")
        print("[+] BASELINE: Legitimate video metadata access")
        return

    new_name = f"My Video {random.randint(1, 999)}"
    print(f"[*] Updating video metadata to: {new_name}")
    result = update_video_metadata(base_url, token, new_name)
    if result:
        print(f"[+] Video metadata updated successfully")
        print(f"[+] BASELINE: Legitimate update of own video metadata")
    else:
        print("[!] Update failed")

if __name__ == "__main__":
    main()
