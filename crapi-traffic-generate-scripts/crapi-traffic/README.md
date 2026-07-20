# crAPI Lab Traffic Generator

Generates API traffic against a **crAPI** training instance to (1) advance the
API through your security sensor's *learning period* and (2) exercise the
specific detection patterns that show up as findings.

> crAPI is a deliberately vulnerable application built for security training.
> Point this tool at **your own lab only** — never at systems you don't own.

## Files

| File | Purpose |
|------|---------|
| `crapi_seed_users_cars_forums.py` | One-time setup: creates the lab users, vehicles, and forum posts. |
| `crapi_traffic.py` | The traffic generator. |
| `crapi_config.yaml` | All options live here — edit this, not the scripts. |
| `requirements.txt` | Python dependencies. |
| `README.md` | This file. |

## Prerequisites

- Python 3.8 or newer (`python3 --version` to check).
- Network access from your machine to the crAPI instance.

## Setup (virtual environment)

Working in a virtual environment keeps these dependencies isolated from your
system Python. From the project folder:

### macOS / Linux

```bash
# 1. create the venv
python3 -m venv .venv

# 2. activate it
source .venv/bin/activate

# 3. install dependencies into the venv
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Once activated, your prompt shows `(.venv)`. Everything below assumes the venv
is active. To leave it later, run `deactivate`.

## Configure

Open `crapi_config.yaml` and set the things specific to your lab:

```yaml
target:
  base_url: "https://crapi.cropseyit.com"   # <- your crAPI instance
  mailhog_base: "http://mail.cropseyit.com" # <- your MailHog (seed script only)

known_users:
  password: "Mylab123!"                      # <- shared password for mike1..mike9
```

Both scripts read these same values, so set them once. Every option in the file
has an inline comment explaining exactly what changes when you edit it (which
phases run, how many consumers, credential-attempt volume, timeouts, etc.).
Review them before your first run.

## Seed the lab (one-time)

Before generating traffic, populate the lab with the known users, their
vehicles, and a forum post each. This is what makes the `mikeN` accounts exist
and gives the authenticated traffic something real to read.

```bash
python3 crapi_seed_users_cars_forums.py
```

For each user it: registers the account, waits for crAPI's enrollment email in
MailHog, parses the VIN and PIN from it, adds the vehicle, and creates a post.
It prints a summary table at the end (✅ SUCCESS / ⚠️ PARTIAL / ❌ FAILED).

Requirements for this step:

- `target.base_url` and `target.mailhog_base` in the config must both be
  reachable from your machine.
- The MailHog instance must be the one crAPI delivers to, or the VIN/PIN lookup
  will time out (`❌ Could not find VIN/PIN`).

Run it once per lab. Re-running is harmless — already-registered users just
report a registration error and are skipped.

## Run

```bash
python3 crapi_traffic.py
```

That reads `crapi_config.yaml` from the current folder. To use a different
config file:

```bash
python3 crapi_traffic.py --config staging.yaml
```

### What a run does

Driven by the `run:` switches in the config:

- **warmup** — many distinct-consumer journeys (signup → login → browse) to
  build the observed-consumer count and move the API out of learning.
- **findings** — three labeled populations:
  - *authenticated* — valid sessions from the `mikeN` accounts,
  - *unauthenticated* — requests with no token at all,
  - *bad-token* — unsigned / expired / long-life / bypass tokens.

A typical first-day pattern is warmup-only (`run.findings: false`) to start the
learning clock, then flip to `run.findings: true` once the API reports out of
learning so the detection patterns actually surface.

## Troubleshooting

- **`Missing dependency. Run: pip install pyyaml`** — the venv isn't active or
  deps aren't installed. Re-activate and run the `pip install -r requirements.txt`
  step. Confirm with `python3 -m pip list | grep -i pyyaml`.
- **`obtained tokens for 0/9 known users`** — the `known_users.password` in the
  config doesn't match the lab accounts. Fix it and re-run.
- **`NotOpenSSLWarning ... LibreSSL`** (yellow line on macOS) — harmless, from
  the system Python's TLS build. It doesn't affect `http://` traffic. Silence it
  by uncommenting `urllib3<2` in `requirements.txt` and reinstalling.
- **`❌ Could not find VIN/PIN` (seed script)** — MailHog isn't reachable at
  `target.mailhog_base`, or it isn't the inbox crAPI delivers to. Verify with
  `curl <mailhog_base>/api/v1/messages` and confirm crAPI's SMTP points there.
- **Connection errors / timeouts** — confirm `target.base_url` is reachable
  (`curl <base_url>/identity/api/auth/login`) and raise `http.timeout` if the
  lab is slow.

## Notes

- Status codes printed in the run summary are crAPI's responses, **not** the
  sensor's verdict. Findings are raised by the monitoring platform after the
  learning period completes.
- Re-running is safe; warmup creates fresh throwaway accounts each time.
