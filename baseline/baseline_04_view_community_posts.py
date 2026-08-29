#!/usr/bin/env python3
"""Baseline 4: User viewing community posts normally"""
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

def get_community_posts(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/community/api/v2/community/posts/recent"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        return requests.get(url, headers=headers, params={"limit": 50}, timeout=timeout).json().get("posts") or []
    except:
        return []

def main():
    parser = argparse.ArgumentParser(description="Baseline 4: View Community Posts")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg.get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 4: View Community Posts\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    print(f"[*] Fetching community posts...")
    posts = get_community_posts(base_url, token)
    if posts:
        print(f"[+] Retrieved {len(posts)} posts")
        for post in posts[:3]:
            author = post.get("author", {})
            print(f"  - By {author.get('name')}: {post.get('content', '')[:50]}...")
        print(f"[+] BASELINE: Legitimate community post viewing")
    else:
        print(f"[!] No posts retrieved")

if __name__ == "__main__":
    main()
