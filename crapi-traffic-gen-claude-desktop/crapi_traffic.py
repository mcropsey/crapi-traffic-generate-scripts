#!/usr/bin/env python3
"""
crAPI Traffic Generator
=======================
Exercises the full OWASP crAPI attack surface so that an API-security sensor
(Noname / Akamai API Security, etc.) can observe enough authenticated,
body-carrying request/response pairs per endpoint to move APIs from
"In Progress" to "Done" and to populate Posture Findings.

It drives real end-to-end flows:
  * consumer + mechanic account signup and login (JWT)
  * dashboard, profile picture + video upload / convert / rename / delete
  * vehicle onboarding using VIN + pincode pulled from MailHog
  * vehicle listing and location
  * community posts, comments, coupons
  * shop products, orders, order return, apply coupon
  * mechanic contact / service requests / reports
  * change-email + verify token, forgot-password + OTP reset (via MailHog)

All hosts, volumes, and timing come from config.yaml. Nothing to edit here.

Usage:
    python crapi_traffic.py                 # uses run.mode from config.yaml
    python crapi_traffic.py --once          # single full sweep, then exit
    python crapi_traffic.py --loop          # force continuous loop
    python crapi_traffic.py --check         # validate config + connectivity only
    python crapi_traffic.py -c other.yaml   # use a different config file

This tool is for exercising YOUR OWN crAPI training instance. crAPI is
intentionally vulnerable software published by OWASP for security education.
"""

import argparse
import io
import logging
import os
import random
import re
import string
import sys
import time
import uuid

try:
    import requests
    import yaml
except ImportError:
    sys.stderr.write(
        "Missing dependencies. Install them with:\n"
        "    pip install -r requirements.txt\n"
        "or: pip install requests pyyaml\n"
    )
    sys.exit(1)

from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    Retry = None

# Silence noisy TLS warnings when verify_tls is intentionally disabled.
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #
def load_config(path):
    if not os.path.exists(path):
        sys.stderr.write("Config file not found: %s\n" % path)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    # Minimal validation of the pieces the script relies on.
    for key in ("hosts", "network", "run", "volume", "mailhog"):
        cfg.setdefault(key, {})
    cfg["hosts"].setdefault("crapi_base", "http://localhost:8888")
    cfg["hosts"].setdefault("mailhog_base", "http://localhost:8025")
    cfg["hosts"]["crapi_base"] = cfg["hosts"]["crapi_base"].rstrip("/")
    cfg["hosts"]["mailhog_base"] = cfg["hosts"]["mailhog_base"].rstrip("/")
    return cfg


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
def setup_logging(cfg):
    logcfg = cfg.get("logging", {})
    level = getattr(logging, str(logcfg.get("level", "INFO")).upper(), logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout)]
    log_file = logcfg.get("log_file")
    if log_file:
        # log next to the script for predictability
        path = log_file if os.path.isabs(log_file) else os.path.join(
            os.path.dirname(os.path.abspath(__file__)), log_file)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("crapi")


# --------------------------------------------------------------------------- #
# Small helpers for realistic-but-fake data
# --------------------------------------------------------------------------- #
FIRST = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie",
         "Cameron", "Avery", "Quinn", "Sofia", "Cristobal", "Einar", "Danielle"]
LAST = ["Weissnat", "Predovic", "Swaniawski", "Ankunding", "Kirlin", "Bahringer",
         "Hettinger", "Cormier", "Reynolds", "Larson", "Okuneva"]
POST_TITLES = ["Great service today", "Road trip planning", "Battery question",
               "Best tires for winter?", "Weird noise on startup",
               "Loving the new dashboard", "Coupon codes?", "Mechanic recommendation"]
LOREM = ("Necessitatibus vero veniam quos nobis. Est maiores voluptas velit "
         "and the drive was smooth all the way through the mountains.")


def rand_name():
    return "%s.%s" % (random.choice(FIRST), random.choice(LAST))


def rand_email(name=None):
    base = (name or rand_name()).replace(" ", ".").lower()
    return "%s.%s@example.com" % (base, uuid.uuid4().hex[:6])


