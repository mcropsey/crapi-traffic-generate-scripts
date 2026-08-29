#!/usr/bin/env python3
"""
Generate NORMAL traffic for user dashboard and profile access.

Flow per user (repeated for N cycles):
  1. Login
  2. View user dashboard
  3. View user profile pictures
  4. Discard token

This teaches an API security solution the expected behaviour when users
access their personal dashboard and profile information.
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


def get_dashboard(base_url: str, token: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    """GET /identity/api/v2/user/dashboard – get user dashboard."""
    url = f"{base_url.rstrip('/')}/identity/api/v2/user/dashboard"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"  [!] get_dashboard failed: {e}")
        return None


def check_email_verification(base_url: str, token: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    """GET /identity/api/v2/user/verify-email-token – check email verification status."""
    url = f"{base_url.rstrip('/')}/identity/api/v2/user/verify-email-token"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        # This endpoint might not exist, just skip
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate normal (legitimate) dashboard and video traffic for crAPI"
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
    print(f"Purpose : NORMAL traffic only (own dashboard & videos)")
    print("-" * 60)

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

            # 2. View dashboard
            dashboard = get_dashboard(base_url, token, timeout=args.timeout)
            if dashboard:
                profile_name = dashboard.get("name") or dashboard.get("email", "")[:20]
                print(f"  Dashboard loaded for {profile_name}")
            else:
                print("  Failed to load dashboard")
            time.sleep(args.delay * 0.3)

            # 3. Check email verification (simulates user checking account status)
            verify_status = check_email_verification(base_url, token, timeout=args.timeout)
            if verify_status:
                print(f"  Email verification checked")
            else:
                print("  Verified email status or not available")

            # 5. Discard token (JWT – just drop it)
            time.sleep(args.delay)

    print("\nDone – normal dashboard and video traffic generated.")


if __name__ == "__main__":
    main()
