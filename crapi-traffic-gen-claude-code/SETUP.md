# crAPI Noname Traffic Generator

Generates realistic, comprehensive traffic across every crAPI endpoint so that
Noname API Security's learning phase completes (`Status: Done`) and Posture /
Runtime findings populate the way they do in the corporate demo environment.

---

## Project layout

```
crapi-traffic-gen/
├── config.ini            ← hosts and tuning knobs — edit this
├── crapi_traffic_gen.py  ← traffic generator script
├── requirements.txt      ← pinned Python dependencies
├── setup.sh              ← one-time bootstrap (creates .venv, checks connectivity)
├── run.sh                ← daily driver (activates .venv automatically)
├── .gitignore
└── SETUP.md              ← this file
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.9 or later | `python3 --version` to check |
| `pip` | Bundled with Python 3.4+ |
| `curl` | Used by `setup.sh` for connectivity checks |
| Network access to crAPI and Mailhog | VPN may be required |

---

## First-time setup

**Run this once.** It creates an isolated virtual environment, installs
dependencies, and checks that both target hosts are reachable.

```bash
cd ~/crapi-traffic-gen
chmod +x setup.sh run.sh
./setup.sh
```

What `setup.sh` does, step by step:

1. Confirms Python 3.9+ is available.
2. Creates `.venv/` in the project directory using `python3 -m venv`.
3. Upgrades `pip` inside the venv.
4. Runs `pip install -r requirements.txt` inside the venv.
5. Makes a test request to `crapi_base_url` and `mailhog_base_url` and prints
   whether each is reachable.
6. Prints the exact commands to activate the venv and run the script.

`.venv/` is listed in `.gitignore` and should never be committed.

### Manual venv setup (if you prefer)

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows PowerShell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

Edit **`config.ini`** before your first run.  All host names and tuning
parameters live here — the script reads nothing else at startup.

```ini
[targets]
crapi_base_url    = https://crapi.cropseyit.com
mailhog_base_url  = https://mail.cropseyit.com

[settings]
num_users                = 6
iterations               = 3
delay_between_requests   = 0.5
verify_ssl               = false
email_domain             = noname.test
log_level                = INFO
log_file                 = crapi_traffic.log
```

| Key | Default | Purpose |
|---|---|---|
| `crapi_base_url` | `https://crapi.cropseyit.com` | crAPI application URL (no trailing slash) |
| `mailhog_base_url` | `https://mail.cropseyit.com` | Mailhog URL (no trailing slash) |
| `num_users` | `6` | Fresh user accounts to create per run |
| `iterations` | `3` | Full traffic cycles — cycle 1 creates accounts, later cycles re-use them |
| `delay_between_requests` | `0.5` | Base pause in seconds between API calls (jittered ±0.3 s) |
| `verify_ssl` | `false` | Set `true` only if your hosts have valid, signed TLS certs |
| `email_domain` | `noname.test` | Domain appended to generated user email addresses |
| `log_level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `log_file` | `crapi_traffic.log` | Log file written next to the script (append mode) |

---

## Running

### Standard run — use `run.sh` (recommended)

`run.sh` activates the venv for you; no manual `source` needed.

```bash
./run.sh
```

Pass any arguments straight through:

```bash
./run.sh --users 10 --iterations 5 --delay 0.3
./run.sh --help
```

### Activate the venv yourself and call Python directly

```bash
source .venv/bin/activate
python crapi_traffic_gen.py
python crapi_traffic_gen.py --users 10 --iterations 5
deactivate                         # when finished
```

### Run in the background

```bash
nohup ./run.sh --users 8 --iterations 4 > /tmp/crapi_run.log 2>&1 &
echo "PID: $!"
tail -f /tmp/crapi_run.log         # watch live
```

### Repeat on a schedule with cron

Open the crontab editor:

```bash
crontab -e
```

Add a line to run every 2 hours (replace the path with your actual path):

```
0 */2 * * * /Users/mcropsey/crapi-traffic-gen/run.sh \
    --users 6 --iterations 2 \
    >> /tmp/crapi_cron.log 2>&1
