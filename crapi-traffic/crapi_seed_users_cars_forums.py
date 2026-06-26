#!/usr/bin/env python3
"""
crAPI Seed / Auto-Enroll Script
===============================
Registers the lab users defined in crapi_config.yaml, grabs each user's
VIN/PIN from MailHog, adds their vehicle, and creates a forum post.

Reads its target URLs and shared password from the SAME YAML config as
crapi_traffic.py, so both stay in sync:
    target.base_url        -> crAPI
    target.mailhog_base    -> MailHog
    known_users.emails     -> which users to enroll
    known_users.password   -> shared password

Run:
    python3 crapi_seed_users_cars_forums.py
    python3 crapi_seed_users_cars_forums.py --config other.yaml

Dependencies:  pip install requests pyyaml
"""

import argparse
import os
import re
import sys
import time
import quopri

import requests


# ── Config loading ────────────────────────────────────────────────────────────
def load_config(path):
    try:
        import yaml
    except ImportError:
        sys.exit("Missing dependency. Run:  pip install pyyaml")
    if not os.path.exists(path):
        sys.exit(f"Config file not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def build_users(emails):
    """Derive name/phone for each configured email. The numeric suffix in the
    local part (mike1 -> 1) drives the lab name/phone; falls back to position."""
    users = []
    for pos, email in enumerate(emails, start=1):
        m = re.search(r"(\d+)", email.split("@")[0])
        n = m.group(1) if m else str(pos)
        users.append({
            "name": f"Mike Williams{n}",
            "email": email,
            "phone": f"{n}{n}{n}-{n}{n}{n}-{n}{n}{n}{n}",
        })
    return users


# ── Helpers ───────────────────────────────────────────────────────────────────
def banner(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def fmt_dur(seconds):
    """Human-readable duration, e.g. '4m 12s' / '9s'."""
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def decode_body(raw_data):
    """Decode quoted-printable email and strip HTML tags."""
    try:
        decoded = quopri.decodestring(raw_data.encode()).decode("utf-8", errors="replace")
    except Exception:
        decoded = raw_data
    plain = re.sub(r"<[^>]+>", " ", decoded)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain


def register(user):
    r = requests.post(
        f"{CRAPI_BASE}/identity/api/auth/signup",
        json={
            "name":     user["name"],
            "email":    user["email"],
            "number":   user["phone"],
            "password": PASSWORD,
        },
    )
    print(f"  Register → {r.status_code}: {r.text.strip()}")
    return r.status_code in (200, 201)


def get_vin_and_pin(email, retries=15, delay=4):
    for attempt in range(1, retries + 1):
        print(f"  MailHog attempt {attempt}/{retries}...")
        try:
            r = requests.get(f"{MAILHOG_BASE}/api/v1/messages", timeout=5)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  MailHog error: {e}")
            time.sleep(delay)
            continue

        for msg in (r.json() or []):
            if not isinstance(msg, dict):
                continue
            raw     = msg.get("Raw") or {}
            to_raw  = " ".join(raw.get("To") or [])
            content = msg.get("Content") or {}
            to_hdr  = " ".join((content.get("Headers") or {}).get("To") or [])
            if email.lower() not in (to_raw + " " + to_hdr).lower():
                continue
            plain = decode_body(raw.get("Data") or "")
            vin_match = re.search(r"VIN:\s*([A-HJ-NPR-Z0-9]{17})", plain, re.IGNORECASE)
            pin_match = re.search(r"Pincode:\s*(\d+)", plain, re.IGNORECASE)
            if vin_match and pin_match:
                vin = vin_match.group(1)
                pin = pin_match.group(1)
                print(f"  ✅ VIN: {vin}  PIN: {pin}")
                return vin, pin
            print(f"  Found email but could not parse VIN/PIN: {plain[:200]}")

        print(f"  Email not found yet — waiting {delay}s...")
        time.sleep(delay)

    print(f"  ❌ Could not find VIN/PIN for {email}")
    return None, None


def login(email):
    r = requests.post(
        f"{CRAPI_BASE}/identity/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    print(f"  Login → {r.status_code}")
    if r.status_code != 200:
        print(f"  ❌ Login failed: {r.text}")
        return None
    token = r.json().get("token")
    if not token:
        print("  ❌ No token in response")
        return None
    return token


def add_vehicle(token, vin, pin):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for pin_val in [pin, int(pin)]:
        r = requests.post(
            f"{CRAPI_BASE}/identity/api/v2/vehicle/add_vehicle",
            json={"vin": vin, "pincode": pin_val},
            headers=headers, timeout=10,
        )
        print(f"  Add vehicle → {r.status_code}: {r.text.strip()}")
        if r.status_code in (200, 201):
            print("  ✅ Vehicle added!")
            return True
    print("  ❌ Failed to add vehicle")
    return False


def create_post(token, name):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "title":   f"Sample Post from {name}",
        "content": f"Sample post from {name}",
    }
    r = requests.post(
        f"{CRAPI_BASE}/community/api/v2/community/posts",
        json=payload, headers=headers, timeout=10,
    )
    print(f"  Create post → {r.status_code}: {r.text.strip()}")
    if r.status_code in (200, 201):
        print("  ✅ Post created!")
        return True
    print("  ❌ Failed to create post")
    return False


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="crAPI lab seed/enroll (config-driven)")
    ap.add_argument("--config", default="crapi_config.yaml",
                    help="path to the YAML config file (default: crapi_config.yaml)")
    args = ap.parse_args()
    cfg = load_config(args.config)

    global CRAPI_BASE, MAILHOG_BASE, PASSWORD
    target = cfg.get("target", {}) or {}
    CRAPI_BASE   = str(target.get("base_url", "http://localhost:8888")).rstrip("/")
    MAILHOG_BASE = str(target.get("mailhog_base", "http://localhost:8025")).rstrip("/")

    ku = cfg.get("known_users", {}) or {}
    emails   = ku.get("emails") or [f"mike{i}@my.lab" for i in range(1, 10)]
    PASSWORD = ku.get("password", "Mylab123!")
    users    = build_users(emails)

    banner(f"crAPI Bulk Enroll — {len(users)} users")
    print(f"Config:  {args.config}")
    print(f"Target:  {CRAPI_BASE}")
    print(f"MailHog: {MAILHOG_BASE}")

    start = time.time()
    results = []

    for user in users:
        banner(f"Processing {user['email']}")
        print(f"  Name:  {user['name']}")
        print(f"  Phone: {user['phone']}")

        if not register(user):
            results.append({**user, "vin": "N/A", "pin": "N/A", "post": "❌", "status": "❌ FAILED - registration"})
            continue

        print("  Waiting 3s for welcome email...")
        time.sleep(3)

        vin, pin = get_vin_and_pin(user["email"])
        if not vin:
            results.append({**user, "vin": "N/A", "pin": "N/A", "post": "❌", "status": "❌ FAILED - no VIN/PIN"})
            continue

        token = login(user["email"])
        if not token:
            results.append({**user, "vin": vin, "pin": pin, "post": "❌", "status": "❌ FAILED - login"})
            continue

        vehicle_ok = add_vehicle(token, vin, pin)
        post_ok    = create_post(token, user["name"])

        results.append({
            **user,
            "vin":    vin,
            "pin":    pin,
            "post":   "✅" if post_ok else "❌",
            "status": "✅ SUCCESS" if (vehicle_ok and post_ok) else "⚠️  PARTIAL",
        })

        time.sleep(2)

    banner("Summary")
    print(f"{'Email':<20} {'Name':<20} {'Phone':<15} {'VIN':<20} {'PIN':<6} {'Post':<6} Status")
    print("-" * 110)
    for r in results:
        print(f"{r['email']:<20} {r['name']:<20} {r['phone']:<15} {r['vin']:<20} {r['pin']:<6} {r['post']:<6} {r['status']}")

    total = time.time() - start
    print(f"\nTotal run time: {fmt_dur(total)} ({total:.1f}s)")


if __name__ == "__main__":
    main()