def rand_phone():
    return "".join(random.choice(string.digits) for _ in range(10))


def rand_vin():
    chars = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"  # no I,O,Q per VIN spec
    return "".join(random.choice(chars) for _ in range(17))


# --------------------------------------------------------------------------- #
# MailHog reader
# --------------------------------------------------------------------------- #
class MailHog:
    """Reads emails crAPI sends so we can complete flows that need secrets
    delivered by email: vehicle VIN + pincode, OTP, and change-email tokens."""

    def __init__(self, cfg, session, log):
        self.cfg = cfg
        self.base = cfg["hosts"]["mailhog_base"]
        self.session = session
        self.log = log
        mh = cfg.get("mailhog", {})
        self.enabled = mh.get("enabled", True)
        self.attempts = int(mh.get("poll_attempts", 12))
        self.interval = float(mh.get("poll_interval_seconds", 3))
        self.kind = mh.get("search_kind", "to")
        self.verify = cfg["network"].get("verify_tls", True)
        self.timeout = cfg["network"].get("timeout_seconds", 20)

    def _search(self, query):
        # MailHog v2 search API. Also generates GET /api/v2/search traffic,
        # matching the reference environment.
        url = "%s/api/v2/search" % self.base
        try:
            r = self.session.get(
                url, params={"kind": self.kind, "query": query},
                verify=self.verify, timeout=self.timeout)
            if r.status_code == 200:
                return r.json().get("items", []) or []
        except Exception as exc:
            self.log.debug("MailHog search failed: %s", exc)
        return []

    @staticmethod
    def _body(item):
        try:
            body = item.get("Content", {}).get("Body", "") or ""
        except Exception:
            body = ""
        # MailHog sometimes quoted-printable encodes '=' as '=3D' etc.
        body = body.replace("=\r\n", "").replace("=\n", "")
        body = body.replace("=3D", "=").replace("=2C", ",")
        return body

    def wait_for(self, recipient, extractor):
        """Poll MailHog for the newest email to `recipient`, run `extractor`
        over its body, return the first truthy result."""
        if not self.enabled:
            return None
        for _ in range(self.attempts):
            items = self._search(recipient)
            # newest first
            for item in items:
                result = extractor(self._body(item))
                if result:
                    return result
            time.sleep(self.interval)
        return None

    def get_vehicle_details(self, recipient):
        """Extract (vin, pincode) from the crAPI vehicle onboarding email."""
        def extract(body):
            vin = re.search(r"\b([A-HJ-NPR-Z0-9]{17})\b", body)
            pin = re.search(r"[Pp]in\s*[Cc]ode\s*[:\-]?\s*(\d{3,8})", body) \
                or re.search(r"[Pp]incode\s*[:\-]?\s*(\d{3,8})", body)
            if vin and pin:
                return (vin.group(1), pin.group(1))
            return None
        return self.wait_for(recipient, extract)

    def get_otp(self, recipient):
        def extract(body):
            m = re.search(r"OTP[^0-9]{0,20}(\d{3,8})", body, re.IGNORECASE) \
                or re.search(r"\b(\d{4,8})\b", body)
            return m.group(1) if m else None
        return self.wait_for(recipient, extract)

    def get_change_email_token(self, recipient):
        def extract(body):
            # crAPI email tokens are ~20 char mixed-case alphanumerics.
            m = re.search(r"token[^A-Za-z0-9]{0,10}([A-Za-z0-9]{8,40})",
                          body, re.IGNORECASE) \
                or re.search(r"\b([A-Za-z0-9]{20})\b", body)
            return m.group(1) if m else None
        return self.wait_for(recipient, extract)


