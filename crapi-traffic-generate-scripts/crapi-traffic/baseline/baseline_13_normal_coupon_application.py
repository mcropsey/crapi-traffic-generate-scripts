#!/usr/bin/env python3
"""Baseline 13: Normal coupon application"""
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

def get_orders(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/workshop/api/shop/orders",
                        headers=headers, timeout=timeout).json()
        return r.get("orders") or []
    except:
        return []

def apply_coupon(base_url: str, token: str, coupon_code: str, order_id: int, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"coupon_code": coupon_code, "order_id": order_id}
    try:
        return requests.post(f"{base_url.rstrip('/')}/workshop/api/shop/apply_coupon",
                            json=payload, headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Baseline 13: Normal Coupon Application")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg.get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 13: Normal Coupon Application\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    orders = get_orders(base_url, token)
    if not orders:
        print("[!] No orders found"); sys.exit(1)

    order = orders[0]
    order_id = order.get("id")
    coupon_code = "TRAC075"
    print(f"[*] Applying coupon {coupon_code} to order {order_id}")

    result = apply_coupon(base_url, token, coupon_code, order_id)
    if result:
        if "error" not in result.get("message", "").lower():
            print(f"[+] Coupon applied successfully")
            print(f"[+] BASELINE: Legitimate coupon application")
        else:
            print(f"[*] Coupon application failed: {result.get('message')}")
    else:
        print("[!] Request failed")

if __name__ == "__main__":
    main()
