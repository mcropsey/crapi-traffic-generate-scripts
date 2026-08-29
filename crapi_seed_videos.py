#!/usr/bin/env python3
"""Seed crAPI with videos for users"""
import sys, time, random
from pathlib import Path
from typing import Optional
import requests, yaml

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def login(base_url: str, email: str, password: str, timeout: float = 15) -> Optional[str]:
    try:
        r = requests.post(f"{base_url.rstrip('/')}/identity/api/auth/login",
                         json={"email": email, "password": password}, timeout=timeout)
        return r.json().get("token") or r.json().get("access_token")
    except Exception as e:
        return None

def upload_video(base_url: str, token: str, video_name: str, timeout: float = 15) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    # Create a dummy video file content
    video_content = b"fake video content for testing"
    files = {"file": (f"{video_name}.mp4", video_content)}
    data = {"video_name": video_name}
    try:
        r = requests.post(f"{base_url.rstrip('/')}/identity/api/v2/user/videos",
                         files=files, data=data, headers=headers, timeout=timeout)
        if r.status_code in (200, 201):
            return True
        else:
            return False
    except Exception as e:
        return False

def main():
    config_path = Path("./crapi_config.yaml")
    if not config_path.exists():
        print("[!] Config file not found"); sys.exit(1)

    cfg = load_config(config_path)
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg.get("num_users", 50)

    print(f"[*] Seeding videos for {num_users} users")
    print(f"[*] Target: {base_url}\n")

    success_count = 0
    for i in range(1, num_users + 1):
        email = f"mike{i}@my.lab"
        print(f"[{i:02d}] {email}: ", end="", flush=True)

        token = login(base_url, email, password)
        if not token:
            print("LOGIN FAILED")
            continue

        video_name = f"My Video {i}"

        if upload_video(base_url, token, video_name):
            print("✓ Video created")
            success_count += 1
        else:
            print("✗ Video upload failed")

        time.sleep(0.3)

    print(f"\n[+] Created {success_count}/{num_users} videos")

if __name__ == "__main__":
    main()
