#!/usr/bin/env python3
"""Baseline 14: Authenticated access to orders"""
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

def get_order_details(base_url: str, token: str, order_id: int, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/workshop/api/shop/orders/{order_id}",
                        headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Baseline 14: Authenticated Order Access")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg.get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 14: Authenticated Order Access\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    print(f"[*] Accessing own orders (authenticated)...")
    orders = get_orders(base_url, token)
    if orders:
        print(f"[+] Retrieved {len(orders)} order(s)")
        order = orders[0]
        order_id = order.get("id")
        print(f"[*] Getting details for order {order_id}...")
        details = get_order_details(base_url, token, order_id)
        if details:
            print(f"[+] Order details retrieved")
            print(f"[+] BASELINE: Legitimate authenticated order access")
        else:
            print("[!] Could not retrieve order details")
    else:
        print("[!] No orders found")

if __name__ == "__main__":
    main()
