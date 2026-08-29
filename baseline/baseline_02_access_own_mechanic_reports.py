#!/usr/bin/env python3
"""Baseline 2: User accessing their own mechanic reports"""
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

def get_own_reports(base_url: str, token: str, timeout: float = 15) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/workshop/api/mechanic/mechanic_report",
                        headers=headers, timeout=timeout).json()
        return r.get("reports") or []
    except:
        return []

def main():
    parser = argparse.ArgumentParser(description="Baseline 2: Access Own Mechanic Reports")
    parser.add_argument("--config", default="../crapi_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]
    num_users = cfg.get("num_users", 50)

    user_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[*] Baseline 2: Access Own Mechanic Reports\n[*] Target: {base_url}\n" + "-"*60)
    print(f"[+] User: {user_email}")

    token = login(base_url, user_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    print(f"[*] Fetching own mechanic reports...")
    reports = get_own_reports(base_url, token)
    if reports:
        print(f"[+] Found {len(reports)} report(s)")
        for report in reports[:3]:
            print(f"  - Report ID: {report.get('id')}, Status: {report.get('status')}")
        print(f"[+] BASELINE: Legitimate access to own reports")
    else:
        print(f"[+] No reports found (user may not have created any)")

if __name__ == "__main__":
    main()
