#!/usr/bin/env python3
"""
Generate NORMAL traffic for community posts interaction.

Flow per user (repeated for N cycles):
  1. Login
  2. List recent community posts
  3. View own posts
  4. Comment on own post
  5. Discard token

This teaches an API security solution the expected behaviour when users
browse and interact with community posts.
"""

import argparse
import sys
import time
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
        token = data.get("token") or data.get("access_token")
        if not token:
            print(f"  [!] Login OK but no token: {data}")
            return None
        return token
    except requests.RequestException as e:
        print(f"  [!] Login failed for {email}: {e}")
        return None


def get_recent_posts(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    """GET /community/api/v2/community/posts/recent – list recent posts."""
    url = f"{base_url.rstrip('/')}/community/api/v2/community/posts/recent"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("posts") or data.get("data") or []
    except requests.RequestException as e:
        print(f"  [!] get_recent_posts failed: {e}")
        return []


def get_user_posts_from_recent(posts: List[Dict[str, Any]], author_email: str) -> List[Dict[str, Any]]:
    """Filter recent posts to find ones by the current user."""
    user_posts = []
    for post in posts:
        author = post.get("author") or {}
        if author.get("email") == author_email:
            user_posts.append(post)
    return user_posts


def comment_on_post(base_url: str, token: str, post_id: int, comment: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    """POST /community/api/v2/community/posts/{postId}/comment – comment on own post."""
    url = f"{base_url.rstrip('/')}/community/api/v2/community/posts/{post_id}/comment"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"body": comment}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"  [!] comment_on_post({post_id}) failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate normal (legitimate) community posts traffic for crAPI"
    )
    parser.add_argument(
        "--config",
        default="crapi_config.yaml",
        help="Path to config file (default: crapi_config.yaml)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of full cycles through all known users (default: 1)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.7,
        help="Delay (seconds) between major steps (default: 0.7)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=12.0,
        help="HTTP timeout in seconds (default: 12)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(config_path)
    base_url = cfg["target"]["base_url"]
    num_users = cfg["known_users"]["num_users"]
    emails = [f"mike{i}@my.lab" for i in range(1, num_users + 1)]
    password = cfg["known_users"]["password"]

    print(f"Target  : {base_url}")
    print(f"Users   : {len(emails)}")
    print(f"Cycles  : {args.cycles}")
    print(f"Purpose : NORMAL traffic only (own posts)")
    print("-" * 60)

    comments = [
        "Great post! Really helpful.",
        "Thanks for sharing this.",
        "Interesting perspective.",
        "This is exactly what I was looking for.",
        "Totally agree with this.",
    ]

    for cycle in range(1, args.cycles + 1):
        print(f"\n=== Cycle {cycle}/{args.cycles} ===")
        for idx, email in enumerate(emails):
            print(f"\nUser: {email}")

            # 1. Login
            token = login(base_url, email, password, timeout=args.timeout)
            if not token:
                print("  Skipping (login failed)")
                continue
            time.sleep(args.delay * 0.4)

            # 2. Browse recent posts (normal community behaviour)
            recent = get_recent_posts(base_url, token, timeout=args.timeout)
            print(f"  Viewed {len(recent)} recent posts")
            time.sleep(args.delay * 0.3)

            # 3. Filter recent posts to find own posts
            own_posts = get_user_posts_from_recent(recent, email)
            if not own_posts:
                print("  No posts created by this user in recent posts")
                time.sleep(args.delay)
                continue
            print(f"  Found {len(own_posts)} own posts in recent")
            time.sleep(args.delay * 0.3)

            # 4. Comment on first own post
            post = own_posts[0]
            post_id = post.get("id")
            if post_id:
                comment_text = comments[idx % len(comments)]
                comment_result = comment_on_post(base_url, token, post_id, comment_text, timeout=args.timeout)
                if comment_result:
                    print(f"  Commented on own post {post_id}")
                else:
                    print(f"  Failed to comment on post {post_id}")
            else:
                print("  Could not extract post ID")

            # 5. Discard token (JWT – just drop it)
            time.sleep(args.delay)

    print("\nDone – normal community posts traffic generated.")


if __name__ == "__main__":
    main()