# --------------------------------------------------------------------------- #
# crAPI client
# --------------------------------------------------------------------------- #
class Crapi:
    def __init__(self, cfg, session, log, mailhog):
        self.cfg = cfg
        self.base = cfg["hosts"]["crapi_base"]
        self.s = session
        self.log = log
        self.mail = mailhog
        net = cfg["network"]
        self.verify = net.get("verify_tls", True)
        self.timeout = net.get("timeout_seconds", 20)
        self.snip = cfg.get("logging", {}).get("show_response_snippets", False)
        # per-request counters for the sweep summary
        self.stats = {"ok": 0, "err": 0, "calls": 0}

    # -- low level ---------------------------------------------------------- #
    def _req(self, method, path, token=None, label=None, **kw):
        url = path if path.startswith("http") else self.base + path
        headers = kw.pop("headers", {}) or {}
        if token:
            headers["Authorization"] = "Bearer " + token
        label = label or ("%s %s" % (method, path))
        self.stats["calls"] += 1
        try:
            r = self.s.request(method, url, headers=headers,
                               verify=self.verify, timeout=self.timeout, **kw)
            ok = r.status_code < 400
            self.stats["ok" if ok else "err"] += 1
            lvl = logging.INFO if ok else logging.WARNING
            self.log.log(lvl, "%-40s -> %s", label, r.status_code)
            if self.snip:
                self.log.debug("    body: %s", (r.text or "")[:200].replace("\n", " "))
            return r
        except Exception as exc:
            self.stats["err"] += 1
            self.log.warning("%-40s -> EXC %s", label, exc)
            return None

    @staticmethod
    def _json(resp):
        if resp is None:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    # -- auth --------------------------------------------------------------- #
    def signup(self, name, email, number, password):
        return self._req("POST", "/identity/api/auth/signup", label="signup",
                         json={"name": name, "email": email,
                               "number": number, "password": password})

    def login(self, email, password):
        r = self._req("POST", "/identity/api/auth/login", label="login",
                      json={"email": email, "password": password})
        data = self._json(r)
        return data.get("token")

    def login_with_token_v2_7(self, email):
        self._req("POST", "/identity/api/auth/v2.7/user/login-with-token",
                  label="login-with-token v2.7", json={"email": email})

    def login_with_token_v4(self, email):
        self._req("POST", "/identity/api/auth/v4.0/user/login-with-token",
                  label="login-with-token v4.0", json={"email": email})

    # -- profile / dashboard ------------------------------------------------ #
    def dashboard(self, token):
        return self._json(self._req(
            "GET", "/identity/api/v2/user/dashboard", token=token, label="dashboard"))

    def upload_profile_pic(self, token):
        img = _tiny_png()
        self._req("POST", "/identity/api/v2/user/pictures", token=token,
                  label="upload profile pic",
                  files={"file": ("avatar.png", img, "image/png")})

    def change_email(self, token, old_email, new_email):
        self._req("POST", "/identity/api/v2/user/change-email", token=token,
                  label="change-email",
                  json={"old_email": old_email, "new_email": new_email})
        token_val = self.mail.get_change_email_token(new_email) if self.mail else None
        if token_val:
            self._req("POST", "/identity/api/v2/user/verify-email-token",
                      token=token, label="verify-email-token",
                      json={"old_email": old_email, "new_email": new_email,
                            "token": token_val})

    def reset_password(self, token, email, new_password):
        self._req("POST", "/identity/api/v2/user/reset-password", token=token,
                  label="reset-password (authed)",
                  json={"email": email, "password": new_password})

    # -- forgot password / OTP (no auth, reads OTP from MailHog) ------------ #
    def forgot_password_flow(self, email, new_password):
        self._req("POST", "/identity/api/auth/forget-password",
                  label="forget-password", json={"email": email})
        otp = self.mail.get_otp(email) if self.mail else None
        if not otp:
            self.log.debug("No OTP retrieved for %s; sending best-effort", email)
            otp = "0000"
        body = {"email": email, "otp": otp, "password": new_password}
        # exercise both OTP versions the sensor tracks
        self._req("POST", "/identity/api/auth/v3/check-otp",
                  label="check-otp v3", json=body)
        self._req("POST", "/identity/api/auth/v2/check-otp",
                  label="check-otp v2", json=body)

    # -- videos ------------------------------------------------------------- #
    def video_flow(self, token):
        r = self._req("POST", "/identity/api/v2/user/videos", token=token,
                      label="upload video",
                      files={"file": ("clip.mp4", _tiny_mp4(), "video/mp4")})
        data = self._json(r)
        vid = data.get("id") or data.get("video_id")
        if vid:
            self._req("GET", "/identity/api/v2/user/videos/%s" % vid, token=token,
                      label="get video")
            self._req("PUT", "/identity/api/v2/user/videos/%s" % vid, token=token,
                      label="rename video",
                      json={"videoName": "road-trip-%s" % random.randint(1, 999)})
            self._req("GET", "/identity/api/v2/user/videos/convert_video",
                      token=token, label="convert video",
                      params={"video_id": vid})
            # Exercise both delete paths (user self-delete + admin delete).
            self._req("DELETE", "/identity/api/v2/admin/videos/%s" % vid,
                      token=token, label="admin delete video")
            self._req("DELETE", "/identity/api/v2/user/videos/%s" % vid,
                      token=token, label="delete video")
        return vid

    # -- vehicles ----------------------------------------------------------- #
    def onboard_vehicle(self, token, email):
        # Ask crAPI to (re)send the vehicle onboarding email, then read it.
        self._req("POST", "/identity/api/v2/vehicle/resend_email", token=token,
                  label="vehicle resend_email")
        details = self.mail.get_vehicle_details(email) if self.mail else None
        if details:
            vin, pincode = details
            self._req("POST", "/identity/api/v2/vehicle/add_vehicle", token=token,
                      label="add_vehicle",
                      json={"vin": vin, "pincode": pincode})
        else:
            self.log.debug("No vehicle email for %s; best-effort add_vehicle", email)
            self._req("POST", "/identity/api/v2/vehicle/add_vehicle", token=token,
                      label="add_vehicle (fallback)",
                      json={"vin": rand_vin(), "pincode": "0000"})
        # List vehicles and query location for each.
        vehicles = self._json(self._req(
            "GET", "/identity/api/v2/vehicle/vehicles", token=token,
            label="get vehicles"))
        ids = _extract_vehicle_ids(vehicles)
        for vid in ids[:3]:
            self._req("GET", "/identity/api/v2/vehicle/%s/location" % vid,
                      token=token, label="vehicle location")
        return ids

    # -- community ---------------------------------------------------------- #
    def community_flow(self, token, posts, comments):
        created = []
        for _ in range(posts):
            r = self._req("POST", "/community/api/v2/community/posts", token=token,
                          label="create post",
                          json={"title": random.choice(POST_TITLES),
                                "content": LOREM})
            pid = self._json(r).get("id")
            if pid:
                created.append(pid)
        recent = self._json(self._req(
            "GET", "/community/api/v2/community/posts/recent", token=token,
            label="recent posts"))
        # Gather post ids from recent feed too (so comments hit real posts).
        ids = created + _extract_post_ids(recent)
        for pid in ids[:max(1, comments)]:
            self._req("GET", "/community/api/v2/community/posts/%s" % pid,
                      token=token, label="get post")
            self._req("POST",
                      "/community/api/v2/community/posts/%s/comment" % pid,
                      token=token, label="post comment",
                      json={"content": "Thanks for sharing! " + LOREM[:40]})
        # Coupon endpoints (community side)
        code = "TRAC" + "".join(random.choice(string.ascii_uppercase) for _ in range(4))
        self._req("POST", "/community/api/v2/coupon/new-coupon", token=token,
                  label="new coupon (community)",
                  json={"coupon_code": code, "amount": random.randint(10, 90)})
        self._req("POST", "/community/api/v2/coupon/validate-coupon", token=token,
                  label="validate coupon",
                  json={"coupon_code": code})
        return created

    # -- shop --------------------------------------------------------------- #
    def shop_flow(self, token, orders, add_products):
        products = self._json(self._req(
            "GET", "/workshop/api/shop/products", token=token, label="get products"))
        pids = _extract_product_ids(products)
        for _ in range(add_products):
            self._req("POST", "/workshop/api/shop/products", token=token,
                      label="add product",
                      json={"name": "Part-%s" % random.randint(100, 999),
                            "price": round(random.uniform(9, 499), 2),
                            "image_url": "https://example.com/part.png"})
        order_ids = []
        for _ in range(orders):
            product_id = random.choice(pids) if pids else 1
            r = self._req("POST", "/workshop/api/shop/orders", token=token,
                          label="create order",
                          json={"product_id": product_id,
                                "quantity": random.randint(1, 3)})
            oid = self._json(r).get("id") or _dig(self._json(r), "order", "id")
            if oid:
                order_ids.append(oid)
        # Read orders back
        self._req("GET", "/workshop/api/shop/orders/all", token=token,
                  label="get all orders")
        for oid in order_ids[:3]:
            self._req("GET", "/workshop/api/shop/orders/%s" % oid, token=token,
                      label="get order")
            self._req("PUT", "/workshop/api/shop/orders/%s" % oid, token=token,
                      label="update order",
                      json={"quantity": random.randint(1, 5),
                            "status": "delivered"})
            self._req("POST", "/workshop/api/shop/orders/return_order",
                      token=token, label="return order",
                      params={"order_id": oid})
        # QR + coupon on the shop side
        self._req("GET", "/workshop/api/shop/return_qr_code", token=token,
                  label="return qr code")
        code = "OFF" + "".join(random.choice(string.digits) for _ in range(4))
        self._req("POST", "/workshop/api/shop/apply_coupon", token=token,
                  label="apply coupon (shop)",
                  json={"coupon_code": code, "amount": random.randint(10, 75)})
        return order_ids

    # -- mechanic / workshop ------------------------------------------------ #
    def mechanic_signup(self, name, email, number, password, code):
        self._req("POST", "/workshop/api/mechanic/signup", label="mechanic signup",
                  json={"name": name, "email": email, "number": number,
                        "password": password, "mechanic_code": code})

    def mechanic_flow(self, token, vins):
        self._req("GET", "/workshop/api/mechanic/", token=token,
                  label="get mechanics")
        self._req("GET", "/workshop/api/management/users/all", token=token,
                  label="workshop users all")
        vin = vins[0] if vins else rand_vin()
        mech = self.cfg.get("mechanic", {})
        code = mech.get("existing_code", "TRAC_JHTQ")
        api = mech.get("existing_api",
                       self.base + "/workshop/api/mechanic/receive_report")
        # Consumer contacts a mechanic about a problem -> creates service request
        self._req("POST", "/workshop/api/merchant/contact_mechanic", token=token,
                  label="contact_mechanic",
                  json={"mechanic_code": code, "mechanic_api": api, "vin": vin,
                        "number_of_repeats": 1, "repeat_request_if_failed": False,
                        "problem_details": "Engine makes a knocking sound."})
        # receive_report is unauthenticated and takes query params
        self._req("GET", "/workshop/api/mechanic/receive_report",
                  label="receive_report",
                  params={"mechanic_code": code, "vin": vin,
                          "problem_details": "Knocking sound, please inspect."})
        # Mechanic-side reads
        self._req("GET", "/workshop/api/mechanic/service_requests", token=token,
                  label="service_requests")
        self._req("GET", "/workshop/api/mechanic/mechanic_report", token=token,
                  label="mechanic_report", params={"report_id": 1})


