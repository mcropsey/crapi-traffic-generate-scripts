#!/usr/bin/env python3
"""
crapi_traffic.py
================
Traffic generator for a crAPI lab instance monitored by an API-security sensor.

All options live in a YAML config file (default: crapi_config.yaml).
Run with:
    python3 crapi_traffic.py                       # uses crapi_config.yaml
    python3 crapi_traffic.py --config other.yaml   # custom path

Phases (toggled in the config):
  warmup    - realistic, high-variety multi-consumer traffic to advance the
              API through the learning period (build distinct-consumer count).
  findings  - detection patterns, split into three populations:
                authenticated   valid sessions (the known mikeN accounts)
                unauthenticated  no Authorization header at all
                bad-token        unsigned / expired / long-life / bypass tokens

Targets a deliberately vulnerable crAPI training instance. Point base_url at
your own lab only.

Dependencies:  pip install requests pyyaml
"""

import argparse
import base64
import json
import os
import random
import string
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/124.0",
    "crAPI-Mobile/2.3.1 (Android 14; Pixel 8)",
    "crAPI-Mobile/2.3.1 (iOS 17.4; iPhone15,3)",
    "PostmanRuntime/7.37.0",
    "python-requests/2.31.0",
    "okhttp/4.12.0",
]

stats = {}


def bump(key, code):
    stats.setdefault(key, {})
    stats[key][code] = stats[key].get(code, 0) + 1


def fmt_dur(seconds):
    """Human-readable duration, e.g. '1h 03m 07s' / '4m 12s' / '9s'."""
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


# ── Config loading ────────────────────────────────────────────────────────────
def load_config(path):
    try:
        import yaml
    except ImportError:
        sys.exit("Missing dependency. Run:  pip install pyyaml")
    if not os.path.exists(path):
        sys.exit(f"Config file not found: {path}\n"
                 f"Create one next to the script (see crapi_config.yaml).")
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    return cfg


# ── Session / consumer identity ───────────────────────────────────────────────
def build_session():
    s = requests.Session()
    retry = Retry(total=1, backoff_factor=0.1,
                  status_forcelist=[502, 503, 504], allowed_methods=None)
    s.mount("http://", HTTPAdapter(max_retries=retry, pool_maxsize=32))
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=32))
    return s


