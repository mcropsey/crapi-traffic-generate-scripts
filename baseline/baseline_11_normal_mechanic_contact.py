#!/usr/bin/env python3
"""Baseline 11: Normal mechanic contact with legitimate internal API"""
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

def get_vehicles(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/identity/api/v2/vehicle/vehicles",
                        headers=headers, timeout=timeout).json()
        return r if isinstance(r, list) else r.get("vehicles") or []
    except:
        return []

def contact_mechanic(base_url: str, token: str, vin: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"vin": vin, "mechanic_api": "http://localhost:3030"}
    try:
        return requests.post(f"{base_url.rstrip('/')}/workshop/api/mechanic/contact_mechanic",
                            json=payload, headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Baseline 11: Normal Mechanic Contact")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg["known_users"].get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 11: Normal Mechanic Contact\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    vehicles = get_vehicles(base_url, token)
    if not vehicles:
        print("[!] No vehicles found"); sys.exit(1)
    vehicle = vehicles[0]
    vin = vehicle.get("vin")
    print(f"[+] Using vehicle VIN: {vin}")

    print(f"[*] Contacting mechanic (legitimate internal API)...")
    result = contact_mechanic(base_url, token, vin)
    if result:
        print(f"[+] SUCCESS! Mechanic contacted")
        print(f"[+] BASELINE: Legitimate mechanic contact with internal API")
    else:
        print("[!] Contact failed")

if __name__ == "__main__":
    main()
