# crAPI Baseline Script (Python)

This script baselines the crAPI environment by simulating realistic user traffic. It registers and logs in users, adds vehicles, places orders, interacts with the community forum, and more. While not exhaustive, it generates enough traffic to build an accurate API model.

**This script is intended to be used after the Noname platform has been installed, and the crAPI traffic has been integrated and the integration has been validated.**

By default, 100 users are simulated at a concurrency of 10. This can be tuned via environment variables (see below).

## Target Endpoints

| Service | URL |
|---------|-----|
| crAPI | https://crapi.cropseyit.com |
| Mailhog | https://mail.cropseyit.com |

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — orchestrates user simulation and concurrency |
| `crapi.py` | All crAPI endpoint calls |
| `mailhog.py` | Mailhog API calls (used to retrieve VIN/PIN from registration emails) |
| `user.py` | Generates randomized fake users |
| `config.py` | Host URLs, regex patterns, and tunable settings |
| `requirements.txt` | Python dependencies |

## Requirements

- Python 3.8+
- pip3

## Install & Run

**1. Install dependencies**
```bash
pip3 install -r requirements.txt --break-system-packages
```

**2. Run the script**
```bash
python3 main.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USERS_TO_SIMULATE` | `100` | Number of randomized users to simulate |
| `FIRST_RUN` | unset | When set, also baselines four fixed users (Jane Doe, John Smith, crapi_user1, crapi_user2) |

**Examples:**
```bash
# Simulate 50 users
USERS_TO_SIMULATE=50 python3 main.py

# First run — simulate 100 random users AND the fixed accounts
FIRST_RUN=true python3 main.py

# Both together
FIRST_RUN=true USERS_TO_SIMULATE=200 python3 main.py
```

## Running in the Background

It's recommended to run this inside `tmux` or `screen` so the script survives SSH disconnects.

```bash
# Start a new tmux session
tmux new -s baseline

# Run the script
python3 main.py

# Detach (leave running in background)
# Press Ctrl+B, then D

# Reattach later
tmux attach -t baseline
```

## What Each User Does

Each simulated user performs the following actions in order:

1. Register and log in
2. Load dashboard and vehicles
3. Retrieve registration email from Mailhog to extract VIN and PIN
4. Add vehicle, refresh location
5. Upload a profile avatar
6. Contact a mechanic and retrieve the report
7. Browse the shop, validate and apply a coupon
8. Place, update, and return an order
9. Read and comment on recent community posts
10. Create a new forum post
11. Trigger a forgot-password flow and change email address

## Notes

- Errors for individual users are caught and logged but will not stop the overall run — some failures are normal
- Video upload is disabled (no video file required)
- Concurrency is set to 10 (`BATCH_SIZE` in `config.py`) and can be adjusted there directly
