#!/usr/bin/env python3
"""Baseline 12: Normal coupon validation"""
import argparse, sys, time, random
from pathlib import Path
from typing import Optional, Dict, Any
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

def validate_coupon(base_url: str, token: str, coupon_code: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"coupon_code": coupon_code}
    try:
        return requests.post(f"{base_url.rstrip('/')}/workshop/api/shop/validate_coupon",
                            json=payload, headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Baseline 12: Normal Coupon Validation")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg.get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 12: Normal Coupon Validation\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    coupon_code = "TRAC075"
    print(f"[*] Validating coupon: {coupon_code}")
    result = validate_coupon(base_url, token, coupon_code)
    if result:
        if "error" not in result.get("message", "").lower():
            print(f"[+] Coupon validation successful")
            print(f"[+] Discount amount: {result.get('amount')}")
            print(f"[+] BASELINE: Legitimate coupon validation")
        else:
            print(f"[*] Coupon invalid: {result.get('message')}")
    else:
        print("[!] Validation failed")

if __name__ == "__main__":
    main()
