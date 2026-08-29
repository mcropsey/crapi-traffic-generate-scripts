#!/usr/bin/env python3
"""Seed crAPI with additional car parts"""
import sys, time, random
from pathlib import Path
from typing import Optional
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

def create_product(base_url: str, token: str, name: str, price: float, description: str = "", timeout: float = 15) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": name,
        "price": price,
        "description": description,
        "image_url": "images/parts.svg"
    }
    try:
        r = requests.post(f"{base_url.rstrip('/')}/workshop/api/shop/products",
                         json=payload, headers=headers, timeout=timeout)
        return r.status_code in (200, 201)
    except Exception as e:
        return False

def main():
    config_path = Path("./crapi_config.yaml")
    if not config_path.exists():
        print("[!] Config file not found"); sys.exit(1)

    cfg = load_config(config_path)
    base_url = cfg["target"]["base_url"]
    password = cfg["known_users"]["password"]

    print(f"[*] Seeding car parts")
    print(f"[*] Target: {base_url}\n")

    # Comprehensive list of car parts with price ranges
    parts = [
        ("Engine Oil", 25.00, "High-quality synthetic motor oil"),
        ("Air Filter", 15.99, "Engine air filter replacement"),
        ("Oil Filter", 8.50, "Engine oil filter"),
        ("Spark Plugs (Set of 4)", 32.00, "Premium spark plugs"),
        ("Battery", 85.00, "Car battery 12V 60Ah"),
        ("Alternator", 150.00, "Vehicle alternator"),
        ("Starter Motor", 120.00, "Electric starter motor"),
        ("Brake Pads (Front)", 45.00, "Ceramic brake pads"),
        ("Brake Pads (Rear)", 40.00, "Rear brake pad set"),
        ("Brake Rotors", 65.00, "Front brake rotor pair"),
        ("Brake Fluid", 12.00, "DOT 4 brake fluid"),
        ("Cabin Air Filter", 18.00, "Cabin air filter replacement"),
        ("Transmission Fluid", 35.00, "ATF transmission fluid"),
        ("Coolant", 20.00, "Engine coolant concentrate"),
        ("Windshield Wipers", 22.00, "Windshield wiper blades pair"),
        ("Headlight Bulbs", 28.00, "HID headlight bulbs"),
        ("Tail Light Assembly", 55.00, "LED tail light"),
        ("Mirror Assembly", 35.00, "Side mirror assembly"),
        ("Door Handle", 25.00, "Exterior door handle"),
        ("Window Regulator", 45.00, "Electric window regulator"),
        ("Door Lock Actuator", 38.00, "Power door lock actuator"),
        ("Belt and Pulley Kit", 89.00, "Serpentine belt and pulley"),
        ("Water Pump", 95.00, "Engine water pump"),
        ("Thermostat Housing", 42.00, "Thermostat and housing"),
        ("Radiator", 130.00, "Replacement radiator"),
        ("Heater Core", 75.00, "Vehicle heater core"),
        ("A/C Compressor", 210.00, "Air conditioning compressor"),
        ("A/C Condenser", 165.00, "Air conditioning condenser"),
        ("Fuel Pump", 145.00, "Electric fuel pump"),
        ("Fuel Filter", 18.00, "Fuel filter cartridge"),
        ("Fuel Injectors (Set)", 125.00, "Set of 4 fuel injectors"),
        ("Ignition Coil", 35.00, "Ignition coil pack"),
        ("Oxygen Sensor", 48.00, "O2 sensor replacement"),
        ("Mass Air Flow Sensor", 65.00, "MAF sensor"),
        ("Suspension Springs", 95.00, "Front coil springs"),
        ("Shock Absorbers (Pair)", 110.00, "Front shock absorbers"),
        ("Strut Assembly", 135.00, "Complete strut assembly"),
        ("Control Arms", 85.00, "Front lower control arm"),
        ("Tie Rod Ends", 55.00, "Inner and outer tie rods"),
        ("Sway Bar Links", 38.00, "Stabilizer bar links"),
        ("Bushings Kit", 45.00, "Suspension bushing kit"),
        ("Ball Joints", 65.00, "Upper and lower ball joints"),
        ("CV Axle Shaft", 125.00, "Front CV axle assembly"),
        ("Driveshaft", 185.00, "Rear driveshaft"),
        ("Differential Cover", 28.00, "Differential cover plate"),
        ("Motor Mounts (Set)", 95.00, "Engine motor mount set"),
        ("Transmission Mount", 75.00, "Transmission mounting bracket"),
        ("Exhaust Manifold", 85.00, "Engine exhaust manifold"),
        ("Catalytic Converter", 200.00, "Catalytic converter assembly"),
        ("Muffler", 65.00, "Exhaust muffler"),
        ("Exhaust Pipe", 45.00, "Exhaust pipe section"),
    ]

    print(f"[*] Attempting to create {len(parts)} parts...\n")

    token = login(base_url, "mike1@my.lab", password)
    if not token:
        print("[!] Login failed"); sys.exit(1)

    success_count = 0
    for i, (name, price, description) in enumerate(parts, 1):
        print(f"[{i:02d}] {name}: ${price:.2f} - ", end="", flush=True)
        if create_product(base_url, token, name, price, description):
            print("✓")
            success_count += 1
        else:
            print("✗")
        time.sleep(0.2)

    print(f"\n[+] Created {success_count}/{len(parts)} parts")

if __name__ == "__main__":
    main()
