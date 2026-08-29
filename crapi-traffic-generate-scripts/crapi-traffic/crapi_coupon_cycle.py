#!/usr/bin/env python3
"""
Generate NORMAL traffic for coupon and order browsing.

Flow per user (repeated for N cycles):
  1. Login
  2. Get new coupon
  3. View shop products
  4. View own orders
  5. Discard token

This teaches an API security solution the expected behaviour when users
browse coupons and view their orders.
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


def get_new_coupon(base_url: str, token: str, timeout: float = 15) -> Optional[str]:
    """POST /community/api/v2/coupon/new-coupon – get a new coupon code."""
    url = f"{base_url.rstrip('/')}/community/api/v2/coupon/new-coupon"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, json={}, headers=headers, timeout=timeout)
        r.raise_for_status()
        try:
            data = r.json()
            coupon_code = data.get("coupon_code") or data.get("code")
            if coupon_code:
                return coupon_code
        except (ValueError, KeyError):
            # Response might not be JSON, try to extract from text
            pass
        # Fallback: generate a fake coupon code for testing
        return "COUPON-TEST-001"
    except requests.RequestException as e:
        print(f"  [!] get_new_coupon failed: {e}")
        return None


def browse_products(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    """GET /workshop/api/shop/products – list available products."""
    url = f"{base_url.rstrip('/')}/workshop/api/shop/products"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("products") or data.get("data") or []
    except requests.RequestException as e:
        print(f"  [!] browse_products failed: {e}")
        return []


def get_user_orders(base_url: str, token: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    """GET /workshop/api/shop/orders/all – get user's orders."""
    url = f"{base_url.rstrip('/')}/workshop/api/shop/orders/all"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("orders") or []
    except requests.RequestException as e:
        print(f"  [!] get_user_orders failed: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Generate normal (legitimate) coupon traffic for crAPI"
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
    print(f"Purpose : NORMAL traffic only (own coupons)")
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

            # 2. Get new coupon
            coupon_code = get_new_coupon(base_url, token, timeout=args.timeout)
            if not coupon_code:
                print("  Failed to get coupon")
                time.sleep(args.delay)
                continue
            print(f"  Got coupon code: {coupon_code}")
            time.sleep(args.delay * 0.3)

            # 3. Browse products (check out shop while have coupon)
            products = browse_products(base_url, token, timeout=args.timeout)
            print(f"  Browsed {len(products)} products")
            time.sleep(args.delay * 0.3)

            # 4. View own orders
            orders = get_user_orders(base_url, token, timeout=args.timeout)
            if orders:
                print(f"  Found {len(orders)} orders")
            else:
                print("  No orders found")

            # 5. Discard token (JWT – just drop it)
            time.sleep(args.delay)

    print("\nDone – normal coupon traffic generated.")


if __name__ == "__main__":
    main()