# --------------------------------------------------------------------------- #
# Response-shape helpers (crAPI responses vary slightly across versions)
# --------------------------------------------------------------------------- #
def _dig(d, *keys):
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return None
    return d


def _extract_vehicle_ids(data):
    ids = []
    seq = data if isinstance(data, list) else _first_list(data)
    for v in seq or []:
        vid = v.get("uuid") or v.get("id") or _dig(v, "vehicleLocation", "id")
        if vid:
            ids.append(vid)
    return ids


def _extract_post_ids(data):
    ids = []
    seq = data if isinstance(data, list) else _first_list(data)
    for p in seq or []:
        pid = p.get("id") or p.get("uuid")
        if pid:
            ids.append(pid)
    return ids


def _extract_product_ids(data):
    ids = []
    seq = _dig(data, "products") or (data if isinstance(data, list) else _first_list(data))
    for p in seq or []:
        pid = p.get("id")
        if pid:
            ids.append(pid)
    return ids


def _first_list(data):
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


# --------------------------------------------------------------------------- #
# Tiny binary payloads for uploads (no external files needed)
# --------------------------------------------------------------------------- #
def _tiny_png():
    # 1x1 transparent PNG
    import base64
    b64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
           "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    return io.BytesIO(base64.b64decode(b64))


def _tiny_mp4():
    # Minimal ftyp box; enough to be a non-empty "video" upload.
    data = (b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
            b"\x00\x00\x00\x08free")
    return io.BytesIO(data)


