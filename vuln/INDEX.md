# crAPI Challenge Scripts Index

All challenge scripts are numbered 01-15 to match the official crAPI challenge documentation.

## Overview

### Challenge 01: BOLA on Vehicle Location
- **File**: `crapi_challenge_01_bola_vehicle_location.py`
- **Vulnerability**: Broken Object Level Authorization (BOLA)
- **Description**: Access another user's vehicle location by finding their vehicleId from community posts
- **Usage**: `python3 crapi_challenge_01_bola_vehicle_location.py --victim-email mike2@my.lab`

### Challenge 02: BOLA on Mechanic Reports  
- **File**: `crapi_challenge_02_bola_mechanic_reports.py`
- **Vulnerability**: Broken Object Level Authorization (BOLA)
- **Description**: Enumerate and access other users' mechanic reports by IDs
- **Usage**: `python3 crapi_challenge_02_bola_mechanic_reports.py --count 50`

### Challenge 03: Broken Auth - Password Reset
- **File**: `crapi_challenge_03_broken_auth_password_reset.py`
- **Vulnerability**: Broken Authentication + OTP Brute-Force
- **Description**: Reset another user's password by brute-forcing the 4-digit OTP (v2 endpoint has no rate limiting)
- **Usage**: `python3 crapi_challenge_03_broken_auth_password_reset.py --victim-email mike2@my.lab`

### Challenge 04: Excessive Data Exposure
- **File**: `crapi_challenge_04_excessive_data_exposure.py`
- **Vulnerability**: Excessive Data Exposure
- **Description**: Retrieve sensitive data (emails, names, vehicle IDs) from community posts endpoint
- **Usage**: `python3 crapi_challenge_04_excessive_data_exposure.py`

### Challenge 05: Internal Video Property Exposure
- **File**: `crapi_challenge_05_internal_video_property.py`
- **Vulnerability**: Information Disclosure
- **Description**: Find the internal `conversion_params` property in video responses
- **Usage**: `python3 crapi_challenge_05_internal_video_property.py`

### Challenge 06: Layer 7 DoS
- **File**: `crapi_challenge_06_layer7_dos.py`
- **Vulnerability**: Denial of Service (Layer 7)
- **Description**: Trigger DoS by sending contact_mechanic with high repeat_request_if_failed count
- **Usage**: `python3 crapi_challenge_06_layer7_dos.py --repeat-count 1000`

### Challenge 07: BFLA - Delete Other User's Video
- **File**: `crapi_challenge_07_delete_other_user_video.py`
- **Vulnerability**: Broken Function Level Authorization (BFLA)
- **Description**: Delete another user's video via admin endpoint without proper authorization
- **Usage**: `python3 crapi_challenge_07_delete_other_user_video.py --video-id <victim_video_id>`

### Challenge 08: Mass Assignment - Free Item
- **File**: `crapi_challenge_08_free_item_negative_quantity.py`
- **Vulnerability**: Mass Assignment
- **Description**: Get free item by using negative quantity in order (receive credit instead of paying)
- **Usage**: `python3 crapi_challenge_08_free_item_negative_quantity.py --quantity -1`

### Challenge 09: Mass Assignment - $1000+ Balance
- **File**: `crapi_challenge_09_increase_balance_1000.py`
- **Vulnerability**: Mass Assignment
- **Description**: Increase balance by $1000+ using large negative quantity
- **Usage**: `python3 crapi_challenge_09_increase_balance_1000.py --quantity -100`

### Challenge 10: Mass Assignment - Video Property
- **File**: `crapi_challenge_10_mass_assignment_video_property.py`
- **Vulnerability**: Mass Assignment
- **Description**: Update internal video properties like `conversion_params`
- **Usage**: `python3 crapi_challenge_10_mass_assignment_video_property.py`

### Challenge 11: SSRF
- **File**: `crapi_challenge_11_ssrf.py`
- **Vulnerability**: Server-Side Request Forgery (SSRF)
- **Description**: Make crAPI call external URLs via mechanic_api parameter
- **Usage**: `python3 crapi_challenge_11_ssrf.py --target-url https://www.google.com`

### Challenge 12: NoSQL Injection - Free Coupons
- **File**: `crapi_challenge_12_nosql_injection_coupons.py`
- **Vulnerability**: NoSQL Injection
- **Description**: Bypass coupon validation using NoSQL operators like `{"$ne": null}`
- **Usage**: `python3 crapi_challenge_12_nosql_injection_coupons.py`

### Challenge 13: SQL Injection - Redeem Coupon Twice
- **File**: `crapi_challenge_13_sql_injection_coupons.py`
- **Vulnerability**: SQL Injection
- **Description**: Redeem already-claimed coupons using SQL injection
- **Usage**: `python3 crapi_challenge_13_sql_injection_coupons.py --coupon-code TRAC075`

### Challenge 14: Unauthenticated Access
- **File**: `crapi_challenge_14_unauthenticated_access.py`
- **Vulnerability**: Missing Authentication
- **Description**: Access protected endpoints (mechanic reports, orders) without authentication
- **Usage**: `python3 crapi_challenge_14_unauthenticated_access.py --report-id 1`

### Challenge 15: JWT Forgery
- **File**: `crapi_challenge_15_jwt_forgery.py`
- **Vulnerability**: Broken Cryptography / JWT Bypass
- **Description**: Forge valid JWT tokens using unsigned or weak algorithms
- **Usage**: `python3 crapi_challenge_15_jwt_forgery.py --target-email mike2@my.lab`

## Common Options

All scripts support:
- `--config ../crapi_config.yaml` - Path to config file (default: ../crapi_config.yaml)

## Running All Challenges

```bash
# Test each challenge to identify vulnerabilities
for i in {01..15}; do
    python3 crapi_challenge_${i}_*.py --help
done
```

## Notes

- All scripts reference the config file in the parent directory (`../crapi_config.yaml`)
- Scripts are designed for the crAPI lab instance specified in the config
- Use these to test API security detection systems
- Baseline traffic scripts are in the parent directory for comparison