```

`run.sh` uses an absolute path to the venv Python, so it works correctly
from cron without any extra `source` or `PATH` setup.

---

## What each iteration does

For **every user account** in each cycle:

| Phase | Endpoints covered |
|---|---|
| Auth | `POST /identity/api/auth/signup` *(first run only)*, `POST /identity/api/auth/login` |
| Public docs | `GET /apidocs`, `GET /api/docs` |
| Dashboard | `GET /identity/api/v2/user/dashboard` |
| Profile picture | `POST /identity/api/v2/user/pictures` |
| Profile video | `POST /identity/api/v2/user/videos`, `GET …/videos/{id}`, `PUT …/videos/{id}`, `GET …/videos/convert_video` |
| Vehicles | `GET /identity/api/v2/vehicle/vehicles`, `POST …/add_vehicle` *(via Mailhog)*, `GET …/{uuid}/location`, `POST …/resend_email` |
| Community posts | `GET /community/api/v2/community/posts/recent`, `POST …/posts`, `GET …/posts/{id}`, `POST …/posts/{id}/comment` |
| Coupons | `POST /community/api/v2/coupon/validate-coupon`, `POST /workshop/api/shop/apply_coupon` |
| Shop | `GET /workshop/api/shop/products`, `POST …/orders`, `GET …/orders/all`, `GET …/orders/{id}`, `POST …/orders/return_order` |
| Mechanics | `GET /workshop/api/mechanic/`, `POST /workshop/api/merchant/contact_mechanic`, `GET …/receive_report`, `GET …/mechanic_report`, `GET …/service_requests` |
| Password reset | `POST /identity/api/auth/forget-password`, `POST …/v2/check-otp`, `POST …/v3/check-otp` |
| Email change | `POST /identity/api/v2/user/change-email` |
| Mailhog API | `GET /api/v2/messages`, `GET /api/v2/search`, `GET /api/v1/messages`, `GET /api/v1/messages/{id}`, `GET /api/v2/outgoing-smtp` |

---

## How the Mailhog integration works

crAPI sends emails for two flows that the script needs to complete:

1. **Vehicle registration** — sent after signup, contains the VIN and pincode
   needed to call `add_vehicle`.
2. **Password-reset OTP** — sent after `forget-password`, contains a numeric
   OTP required by `check-otp`.

The script polls `GET /api/v2/search?kind=to&query=<email>` up to 6 times
(3 s apart).  If the email still isn't found it falls back to:

- Calling `resend_email` and polling again.
- Submitting a dummy OTP so that the `check-otp` endpoints still receive
  traffic even when the OTP lookup fails.

---

## Recommended plan for a new Noname environment

Noname typically needs **~72 hours** of observed traffic before marking all
endpoints `Done`.  To accelerate this:

1. Run `./setup.sh` once to bootstrap.
2. Run `./run.sh` immediately to seed the initial traffic.
3. Add a cron job to repeat every 2 hours (see above).
4. After 24–48 hours check the Noname portal — all APIs from `findings.csv`
   should show `Done` and Posture findings should be populated.

---

## Troubleshooting

### Reading the connectivity check output

At startup the script probes each service and logs:

```
Connectivity check:
  identity     ✓  HTTP 401  (https://crapi.cropseyit.com/identity/api/auth/login)
  community    ✗  ConnectionRefusedError: ...
  workshop     ✗  ConnectTimeout: ...
  mailhog      ✓  HTTP 200  (https://mail.cropseyit.com/api/v2/messages)
Unreachable services: ['community', 'workshop'] — their endpoints will be skipped
```

Any service marked `✗` will have **all its endpoints skipped** for the run.
The exception type and message tell you exactly what is wrong:

| Exception | Meaning |
|---|---|
| `ConnectionRefusedError` | The port is closed — that container/service is not running |
| `ConnectTimeout` | Host is reachable but the port does not respond within `request_timeout` seconds — check firewall or the service process |
| `SSLError` | TLS handshake failed — try `verify_ssl = false` in `config.ini` |
| `NewConnectionError` | DNS or routing failure — check the URL in `config.ini` |

### Identity service unreachable — script exits immediately
- The script will not continue if the identity service fails the connectivity check.
- Confirm `crapi_base_url` in `config.ini` is correct.
- Test manually: `curl -sk https://crapi.cropseyit.com/identity/api/auth/login -d '{}' -H 'Content-Type: application/json'`
- The crAPI app may still be starting — wait a minute and retry.

### Community or workshop service unreachable
These are separate microservices (Go and Python Flask) that run alongside the
Java identity service.  If they are down:
- Check that the community and workshop Docker containers are running:
  ```
  docker ps | grep -E "community|workshop"
  ```
- Check that the nginx/reverse-proxy config routes `/community/` and `/workshop/`
  to those containers.
- Check the container logs: `docker logs <container_id>`

### `pip install` fails during `setup.sh`
- Make sure you have internet access.
- Run `source .venv/bin/activate && pip install --upgrade pip` then retry.

### Videos / pictures return 500
crAPI's media service sometimes rejects minimal files.  This is non-fatal —
the endpoint is still observed by Noname.  Increase `delay_between_requests`
if it happens consistently.

### Vehicles never found in Mailhog
The script now prints the actual exception if Mailhog is unreachable.  If it
shows `✗` in the connectivity check:
- Confirm `mailhog_base_url` in `config.ini` is correct.
- Test: `curl -sk https://mail.cropseyit.com/api/v2/messages | head -c 200`
- Check Mailhog in a browser at `https://mail.cropseyit.com`.
- When Mailhog is unreachable the vehicle email poll is skipped immediately
  (no more 30-second blocking wait).

### Requests taking too long / script runs slowly
Increase `request_timeout` in `config.ini` for slow servers, or decrease it
to fail faster on dead services.  The default is 15 seconds.

### SSL certificate errors
Set `verify_ssl = false` in `config.ini` (already the default for self-signed certs).

### Noname still shows "In Progress" after 48 h
- Increase `num_users` (try 10–15) and `iterations` (try 5+) and re-run.
- Verify the Noname sensor is capturing traffic from `crapi.cropseyit.com`
  (check sensor status in the Noname portal).
- Run with `--delay 0.2` for denser traffic.
- Confirm community and workshop are reachable (see connectivity check above) —
  Noname needs traffic to those services too.

### "WARNING: not running inside a virtual environment"
Run `./setup.sh` to create `.venv`, then use `./run.sh` instead of calling
`python` directly.