# --------------------------------------------------------------------------- #
# Session builder
# --------------------------------------------------------------------------- #
def build_session(cfg):
    s = requests.Session()
    net = cfg["network"]
    proxy = net.get("proxy")
    if proxy:
        s.proxies.update({"http": proxy, "https": proxy})
    if Retry is not None:
        retry = Retry(total=int(net.get("retries", 2)), backoff_factor=0.5,
                      status_forcelist=(502, 503, 504),
                      allowed_methods=None)
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
    s.headers.update({"User-Agent": "crapi-traffic-generator/1.0",
                      "Accept": "application/json"})
    return s


# --------------------------------------------------------------------------- #
# One full sweep of the API surface
# --------------------------------------------------------------------------- #
class Runner:
    def __init__(self, cfg, log):
        self.cfg = cfg
        self.log = log
        self.session = build_session(cfg)
        self.mail = MailHog(cfg, self.session, log)
        self.api = Crapi(cfg, self.session, log, self.mail)
        self.known_users = []  # list of (email, password) created this process
        self._seed_known_users()

    def _seed_known_users(self):
        for u in self.cfg.get("seed_users", []) or []:
            if u.get("email") and u.get("password"):
                self.known_users.append((u["email"], u["password"]))

    def _active_accounts(self):
        vol = self.cfg["volume"]
        accounts = []
        # 1) brand-new consumer accounts
        for _ in range(int(vol.get("new_users_per_cycle", 3))):
            name = rand_name()
            email = rand_email(name)
            pwd = self.cfg.get("generated_account_password", "Password123!")
            self.api.signup(name, email, rand_phone(), pwd)
            # magic-link/token login endpoints the sensor also tracks
            self.api.login_with_token_v2_7(email)
            self.api.login_with_token_v4(email)
            accounts.append((email, pwd))
            self.known_users.append((email, pwd))
        # 2) replay a sample of previously-known users
        if vol.get("reuse_existing_users", True):
            pool = self.known_users[:-len(accounts)] if accounts else self.known_users
            sample = pool[-int(vol.get("max_reused_users", 10)):]
            accounts.extend(sample)
        return accounts

    def _run_mechanics(self, token, vins):
        vol = self.cfg["volume"]
        code = self.cfg.get("mechanic", {}).get("signup_code", "TRAC_JHTQ")
        pwd = self.cfg.get("generated_account_password", "Password123!")
        for _ in range(int(vol.get("new_mechanics_per_cycle", 1))):
            name = rand_name()
            self.api.mechanic_signup(name, rand_email(name), rand_phone(), pwd, code)
        # Exercise mechanic/workshop reads + service-request flow as a user.
        if token:
            self.api.mechanic_flow(token, vins)

    def sweep(self, cycle):
        vol = self.cfg["volume"]
        self.log.info("========== SWEEP #%d START ==========", cycle)
        self.api.stats = {"ok": 0, "err": 0, "calls": 0}

        accounts = self._active_accounts()
        primary_vins = []

        for email, pwd in accounts:
            token = self.api.login(email, pwd)
            if not token:
                # Unauthenticated flows we can still exercise for this email.
                self.api.forgot_password_flow(email, pwd)
                continue

            self.api.dashboard(token)
            self.api.upload_profile_pic(token)
            self.api.video_flow(token)
            vins = self.api.onboard_vehicle(token, email)
            if vins and not primary_vins:
                primary_vins = vins
            self.api.community_flow(token,
                                    int(vol.get("posts_per_user", 2)),
                                    int(vol.get("comments_per_user", 2)))
            self.api.shop_flow(token,
                               int(vol.get("orders_per_user", 2)),
                               int(vol.get("products_added_per_cycle", 1)))

            # account-maintenance flows (change email + password reset)
            new_email = rand_email()
            self.api.change_email(token, email, new_email)
            self.api.reset_password(token, email, pwd)

        # Mechanic / workshop flows using the last valid token if any.
        last_token = None
        for email, pwd in reversed(accounts):
            last_token = self.api.login(email, pwd)
            if last_token:
                break
        self._run_mechanics(last_token, primary_vins)

        # A couple of unauthenticated password-reset cycles for coverage.
        for email, pwd in accounts[:2]:
            self.api.forgot_password_flow(email, pwd)

        st = self.api.stats
        self.log.info("SWEEP #%d DONE: %d calls (%d ok / %d err)",
                      cycle, st["calls"], st["ok"], st["err"])
        return st


