#!/usr/bin/env python3
"""Baseline 3: Normal login process"""
import argparse, sys, time, random
from pathlib import Path
from typing import Optional
import requests, yaml

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def login(base_url: str, email: str, password: str, timeout: float = 15) -> Optional[str]:
    try:
        r = requests.post(f"{base_url.rstrip('/')}/identity/api/auth/login",
                         json={"email": email, "password": password}, timeout=timeout)
        r.raise_for_status()
        return r.json().get("token") or r.json().get("access_token")
    except:
        return None

def get_dashboard(base_url: str, token: str, timeout: float = 15) -> Optional[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        return requests.get(f"{base_url.rstrip('/')}/identity/api/v2/user/dashboard",
                           headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Baseline 3: Normal Login")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg.get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 3: Normal Login\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    print(f"[*] Performing normal login...")
    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Login successful")
    time.sleep(0.5)

    print(f"[*] Accessing dashboard...")
    dashboard = get_dashboard(base_url, token)
    if dashboard:
        print(f"[+] Dashboard retrieved: {dashboard.get('name')}")
        print(f"[+] Email: {dashboard.get('email')}")
        print(f"[+] Role: {dashboard.get('role')}")
        print(f"[+] BASELINE: Legitimate login and dashboard access")
    else:
        print("[!] Dashboard access failed")

if __name__ == "__main__":
    main()
