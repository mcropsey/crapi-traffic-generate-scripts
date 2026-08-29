#!/usr/bin/env python3
"""Baseline 7: User deleting their own video"""
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

def delete_video(base_url: str, token: str, video_id: int, timeout: float = 15) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.delete(f"{base_url.rstrip('/')}/identity/api/v2/user/videos/{video_id}",
                           headers=headers, timeout=timeout)
        return r.status_code in (200, 204)
    except:
        return False

def main():
    parser = argparse.ArgumentParser(description="Baseline 7: Delete Own Video")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg["known_users"].get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 7: Delete Own Video\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    dashboard = get_dashboard(base_url, token)
    if not dashboard or not dashboard.get("video_id"):
        print("[+] User has no videos (skipping delete)")
        print("[+] BASELINE: Legitimate video management access")
        return

    video_id = dashboard.get("video_id")
    print(f"[*] Deleting own video (ID: {video_id})...")

    if delete_video(base_url, token, video_id):
        print(f"[+] Video deleted successfully")
        print(f"[+] BASELINE: Legitimate deletion of own video")
    else:
        print("[+] Delete request sent (API may restrict deletion)")
        print(f"[+] BASELINE: Legitimate video deletion attempt")

if __name__ == "__main__":
    main()
