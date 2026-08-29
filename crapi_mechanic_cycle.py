#!/usr/bin/env python3
"""
Generate NORMAL traffic for crAPI Challenge 2 (mechanic reports).

Flow per user (repeated for N cycles):
  1. Login
  2. Get own vehicles → extract VIN
  3. List mechanics
  4. POST /workshop/api/merchant/contact_mechanic  (legitimate service request)
  5. GET  /workshop/api/mechanic/mechanic_report?report_id=<own_id>  (only own report)
  6. Discard token

This teaches an API security solution the expected behaviour so that
changing report_id to other users’ IDs later stands out as abnormal.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

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
        token = data.get("token") or data.get("access_token")
        if not token:
            print(f"  [!] Login OK but no token: {data}")
            return None
        return token
    except requests.RequestException as e:
        print(f"  [!] Login failed for {email}: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"      {e.response.text[:250]}")
            except Exception:
                pass
        return None


def get_vehicles(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/identity/api/v2/vehicle/vehicles"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("vehicles") or data.get("data") or []
        return []
    except requests.RequestException as e:
        print(f"  [!] get_vehicles failed: {e}")
        return []


def get_mechanics(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    """GET /workshop/api/mechanic/  – list available mechanics."""
    url = f"{base_url.rstrip('/')}/workshop/api/mechanic/"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("mechanics") or []
    except requests.RequestException as e:
        print(f"  [!] get_mechanics failed: {e}")
        return []


def contact_mechanic(
    base_url: str,
    token: str,
    vin: str,
    mechanic_code: str,
    problem_details: str,
    timeout: float = 15,
) -> Optional[Dict[str, Any]]:
    """
    POST /workshop/api/merchant/contact_mechanic
    Returns the response that contains report_link / id.
    """
    url = f"{base_url.rstrip('/')}/workshop/api/merchant/contact_mechanic"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    # Use the same host the base_url points to for the callback
    parsed = urlparse(base_url)
    mechanic_api = f"{parsed.scheme}://{parsed.netloc}/workshop/api/mechanic/receive_report"

    payload = {
        "mechanic_api": mechanic_api,
        "mechanic_code": mechanic_code,
        "number_of_repeats": 1,
        "problem_details": problem_details,
        "repeat_request_if_failed": False,
        "vin": vin,
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"  [!] contact_mechanic failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"      {e.response.text[:300]}")
            except Exception:
                pass
        return None


def get_own_report(base_url: str, token: str, report_id: int, timeout: float = 15) -> Optional[Dict[str, Any]]:
    """GET /workshop/api/mechanic/mechanic_report?report_id=<own_id> – only own report."""
    url = f"{base_url.rstrip('/')}/workshop/api/mechanic/mechanic_report"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"report_id": report_id}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"  [!] get_own_report({report_id}) failed: {e}")
        return None


def extract_report_id(contact_resp: Dict[str, Any]) -> Optional[int]:
    """Pull the report id from the contact_mechanic response."""
    if not contact_resp:
        return None
    # Common shapes
    rfm = contact_resp.get("response_from_mechanic_api") or {}
    rid = rfm.get("id")
    if rid is not None:
        return int(rid)

    # Fallback: parse report_link query string
    link = rfm.get("report_link") or contact_resp.get("report_link")
    if link:
        qs = parse_qs(urlparse(link).query)
        if "report_id" in qs:
            return int(qs["report_id"][0])
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate normal (legitimate) mechanic-report traffic for crAPI Challenge 2"
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
        help="Number of full cycles through all known users (default: 1)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.7,
        help="Delay (seconds) between major steps (default: 0.7)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=12.0,
        help="HTTP timeout in seconds (default: 12)",
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

    print(f"Target  : {base_url}")
    print(f"Users   : {len(emails)}")
    print(f"Cycles  : {args.cycles}")
    print(f"Purpose : NORMAL traffic only (own report_id)")
    print("-" * 60)

    problem_templates = [
        "Brake pads are squeaking, please inspect.",
        "Oil change and filter replacement needed.",
        "Check engine light is on intermittently.",
        "AC is blowing warm air only.",
        "Strange vibration at highway speeds.",
        "Wipers leave streaks, need replacement.",
        "Battery seems weak on cold starts.",
        "Tire pressure warning keeps appearing.",
    ]

    for cycle in range(1, args.cycles + 1):
        print(f"\n=== Cycle {cycle}/{args.cycles} ===")
        for idx, email in enumerate(emails):
            print(f"\nUser: {email}")

            # 1. Login
            token = login(base_url, email, password, timeout=args.timeout)
            if not token:
                print("  Skipping (login failed)")
                continue
            time.sleep(args.delay * 0.4)

            # 2. Own vehicles → VIN
            vehicles = get_vehicles(base_url, token, timeout=args.timeout)
            if not vehicles:
                print("  No vehicles – skipping contact mechanic")
                continue
            vehicle = vehicles[0]
            vin = vehicle.get("vin")
            if not vin:
                print(f"  No VIN found in vehicle object: {list(vehicle.keys())}")
                continue
            print(f"  VIN     : {vin}")
            time.sleep(args.delay * 0.3)

            # 3. List mechanics (normal browsing behaviour)
            mechanics = get_mechanics(base_url, token, timeout=args.timeout)
            if not mechanics:
                print("  No mechanics returned – using default TRAC_JHN")
                mechanic_code = "TRAC_JHN"
            else:
                # Pick a mechanic deterministically so traffic is repeatable
                mech = mechanics[idx % len(mechanics)]
                mechanic_code = mech.get("mechanic_code") or "TRAC_JHN"
                print(f"  Mechanic: {mechanic_code}")
            time.sleep(args.delay * 0.3)

            # 4. Submit legitimate contact-mechanic request
            problem = problem_templates[(cycle + idx) % len(problem_templates)]
            contact_resp = contact_mechanic(
                base_url, token, vin, mechanic_code, problem, timeout=args.timeout
            )
            if not contact_resp:
                print("  contact_mechanic failed – skipping report fetch")
                continue

            report_id = extract_report_id(contact_resp)
            if report_id is None:
                print(f"  Could not extract report_id from: {contact_resp}")
                continue
            print(f"  Created report_id={report_id}")
            time.sleep(args.delay * 0.4)

            # 5. Fetch ONLY the report that belongs to this user
            report = get_own_report(base_url, token, report_id, timeout=args.timeout)
            if report:
                # Just confirm we got something; do not print sensitive data
                status = report.get("status") or report.get("problem_details", "")[:40]
                print(f"  Fetched own report OK (status/snippet: {status})")
            else:
                print("  Failed to fetch own report")

            # 6. Discard token (JWT – just drop it)
            time.sleep(args.delay)

    print("\nDone – normal mechanic-report traffic generated.")


if __name__ == "__main__":
    main()