def consumer_headers(idx):
    """Each consumer gets a distinct identity surface. Which of these the sensor
    actually counts as a 'consumer' depends on its config (source IP / token sub
    / api key) — vary all of them so at least one dimension lands."""
    octet_a = (idx // 254) % 254 + 1
    octet_b = idx % 254 + 1
    return {
        "User-Agent": random.choice(UAS),
        "X-Forwarded-For": f"10.{octet_a}.{octet_b}.{random.randint(2, 250)}",
        "X-Api-Client": f"client-{idx:05d}",
    }


def rand_email(tag="user"):
    n = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{tag}_{n}@my.lab"


def rand_name():
    return random.choice(["Alex", "Sam", "Jordan", "Riley", "Casey", "Morgan"]) + \
        " " + "".join(random.choices(string.ascii_uppercase, k=1)) + "."


# ── JWT crafting (no signing key needed; sensor inspects header+claims) ────────
def b64url(obj):
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_jwt(sub, alg="none", exp_delta=3600, sig="fakesig"):
    header = {"alg": alg, "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": sub, "iat": now, "exp": now + exp_delta, "role": "user"}
    token = f"{b64url(header)}.{b64url(payload)}"
    if alg == "none":
        return token + "."          # unsigned: empty signature segment
    return f"{token}.{base64.urlsafe_b64encode(sig.encode()).rstrip(b'=').decode()}"


# ── Core requesters ────────────────────────────────────────────────────────────
def signup(s, email, password, hdrs):
    return s.post(f"{BASE}/identity/api/auth/signup",
                  json={"name": rand_name(), "email": email,
                        "number": "".join(random.choices(string.digits, k=10)),
                        "password": password},
                  headers=hdrs, timeout=TIMEOUT)


def login(s, email, password, hdrs):
    return s.post(f"{BASE}/identity/api/auth/login",
                  json={"email": email, "password": password},
                  headers=hdrs, timeout=TIMEOUT)


def auth_get(s, path, token, hdrs):
    h = dict(hdrs)
    if token:
        h["Authorization"] = f"Bearer {token}"
    return s.get(f"{BASE}{path}", headers=h, timeout=TIMEOUT)


def get_user_tokens():
    """Log in each known lab user once; return {email: token}."""
    tokens = {}
    s = build_session()
    for i, email in enumerate(KNOWN_USERS):
        try:
            r = login(s, email, KNOWN_PASSWORD, consumer_headers(1000 + i))
            tok = ""
            try:
                tok = r.json().get("token", "")
            except Exception:
                pass
            tokens[email] = tok
            bump("auth.login", r.status_code)
        except requests.RequestException:
            tokens[email] = ""
            bump("auth.login", "err")
    s.close()
    ok = sum(1 for t in tokens.values() if t)
    print(f"[auth] obtained tokens for {ok}/{len(KNOWN_USERS)} known users")
    return tokens


# ── WARMUP: realistic multi-consumer traffic for the learning period ──────────
def one_consumer_journey(idx):
    s = build_session()
    hdrs = consumer_headers(idx)
    email = rand_email("warm")
    pw = "GoodPass" + str(random.randint(1000, 9999)) + "!"
    try:
        r = signup(s, email, pw, hdrs); bump("warmup.signup", r.status_code)
        r = login(s, email, pw, hdrs);  bump("warmup.login", r.status_code)
        token = ""
        try:
            token = r.json().get("token", "")
        except Exception:
            pass
        auth_get(s, "/identity/api/v2/user/dashboard", token, hdrs); bump("warmup.dashboard", 1)
        auth_get(s, "/identity/api/v2/vehicle/vehicles", token, hdrs); bump("warmup.vehicles", 1)
        r = auth_get(s, "/workshop/api/shop/products", token, hdrs); bump("warmup.products", r.status_code)
        auth_get(s, "/community/api/v2/community/posts/recent", token, hdrs); bump("warmup.posts", 1)
        if idx % 7 == 0:
            h = dict(hdrs); h["Authorization"] = f"Bearer {token}"
            s.post(f"{BASE}/community/api/v2/community/posts",
                   json={"title": "Trip review", "content": "Smooth drive today."},
                   headers=h, timeout=TIMEOUT)
            bump("warmup.create_post", 1)
    except requests.RequestException as e:
        bump("warmup.error", str(type(e).__name__))
    finally:
        s.close()


def run_warmup(count, threads):
    print(f"[warmup] generating {count} distinct-consumer journeys ...")
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futs = [ex.submit(one_consumer_journey, i) for i in range(count)]
        done = 0
        for _ in as_completed(futs):
            done += 1
            if done % 250 == 0:
                print(f"  ... {done}/{count} consumers")
    print("[warmup] complete")


# ── AUTHENTICATED population ──────────────────────────────────────────────────
def run_authenticated(tokens, rounds):
    print(f"[authenticated] {len(tokens)} users x {rounds} round(s) ...")
    s = build_session()
    emails = list(tokens.keys())
    try:
        for r_ in range(rounds):
            for idx, email in enumerate(emails):
                token = tokens[email]
                if not token:
                    continue
                hdrs = consumer_headers(1000 + idx + r_ * len(emails))
                auth_get(s, "/identity/api/v2/user/dashboard", token, hdrs); bump("auth.dashboard", 1)
                auth_get(s, "/identity/api/v2/vehicle/vehicles", token, hdrs); bump("auth.vehicles", 1)
                auth_get(s, "/workshop/api/shop/products", token, hdrs); bump("auth.products", 1)
                auth_get(s, "/community/api/v2/community/posts/recent", token, hdrs); bump("auth.posts", 1)
                auth_get(s, "/workshop/api/shop/orders/all", token, hdrs); bump("auth.orders", 1)
    finally:
        s.close()
    print("[authenticated] complete")


# ── UNAUTHENTICATED population ────────────────────────────────────────────────
def f_unauth_sensitive(s):
    for path in ("/identity/api/v2/user/dashboard",
                 "/community/api/v2/community/posts/recent",
                 "/workshop/api/shop/orders/all"):
        r = s.get(f"{BASE}{path}", headers=consumer_headers(900), timeout=TIMEOUT)
        bump("unauth_sensitive", r.status_code)


def f_unauthenticated_apis(s):
    for path in ("/identity/api/auth/signup", "/identity/api/auth/login",
                 "/identity/api/auth/forget-password",
                 "/community/api/v2/community/posts/recent",
                 "/workshop/api/shop/products"):
        try:
            r = s.get(f"{BASE}{path}", headers=consumer_headers(990), timeout=TIMEOUT)
            bump("unauth_apis", r.status_code)
        except requests.RequestException:
            bump("unauth_apis", "err")


def f_sensitive_query_params(s):
    qp = {"email": "victim@my.lab", "password": "Secret123!",
          "token": make_jwt("victim@my.lab"), "card": "4111111111111111"}
    r = s.post(f"{BASE}/identity/api/auth/login", params=qp,
               json={"email": qp["email"], "password": qp["password"]},
               headers=consumer_headers(905), timeout=TIMEOUT)
    bump("sensitive_query", r.status_code)


def f_injection_reflection(s):
    marker = "INJ" + uuid.uuid4().hex[:6]
    for p in (f"<script>{marker}</script>", f"' OR '1'='{marker}", f"${{{marker}}}"):
        r = s.post(f"{BASE}/identity/api/auth/signup",
                   json={"name": p, "email": rand_email("inj"),
                         "number": "1234567890", "password": "Weakpass1!"},
                   headers=consumer_headers(906), timeout=TIMEOUT)
        bump("injection", r.status_code)


def f_weak_password(s):
    for pw in ("123", "password", "abc", "111111", "qwerty"):
        r = signup(s, rand_email("weak"), pw, consumer_headers(907))
        bump("weak_password", r.status_code)


def f_tech_info_exposure(s):
    s.post(f"{BASE}/identity/api/auth/login", data="{not:json,,}",
           headers={**consumer_headers(908), "Content-Type": "application/json"},
           timeout=TIMEOUT)
    bump("tech_info", 1)
    s.post(f"{BASE}/identity/api/auth/login",
           json={"email": {"$ne": None}, "password": ["array"]},
           headers=consumer_headers(908), timeout=TIMEOUT)
    bump("tech_info", 1)
    s.get(f"{BASE}/workshop/api/shop/orders/not-an-int",
          headers=consumer_headers(908), timeout=TIMEOUT)
    bump("tech_info", 1)


def f_excessive_single_user(s, intensity):
    target = KNOWN_USERS[0]
    for i in range(40 * intensity):
        r = login(s, target, f"wrong{i}", consumer_headers(909))
        bump("excessive_single", r.status_code)


def f_excessive_across_users(s, intensity):
    pool = list(KNOWN_USERS) + [f"target{i}@my.lab" for i in range(60)]
    for i in range(40 * intensity):
        email = pool[i % len(pool)]
        r = login(s, email, "Password123!", consumer_headers(910 + i))
        bump("excessive_across", r.status_code)


def run_unauthenticated(intensity):
    print("[unauthenticated] generating no-token + pre-auth patterns ...")
    s = build_session()
    try:
        f_unauthenticated_apis(s)
        f_unauth_sensitive(s)
        f_sensitive_query_params(s)
        f_injection_reflection(s)
        f_weak_password(s)
        f_tech_info_exposure(s)
        f_excessive_single_user(s, intensity)
        f_excessive_across_users(s, intensity)
    finally:
        s.close()
    print("[unauthenticated] complete")


# ── BAD-TOKEN population ──────────────────────────────────────────────────────
def run_bad_tokens():
    print("[bad-token] generating unsigned / expired / long-life / bypass ...")
    s = build_session()
    try:
        r = auth_get(s, "/identity/api/v2/user/dashboard",
                     make_jwt("attacker@my.lab", alg="none"), consumer_headers(901))
        bump("unsigned_jwt", r.status_code)
        r = auth_get(s, "/identity/api/v2/user/dashboard",
                     make_jwt(KNOWN_USERS[0], alg="HS256", exp_delta=-86400),
                     consumer_headers(902))
        bump("expired_jwt", r.status_code)
        r = auth_get(s, "/identity/api/v2/user/dashboard",
                     make_jwt(KNOWN_USERS[0], alg="HS256", exp_delta=10 * 365 * 86400),
                     consumer_headers(903))
        bump("longlife_jwt", r.status_code)
        for path in ("/identity/api/auth/v4.0/user/login-with-token",
                     "/identity/api/auth/v2.7/user/login-with-token"):
            r = s.post(f"{BASE}{path}",
                       json={"token": make_jwt("x@my.lab", alg="none")},
                       headers=consumer_headers(904), timeout=TIMEOUT)
            bump("auth_bypass", r.status_code)
    finally:
        s.close()
    print("[bad-token] complete")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="crAPI lab traffic generator (config-driven)")
    ap.add_argument("--config", default="crapi_config.yaml",
                    help="path to the YAML config file (default: crapi_config.yaml)")
    args = ap.parse_args()
    cfg = load_config(args.config)

    global BASE, TIMEOUT, KNOWN_USERS, KNOWN_PASSWORD
    target = cfg.get("target", {}) or {}
    BASE = str(target.get("base_url", "http://192.168.1.101:8888")).rstrip("/")

    ku = cfg.get("known_users", {}) or {}
    KNOWN_USERS = ku.get("emails") or [f"mike{i}@my.lab" for i in range(1, 10)]
    KNOWN_PASSWORD = ku.get("password", "Mylab123!")

    http = cfg.get("http", {}) or {}
    TIMEOUT = float(http.get("timeout", 10.0))

    runc = cfg.get("run", {}) or {}
    do_warmup = bool(runc.get("warmup", False))
    do_findings = bool(runc.get("findings", False))

    wc = cfg.get("warmup", {}) or {}
    consumers = int(wc.get("consumers", 2500))
    threads = int(wc.get("threads", 12))

    fc = cfg.get("findings", {}) or {}
    auth_rounds = int(fc.get("auth_rounds", 3))
    intensity = int(fc.get("intensity", 1))

    if not (do_warmup or do_findings):
        sys.exit("Nothing to do: set run.warmup and/or run.findings to true in the config.")

    print(f"config: {args.config}")
    print(f"target: {BASE}")
    start = time.time()
    timings = {}

    if do_warmup:
        t0 = time.time()
        run_warmup(consumers, threads)
        timings["warmup"] = time.time() - t0

    if do_findings:
        t0 = time.time()
        tokens = get_user_tokens()
        run_authenticated(tokens, auth_rounds)
        run_unauthenticated(intensity)
        run_bad_tokens()
        timings["findings"] = time.time() - t0

    total = time.time() - start
    print("\n--- summary ---")
    for k in sorted(stats):
        print(f"{k}: {stats[k]}")
    print("\n--- timing ---")
    for phase, dur in timings.items():
        print(f"{phase}: {fmt_dur(dur)} ({dur:.1f}s)")
    print(f"total run time: {fmt_dur(total)} ({total:.1f}s)")


if __name__ == "__main__":
    main()
