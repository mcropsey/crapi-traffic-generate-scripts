#!/usr/bin/env python3
"""Baseline 9: Normal small purchase"""
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

def get_products(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/workshop/api/shop/products",
                        headers=headers, timeout=timeout).json()
        return r.get("products") or []
    except:
        return []

def place_order(base_url: str, token: str, product_id: int, quantity: int, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"product_id": product_id, "quantity": quantity}
    try:
        return requests.post(f"{base_url.rstrip('/')}/workshop/api/shop/orders",
                            json=payload, headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Baseline 9: Small Purchase")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg["known_users"].get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 9: Small Purchase\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    products = get_products(base_url, token)
    if not products:
        print("[!] No products found"); sys.exit(1)

    product = random.choice(products)
    product_id = product.get("id")
    quantity = 1
    print(f"[*] Placing small order: {product.get('name')} x{quantity}")

    order = place_order(base_url, token, product_id, quantity)
    if order:
        print(f"[+] Order placed successfully")
        print(f"[+] BASELINE: Legitimate small purchase")
    else:
        print("[!] Order failed")

if __name__ == "__main__":
    main()
