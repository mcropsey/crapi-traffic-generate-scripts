# crAPI Traffic Generator

A traffic driver for your own [OWASP crAPI](https://github.com/OWASP/crAPI) training
instance. It exercises the **entire crAPI API surface** — real signups, logins,
vehicle onboarding, community posts, shop orders, mechanic flows, password
resets, and more — so that an inline API-security sensor (Noname / Akamai API
Security, and similar) sees enough authenticated, body-carrying request/response
pairs on **every** endpoint to:

- move APIs out of **"In Progress"** learning status into **"Done"**, and
- populate **Posture Findings** (weak password policy, BOLA, sensitive-data
  exposure, etc.) like the ones in your corporate demo environment.

Everything configurable — hosts, credentials, volume, timing — lives in
`config.yaml`. You should never need to edit the Python.

---

## Why your APIs are stuck "In Progress"

A discovery sensor promotes an endpoint to "Done" only after it has observed
enough **complete, representative** transactions on it. Endpoints stall when:

1. **Traffic never reaches them.** Some crAPI endpoints only fire after a
   multi-step flow (e.g. you can't hit `add_vehicle` until you've read the VIN +
   pincode that crAPI emails to MailHog). A shallow script that just spams
   `/login` never touches them.
2. **Requests aren't authenticated.** Most endpoints need a valid JWT. Anonymous
   or failed calls give the sensor thin, non-representative samples.
3. **Bodies are empty or identical.** Datatype detection (email, password, VIN,
   coordinates, coupon code…) needs realistic, varied payloads.
4. **Volume is too low.** One request isn't a pattern. Endpoints need repeated
   hits over time.

This generator addresses all four: it logs in for real, pulls email-delivered
secrets from MailHog to finish the vehicle and OTP flows, sends varied realistic
bodies, and repeats on a loop.

---

## What it exercises

All 44 operations in your OpenAPI spec, including the ones that need a real
end-to-end flow:

- **Auth / identity:** signup, login, login-with-token (v2.7 + v4.0),
  forgot-password + OTP reset (v2 + v3 check-otp), change-email + verify token.
- **Profile:** dashboard, profile picture upload, video upload → get → rename →
  convert → delete (user + admin delete).
- **Vehicles:** resend onboarding email, **add vehicle using the VIN + pincode
  read from MailHog**, list vehicles, vehicle location.
- **Community:** create posts, recent feed, get post, comment, new + validate
  coupon.
- **Shop:** list + add products, create orders, get all / get one / update /
  return order, return QR code, apply coupon.
- **Workshop / mechanic:** mechanic signup, list mechanics, workshop users,
  contact mechanic, receive report, service requests, mechanic report.

The generator also queries the MailHog API (`/api/v2/search`, `/api/v2/messages`),
which mirrors the mail-server endpoints your demo environment tracks.

---

## 1. Install

You need **Python 3.8+**. Check with `python3 --version`.

> **Important — command form.** Do **not** run `python3 pip install ...`. That
> tells Python to execute a *file* named `pip` and fails with
> `can't open file '.../pip': [Errno 2] No such file or directory`. Always use
> the module form: `python3 -m pip install ...`.

On modern macOS (Homebrew Python), a plain `pip install` is blocked by PEP 668
with `error: externally-managed-environment`. Use a virtual environment — this is
the recommended, cleanest fix and avoids touching your system Python:

```bash
# from the folder that contains crapi_traffic.py (e.g. crapi-traffic-gen)

# 1. create a virtual environment in this folder
python3 -m venv .venv

# 2. activate it  (Windows: .venv\Scripts\activate)
source .venv/bin/activate

# 3. install the two dependencies
python3 -m pip install -r requirements.txt
```

Your shell prompt will show `(.venv)` once activated. Run the generator from
inside this activated environment (see sections 3–4). To leave it later, type
`deactivate`; to return, just re-run `source .venv/bin/activate` from this folder.

### Alternative: skip the venv (not recommended)

If you would rather install into the system Python, override PEP 668 with
`--break-system-packages` (and `--user` to avoid breaking Homebrew):

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

Only two packages are required: `requests` and `PyYAML`.

---

## 2. Configure

Open **`config.yaml`** and set the two hosts:

```yaml
hosts:
  crapi_base:  "https://crapi.cropseyit.com"
  mailhog_base: "https://mail.cropseyit.com"
```

Then review these common knobs:

| Setting | What it does |
|---|---|
| `network.verify_tls` | Set `false` only if your instance uses self-signed certs. |
| `network.proxy` | Route **all** traffic through an inline collector/sensor, e.g. `http://127.0.0.1:8080`. Leave blank to go direct. |
| `run.mode` | `loop` (run for days) or `once` (single sweep). CLI flags override this. |
| `run.loop_interval_seconds` | Gap between sweeps in loop mode (default 900s = 15 min). |
| `volume.*` | How many users/posts/orders/etc. per sweep. Raise these to build history faster. |
| `mechanic.signup_code` | Code crAPI requires for mechanic registration. Stock default is `TRAC_JHTQ`; change if your deployment customized it. |
| `seed_users` | Any pre-seeded crAPI accounts you want replayed each sweep. |
| `generated_account_password` | Password used for generated accounts. Kept intentionally weak so the "Weak Password Policy" finding also triggers. |

Full comments for every field are inline in `config.yaml`.

---

## 3. Verify connectivity

Before generating traffic, confirm the script can reach both hosts:

```bash
python3 crapi_traffic.py --check
```

You want to see `Self-check PASSED`, with an HTTP status from both crAPI's login
endpoint and MailHog's `/api/v2/messages`. If MailHog is unreachable, the
vehicle and OTP flows will fall back to best-effort values (still generating
traffic, but with less complete data).

---

## 4. Run

```bash
# One full sweep of every endpoint, then exit (good for cron / Task Scheduler)
python3 crapi_traffic.py --once

# Run continuously, re-exercising everything on the configured interval
python3 crapi_traffic.py --loop

# Use whatever run.mode is set to in config.yaml
python3 crapi_traffic.py

# Point at a different config file
python3 crapi_traffic.py -c staging.yaml --loop
```

Each sweep logs every call and a summary line, e.g.
`SWEEP #3 DONE: 120 calls (110 ok / 10 err)`. A log file
(`crapi_traffic.log` by default) is written next to the script.

> **On "err" counts:** some non-2xx responses are expected and still useful — a
> failed login or an invalid coupon is legitimate traffic the sensor profiles.
> The goal is coverage and volume, not a clean 200 on every call.

---

## 5. Keep it running for a few days

To promote endpoints to "Done", let it run continuously so the sensor
accumulates samples over time.

### Linux / macOS — background with `nohup`

```bash
nohup python3 crapi_traffic.py --loop > /dev/null 2>&1 &
```

### Linux — systemd service (survives reboots)

Create `/etc/systemd/system/crapi-traffic.service`:

```ini
[Unit]
Description=crAPI Traffic Generator
After=network-online.target

[Service]
WorkingDirectory=/opt/crapi-traffic
ExecStart=/usr/bin/python3 /opt/crapi-traffic/crapi_traffic.py --loop
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now crapi-traffic
sudo journalctl -u crapi-traffic -f    # watch logs
```

### Linux / macOS — cron (single sweep every 15 min)

Set `run.mode: once` (or use `--once`) and add:

```cron
*/15 * * * * cd /opt/crapi-traffic && /usr/bin/python3 crapi_traffic.py --once >> cron.log 2>&1
```

### Windows — Task Scheduler

Create a task that runs, e.g. every 15 minutes:

```
Program/script:  python
Add arguments:   crapi_traffic.py --once
Start in:        C:\path\to\crapi-traffic
```

Or run the loop mode once at logon with `python crapi_traffic.py --loop`.

---

## Troubleshooting

**Some endpoints still show "In Progress" after a day.**
Give it more volume and time. Increase `volume.new_users_per_cycle`,
`posts_per_user`, `orders_per_user`, and shorten `run.loop_interval_seconds`.
More importantly, confirm the sensor is actually seeing this traffic — if crAPI
sits behind a proxy/daemonset sensor, make sure the generator's traffic path
crosses it (use `network.proxy` if needed).

**`add_vehicle` returns errors / vehicles list is empty.**
The VIN + pincode come from the email crAPI sends to MailHog. Run `--check` to
confirm MailHog is reachable, and make sure crAPI is configured to deliver mail
to the MailHog host in `config.yaml`. Watch the log for `add_vehicle -> 200`
vs `add_vehicle (fallback)`.

**`verify-email-token` never appears in the logs.**
It only fires when the change-email token is found in MailHog. If MailHog is
disabled or the token can't be parsed, the step is skipped by design.

**Mechanic signup returns 4xx.**
Your instance likely uses a non-default mechanic code. Set
`mechanic.signup_code` to the value configured in your crAPI deployment.

**TLS errors.**
If you use self-signed certs, set `network.verify_tls: false`.

**Rate limiting / overload.**
Lower the `volume.*` numbers and raise `run.loop_interval_seconds`.

---

## Files

| File | Purpose |
|---|---|
| `crapi_traffic.py` | The generator. No editing required. |
| `config.yaml` | All hosts, credentials, volume, and timing settings. |
| `requirements.txt` | Python dependencies (`requests`, `PyYAML`). |
| `README.md` | This guide. |
| `crapi_traffic.log` | Run log (created on first run). |

---

## Note on intended use

crAPI is intentionally vulnerable software published by OWASP for security
training. This generator is for driving traffic against **your own** crAPI
instance so your API-security tooling can learn and profile it. Point it only at
systems you own or are authorized to test.
