#!/usr/bin/env python3
"""Baseline 1: User accessing their own vehicle location"""
import argparse, sys, time, random
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests, yaml

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def login(base_url: str, email: str, password: str, timeout: float = 15) -> Optional[str]:
    url = f"{base_url.rstrip('/')}/identity/api/auth/login"
    try:
        r = requests.post(url, json={"email": email, "password": password}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("token") or data.get("access_token")
    except:
        return None

def get_own_vehicles(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/identity/api/v2/vehicle/vehicles"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout).json()
        return r if isinstance(r, list) else r.get("vehicles") or []
    except:
        return []

def get_vehicle_location(base_url: str, token: str, vehicle_id: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/identity/api/v2/vehicle/{vehicle_id}/location"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        return requests.get(url, headers=headers, timeout=timeout).json()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description="Baseline 1: Access Own Vehicle Location")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg["known_users"].get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 1: Access Own Vehicle Location\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    vehicles = get_own_vehicles(base_url, token)
    if not vehicles:
        print("[!] No vehicles found"); sys.exit(1)
    print(f"[+] Found {len(vehicles)} vehicle(s)")

    vehicle = vehicles[0]
    vehicle_id = vehicle.get("id")
    print(f"[*] Accessing own vehicle location...")
    loc = get_vehicle_location(base_url, token, vehicle_id)
    if loc:
        vl = loc.get("vehicleLocation", {})
        print(f"[+] SUCCESS! Own location: lat={vl.get('latitude')}, lon={vl.get('longitude')}")
        print(f"[+] BASELINE: Legitimate access to own vehicle location")

if __name__ == "__main__":
    main()