# --------------------------------------------------------------------------- #
# Connectivity / config self-check
# --------------------------------------------------------------------------- #
def run_check(cfg, log):
    log.info("Config OK. crAPI base: %s | MailHog base: %s",
             cfg["hosts"]["crapi_base"], cfg["hosts"]["mailhog_base"])
    session = build_session(cfg)
    verify = cfg["network"].get("verify_tls", True)
    timeout = cfg["network"].get("timeout_seconds", 20)
    ok = True
    # crAPI reachability (login endpoint should answer even to a bad body)
    try:
        r = session.post(cfg["hosts"]["crapi_base"] + "/identity/api/auth/login",
                         json={"email": "x@example.com", "password": "x"},
                         verify=verify, timeout=timeout)
        log.info("crAPI reachable: HTTP %s from /identity/api/auth/login", r.status_code)
    except Exception as exc:
        ok = False
        log.error("crAPI NOT reachable: %s", exc)
    # MailHog reachability
    if cfg.get("mailhog", {}).get("enabled", True):
        try:
            r = session.get(cfg["hosts"]["mailhog_base"] + "/api/v2/messages",
                            params={"limit": 1}, verify=verify, timeout=timeout)
            log.info("MailHog reachable: HTTP %s from /api/v2/messages", r.status_code)
        except Exception as exc:
            ok = False
            log.error("MailHog NOT reachable: %s", exc)
    log.info("Self-check %s", "PASSED" if ok else "FAILED")
    return 0 if ok else 2


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description="crAPI traffic generator")
    parser.add_argument("-c", "--config", default="config.yaml",
                        help="path to config file (default: config.yaml)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="single sweep then exit")
    mode.add_argument("--loop", action="store_true", help="run continuously")
    parser.add_argument("--check", action="store_true",
                        help="validate config + connectivity, then exit")
    args = parser.parse_args(argv)

    # resolve config path relative to the script if not absolute
    cfg_path = args.config
    if not os.path.isabs(cfg_path) and not os.path.exists(cfg_path):
        alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), cfg_path)
        if os.path.exists(alt):
            cfg_path = alt

    cfg = load_config(cfg_path)
    log = setup_logging(cfg)

    if args.check:
        return run_check(cfg, log)

    mode = "loop"
    if args.once:
        mode = "once"
    elif args.loop:
        mode = "loop"
    else:
        mode = cfg["run"].get("mode", "loop")

    runner = Runner(cfg, log)
    log.info("Starting crAPI traffic generator in '%s' mode against %s",
             mode, cfg["hosts"]["crapi_base"])

    if mode == "once":
        runner.sweep(1)
        return 0

    # loop mode
    interval = float(cfg["run"].get("loop_interval_seconds", 900))
    jitter = float(cfg["run"].get("jitter_seconds", 0))
    stop_after = int(cfg["run"].get("stop_after_cycles", 0))
    cycle = 0
    try:
        while True:
            cycle += 1
            runner.sweep(cycle)
            if stop_after and cycle >= stop_after:
                log.info("Reached stop_after_cycles=%d; exiting.", stop_after)
                break
            wait = interval + random.uniform(-jitter, jitter)
            wait = max(5.0, wait)
            log.info("Sleeping %.0fs before next sweep...", wait)
            time.sleep(wait)
    except KeyboardInterrupt:
        log.info("Interrupted; exiting cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
