#!/usr/bin/env python3
"""
Cycle through known crAPI users:
  login → get vehicle location → logout (discard token) → next user
Repeat the full cycle 10 times.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests
import yaml


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def login(base_url: str, email: str, password: str) -> Optional[str]:
    url = f"{base_url.rstrip('/')}/identity/api/auth/login"
    payload = {"email": email, "password": password}
    try:
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        token = data.get("token") or data.get("access_token")
        if not token:
            print(f"  [!] Login succeeded but no token found in response: {data}")
            return None
        return token
    except requests.RequestException as e:
        print(f"  [!] Login failed for {email}: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"      Response: {e.response.text[:300]}")
            except Exception:
                pass
        return None


def get_vehicles(base_url: str, token: str) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/identity/api/v2/vehicle/vehicles"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("vehicles") or data.get("data") or []
        return []
    except requests.RequestException as e:
        print(f"  [!] Failed to fetch vehicles: {e}")
        return []


def get_location(base_url: str, token: str, vehicle_id: str) -> Optional[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/identity/api/v2/vehicle/{vehicle_id}/location"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"  [!] Failed to fetch location for vehicle {vehicle_id}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Cycle through crAPI users and print their vehicle locations"
    )
    parser.add_argument(
        "--config",
        default="crapi_config.yaml",
        help="Path to config file (default: crapi_config.yaml)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of full cycles through all users (default: 1)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay (seconds) between requests (default: 0.5)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(config_path)

    base_url = cfg["target"]["base_url"]
    num_users = cfg["known_users"]["num_users"]
    emails = [f"mike{i}@my.lab" for i in range(1, num_users + 1)]
    password = cfg["known_users"]["password"]

    print(f"Target : {base_url}")
    print(f"Users  : {len(emails)}")
    print(f"Cycles : {args.cycles}")
    print("-" * 60)

    for cycle in range(1, args.cycles + 1):
        print(f"\n=== Cycle {cycle}/{args.cycles} ===")
        for email in emails:
            print(f"\nUser: {email}")

            token = login(base_url, email, password)
            if not token:
                print("  Skipping (login failed)")
                continue

            vehicles = get_vehicles(base_url, token)
            if not vehicles:
                print("  No vehicles found for this user")
                continue

            vehicle = vehicles[0]
            vehicle_id = vehicle.get("uuid") or vehicle.get("id") or vehicle.get("vehicleId")
            if not vehicle_id:
                print(f"  Could not extract vehicle ID from: {vehicle}")
                continue

            loc = get_location(base_url, token, vehicle_id)
            if loc:
                lat = lon = None
                if "vehicleLocation" in loc:
                    vl = loc["vehicleLocation"]
                    lat = vl.get("latitude")
                    lon = vl.get("longitude")
                else:
                    lat = loc.get("latitude")
                    lon = loc.get("longitude")

                print(f"  Vehicle : {vehicle_id}")
                print(f"  Location: lat={lat}, lon={lon}")
                if "fullName" in loc:
                    print(f"  Name    : {loc['fullName']}")
            else:
                print("  Location lookup failed")

            time.sleep(args.delay)

    print("\nDone.")


if __name__ == "__main__":
    main()
