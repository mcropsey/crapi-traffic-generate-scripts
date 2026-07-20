#!/usr/bin/env python3
"""
crAPI Traffic Generator for Noname API Security Posture Findings

Exercises every crAPI endpoint so that Noname's learning phase
completes (status: Done) and posture/runtime findings populate.

Usage:
    ./run.sh                                          # recommended
    ./run.sh --users 8 --iterations 5 --delay 0.3

    # or with the venv activated manually:
    source .venv/bin/activate
    python crapi_traffic_gen.py --users 8 --iterations 5
"""

import sys
import os

# Warn when run outside the project venv so dependency issues are caught early.
_expected_venv = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv")
_active_prefix = getattr(sys, "base_prefix", sys.prefix)
_in_venv = (sys.prefix != _active_prefix) or (
    os.path.abspath(sys.prefix).startswith(os.path.abspath(_expected_venv))
)
if not _in_venv:
    print(
        "WARNING: not running inside a virtual environment.\n"
        "Run ./setup.sh once, then use ./run.sh to avoid dependency issues.\n",
        file=sys.stderr,
    )

import argparse
import base64
import configparser
import io
import json
import logging
import os
import random
import re
import string
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "config.ini"
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

CRAPI_URL = config.get("targets", "crapi_base_url", fallback="https://crapi.cropseyit.com").rstrip("/")
MAILHOG_URL = config.get("targets", "mailhog_base_url", fallback="https://mail.cropseyit.com").rstrip("/")
NUM_USERS = config.getint("settings", "num_users", fallback=6)
ITERATIONS = config.getint("settings", "iterations", fallback=3)
DELAY = config.getfloat("settings", "delay_between_requests", fallback=0.5)
VERIFY_SSL = config.getboolean("settings", "verify_ssl", fallback=False)
EMAIL_DOMAIN = config.get("settings", "email_domain", fallback="noname.test")
LOG_LEVEL = config.get("settings", "log_level", fallback="INFO")
LOG_FILE = config.get("settings", "log_file", fallback="crapi_traffic.log")
REQUEST_TIMEOUT = config.getint("settings", "request_timeout", fallback=15)

# Populated by check_connectivity() before the first iteration.
# Keys: "identity", "community", "workshop", "mailhog"
SERVICE_STATUS: Dict[str, bool] = {}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / LOG_FILE),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedded assets (so no external files are needed)
# ---------------------------------------------------------------------------

# 1×1 transparent PNG
_MINIMAL_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
MINIMAL_PNG = base64.b64decode(_MINIMAL_PNG_B64)

# Minimal valid ISO-base media file (MP4/ftyp only; crAPI stores without validating)
MINIMAL_MP4 = bytes([
    0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70,
    0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00,
    0x69, 0x73, 0x6F, 0x6D, 0x69, 0x73, 0x6F, 0x32,
    0x61, 0x76, 0x63, 0x31, 0x6D, 0x70, 0x34, 0x31,
])

# ---------------------------------------------------------------------------
# Static data pools
# ---------------------------------------------------------------------------

FIRST_NAMES = ["Alex", "Jordan", "Morgan", "Taylor", "Casey", "Riley", "Drew",
               "Quinn", "Blake", "Cameron", "Avery", "Peyton", "Skylar", "Reese"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
              "Miller", "Davis", "Wilson", "Anderson", "Thomas", "Martinez"]

POST_TITLES = [
    "My experience with the crAPI platform",
    "Best maintenance tips I've discovered",
    "Question about vehicle warranty",
    "Happy with the service today!",
    "Tips for winter driving",
    "Anyone else love the new models?",
    "Mechanic recommendation needed",
    "Road trip planning — vehicle tracking is amazing",
    "Coupon codes that actually work",
    "First impressions after a week",
]

POST_CONTENTS = [
    "Just wanted to share my experience. Really impressed with the API features!",
    "Has anyone tried the new products in the shop? They look interesting.",
    "The vehicle location tracking is working great. Very convenient for daily use.",
    "The mechanic service was prompt and professional. Highly recommend TRAC_MECH1.",
    "What's the best way to maintain vehicle performance? Looking for community tips.",
    "Just got back from a long road trip. The vehicle tracking was incredibly useful.",
    "Applied a coupon today and got great discounts. Check the promotions section!",
    "First time using the platform and already a fan. Clean interface and fast APIs.",
    "The community forum is a great addition. Love seeing everyone's experiences.",
    "Got my service request handled same day. Impressed with the mechanic team.",
]

PROBLEMS = [
    "Engine check light is on, need a diagnostic scan",
    "Strange clicking noise from front left wheel at low speed",
    "AC not cooling properly, possible refrigerant leak",
    "Routine oil change and filter replacement needed",
    "Brake pads feel thin, inspection required",
    "Battery voltage seems low, possible replacement needed",
    "Transmission is shifting rough between 2nd and 3rd gear",
    "Tire rotation and wheel balancing due",
    "Windshield wiper fluid system not working",
    "Power steering feels heavy, fluid check needed",
]

COUPON_CODES = ["TRAC75", "TRAC10"]

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def rstr(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def check_connectivity() -> None:
    """Probe one representative endpoint per service and populate SERVICE_STATUS.

    Called once at startup so that unreachable services are detected immediately
    rather than being discovered one timed-out call at a time.
    """
    probes = [
        # (key, url, method, body)
        ("identity",  f"{CRAPI_URL}/identity/api/auth/login",                     "POST", {"email": "x", "password": "x"}),
        ("community", f"{CRAPI_URL}/community/api/v2/community/posts/recent",     "GET",  None),
        ("workshop",  f"{CRAPI_URL}/workshop/api/shop/products",                  "GET",  None),
        ("mailhog",   f"{MAILHOG_URL}/api/v2/messages",                           "GET",  None),
    ]
    log.info("Connectivity check:")
    for key, url, method, body in probes:
        try:
            if method == "POST":
                r = requests.post(url, json=body, verify=VERIFY_SSL,
                                  timeout=REQUEST_TIMEOUT)
            else:
                r = requests.get(url, verify=VERIFY_SSL, timeout=REQUEST_TIMEOUT)
            SERVICE_STATUS[key] = True
            log.info(f"  {key:12s} ✓  HTTP {r.status_code}  ({url})")
        except Exception as exc:
            SERVICE_STATUS[key] = False
            log.warning(f"  {key:12s} ✗  {type(exc).__name__}: {exc}")
            log.warning(f"             → all {key} endpoints will be skipped this run")


def make_user() -> Dict:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    tag = rstr(6)
    name = f"{first}.{last}.{tag}"
    return {
        "name": name,
        "email": f"{name.lower()}@{EMAIL_DOMAIN}",
        "number": "".join(random.choices(string.digits, k=10)),
        "password": f"Test!{rstr(8)}",
    }


# ---------------------------------------------------------------------------
# Mailhog helpers
# ---------------------------------------------------------------------------


def mh_get(path: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
    """GET from Mailhog, return Response or None on error."""
    try:
        r = requests.get(f"{MAILHOG_URL}{path}", params=params,
                         verify=VERIFY_SSL, timeout=10)
        return r
    except Exception as exc:
        log.warning(f"Mailhog GET {path}: {exc}")
        return None


def mailhog_all_messages_v2(limit: int = 50) -> List[Dict]:
    r = mh_get("/api/v2/messages", params={"limit": limit})
    if r and r.status_code == 200:
        return r.json().get("items", [])
    return []


def mailhog_all_messages_v1() -> List[Dict]:
    r = mh_get("/api/v1/messages")
    if r and r.status_code == 200:
        data = r.json()
        return data if isinstance(data, list) else []
    return []


def mailhog_search_v2(query: str) -> List[Dict]:
    r = mh_get("/api/v2/search", params={"kind": "to", "query": query})
    if r and r.status_code == 200:
        return r.json().get("items", [])
    return []


def mailhog_outgoing_smtp() -> None:
    r = mh_get("/api/v2/outgoing-smtp")
    log.debug(f"Mailhog outgoing-smtp: {r.status_code if r else 'err'}")


def mailhog_fetch_message_v1(msg_id: str) -> None:
    r = mh_get(f"/api/v1/messages/{msg_id}")
    log.debug(f"Mailhog v1 message {msg_id}: {r.status_code if r else 'err'}")


def _body_from_mailhog_msg(msg: Dict) -> str:
    """Extract plain-text body from a mailhog message object."""
    try:
        body = msg.get("Content", {}).get("Body", "")
        if body:
            return body
    except Exception:
        pass
    try:
        for part in msg.get("MIME", {}).get("Parts", []):
            b = part.get("Body", "")
            if b:
                return b
    except Exception:
        pass
    return str(msg)


def _extract_vehicle_info(text: str) -> Optional[Tuple[str, str]]:
    """Pull VIN and pincode from an email body string."""
    vin = re.search(r"\b([A-HJ-NPR-Z0-9]{17})\b", text)
    pin = re.search(r"(?:pincode|pin)\s*[:\-]?\s*(\d{4,8})", text, re.IGNORECASE)
    # crAPI emails often have the pin as a plain number after 'PIN'
    if not pin:
        pin = re.search(r"\b(\d{4})\b", text)
    if vin and pin:
        return vin.group(1), pin.group(1)
    return None


def _extract_otp(text: str) -> Optional[str]:
    """Pull OTP from a password-reset email body."""
    m = re.search(r"\b(\d{4,8})\b", text)
    return m.group(1) if m else None


def poll_mailhog_for_vehicle(email: str, retries: int = 4) -> Optional[Tuple[str, str]]:
    """Poll Mailhog until we find a vehicle registration email.

    Returns immediately (None) if Mailhog was unreachable at startup.
    """
    if not SERVICE_STATUS.get("mailhog", True):
        log.warning("  mailhog unreachable — skipping vehicle email poll")
        return None
    for attempt in range(retries):
        time.sleep(2)
        for msg in mailhog_search_v2(email):
            body = _body_from_mailhog_msg(msg)
            info = _extract_vehicle_info(body)
            if info:
                return info
        for msg in mailhog_all_messages_v1():
            if email.lower() in str(msg).lower():
                body = _body_from_mailhog_msg(msg)
                info = _extract_vehicle_info(body)
                if info:
                    return info
        log.debug(f"  no vehicle email yet (attempt {attempt+1}/{retries})")
    return None


def poll_mailhog_for_otp(email: str, retries: int = 3) -> Optional[str]:
    """Poll Mailhog until we find a password-reset OTP email.

    Returns immediately (None) if Mailhog was unreachable at startup.
    """
    if not SERVICE_STATUS.get("mailhog", True):
        log.warning("  mailhog unreachable — skipping OTP poll")
        return None
    for attempt in range(retries):
        time.sleep(2)
        for msg in mailhog_search_v2(email):
            body = _body_from_mailhog_msg(msg)
            if "otp" in body.lower() or "reset" in body.lower() or "password" in body.lower():
                otp = _extract_otp(body)
                if otp:
                    return otp
        log.debug(f"  no OTP email yet (attempt {attempt+1}/{retries})")
    return None


# ---------------------------------------------------------------------------
# Per-user session
# ---------------------------------------------------------------------------


class CRAPISession:
    def __init__(self, user: Dict) -> None:
        self.user = user
        self.token: Optional[str] = None
        self.vehicles: List[Dict] = []
        self.orders: List[int] = []
        self.video_id: Optional[int] = None
        self.session = requests.Session()
        self.session.verify = VERIFY_SSL

    # -- internals -----------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{CRAPI_URL}{path}"

    def _hdrs(self) -> Dict:
        return {"Authorization": f"Bearer {self.token}"}

    def _pause(self) -> None:
        time.sleep(max(0.1, DELAY + random.uniform(-0.1, 0.3)))

    def _get(self, path: str, *, params: Optional[Dict] = None,
             auth: bool = True, **kw) -> Optional[requests.Response]:
        try:
            headers = self._hdrs() if auth else {}
            r = self.session.get(self._url(path), headers=headers, params=params,
                                 timeout=REQUEST_TIMEOUT, **kw)
            self._pause()
            return r
        except Exception as exc:
            log.warning(f"  ← GET {path} raised {type(exc).__name__}: {exc}")
            return None

    def _post(self, path: str, *, json_body: Optional[Dict] = None,
              params: Optional[Dict] = None, files=None,
              auth: bool = True, **kw) -> Optional[requests.Response]:
        try:
            headers = self._hdrs() if auth else {}
            r = self.session.post(self._url(path), headers=headers,
                                  json=json_body, params=params, files=files,
                                  timeout=REQUEST_TIMEOUT, **kw)
            self._pause()
            return r
        except Exception as exc:
            log.warning(f"  ← POST {path} raised {type(exc).__name__}: {exc}")
            return None

    def _put(self, path: str, *, json_body: Optional[Dict] = None,
             auth: bool = True, **kw) -> Optional[requests.Response]:
        try:
            headers = self._hdrs() if auth else {}
            r = self.session.put(self._url(path), headers=headers, json=json_body,
                                 timeout=REQUEST_TIMEOUT, **kw)
            self._pause()
            return r
        except Exception as exc:
            log.warning(f"  ← PUT {path} raised {type(exc).__name__}: {exc}")
            return None

    # -- auth ----------------------------------------------------------------

    def signup(self) -> bool:
        r = self._post("/identity/api/auth/signup", auth=False, json_body={
            "email": self.user["email"],
            "name": self.user["name"],
            "number": self.user["number"],
            "password": self.user["password"],
        })
        ok = r is not None and r.status_code == 200
        log.info(f"  signup {self.user['email']}: {r.status_code if r else 'ERR'}")
        return ok

    def login(self) -> bool:
        r = self._post("/identity/api/auth/login", auth=False, json_body={
            "email": self.user["email"],
            "password": self.user["password"],
        })
        if r is None or r.status_code != 200:
            log.warning(f"  login failed {self.user['email']}: {r.status_code if r else 'ERR'}")
            return False
        data = r.json()
        self.token = data.get("token") or data.get("access_token")
        log.info(f"  login {self.user['email']}: OK")
        return bool(self.token)

    def forgot_password(self) -> None:
        r = self._post("/identity/api/auth/forget-password", auth=False,
                       json_body={"email": self.user["email"]})
        log.info(f"  forgot-password: {r.status_code if r else 'ERR'}")

    def check_otp_v2(self, email: str, otp: str, new_pw: str) -> None:
        r = self._post("/identity/api/auth/v2/check-otp", auth=False,
                       json_body={"email": email, "otp": otp, "password": new_pw})
        log.info(f"  check-otp v2: {r.status_code if r else 'ERR'}")

    def check_otp_v3(self, email: str, otp: str, new_pw: str) -> None:
        r = self._post("/identity/api/auth/v3/check-otp", auth=False,
                       json_body={"email": email, "otp": otp, "password": new_pw})
        log.info(f"  check-otp v3: {r.status_code if r else 'ERR'}")

    # -- user / profile ------------------------------------------------------

    def get_dashboard(self) -> Optional[Dict]:
        r = self._get("/identity/api/v2/user/dashboard")
        if r and r.status_code == 200:
            data = r.json()
            self.video_id = data.get("video_id") or self.video_id
            log.info(f"  dashboard: OK")
            return data
        log.warning(f"  dashboard: {r.status_code if r else 'ERR'}")
        return None

    def change_email(self) -> None:
        new_email = f"chg.{rstr(6)}@{EMAIL_DOMAIN}"
        r = self._post("/identity/api/v2/user/change-email", json_body={
            "new_email": new_email,
            "old_email": self.user["email"],
        })
        log.info(f"  change-email: {r.status_code if r else 'ERR'}")

    def upload_picture(self) -> None:
        files = {"file": ("profile.png", io.BytesIO(MINIMAL_PNG), "image/png")}
        r = self._post("/identity/api/v2/user/pictures", files=files)
        log.info(f"  upload-picture: {r.status_code if r else 'ERR'}")

    def upload_video(self) -> Optional[int]:
        files = {"file": ("profile.mp4", io.BytesIO(MINIMAL_MP4), "video/mp4")}
        r = self._post("/identity/api/v2/user/videos", files=files)
        if r and r.status_code == 200:
            try:
                data = r.json()
                vid_id = data.get("id") or data.get("video_id")
                if vid_id:
                    self.video_id = int(vid_id)
                    log.info(f"  upload-video: OK id={vid_id}")
                    return self.video_id
            except Exception:
                pass
        log.warning(f"  upload-video: {r.status_code if r else 'ERR'} {(r.text[:120] if r else '')}")
        return None

    def get_video(self, video_id: int) -> None:
        r = self._get(f"/identity/api/v2/user/videos/{video_id}")
        log.info(f"  get-video {video_id}: {r.status_code if r else 'ERR'}")

    def update_video(self, video_id: int) -> None:
        r = self._put(f"/identity/api/v2/user/videos/{video_id}",
                      json_body={"video_name": f"clip_{rstr(4)}.mp4"})
        log.info(f"  update-video {video_id}: {r.status_code if r else 'ERR'}")

    def convert_video(self, video_id: int) -> None:
        r = self._get("/identity/api/v2/user/videos/convert_video",
                      params={"video_id": video_id})
        log.info(f"  convert-video {video_id}: {r.status_code if r else 'ERR'}")

    # -- vehicle -------------------------------------------------------------

    def get_vehicles(self) -> List[Dict]:
        r = self._get("/identity/api/v2/vehicle/vehicles")
        if r and r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                self.vehicles = data
                log.info(f"  vehicles: {len(data)} found")
                return data
        log.warning(f"  vehicles: {r.status_code if r else 'ERR'}")
        return []

    def add_vehicle(self, vin: str, pincode: str) -> bool:
        r = self._post("/identity/api/v2/vehicle/add_vehicle",
                       json_body={"vin": vin, "pincode": pincode})
        log.info(f"  add-vehicle vin={vin}: {r.status_code if r else 'ERR'}")
        return r is not None and r.status_code == 200

    def get_vehicle_location(self, vehicle_uuid: str) -> None:
        r = self._get(f"/identity/api/v2/vehicle/{vehicle_uuid}/location")
        log.info(f"  vehicle-location {vehicle_uuid[:8]}…: {r.status_code if r else 'ERR'}")

    def resend_vehicle_email(self) -> None:
        # Do not send a body — some crAPI builds reject an empty JSON object here.
        r = self._post("/identity/api/v2/vehicle/resend_email")
        log.info(f"  resend-vehicle-email: {r.status_code if r else 'ERR'}")

    # -- community -----------------------------------------------------------

    def get_recent_posts(self) -> List[Dict]:
        r = self._get("/community/api/v2/community/posts/recent",
                      params={"limit": 30, "offset": 0})
        if r and r.status_code == 200:
            posts = r.json()
            log.info(f"  recent-posts: {len(posts)} found")
            return posts if isinstance(posts, list) else []
        log.warning(f"  recent-posts: {r.status_code if r else 'ERR'}")
        return []

    def create_post(self) -> Optional[str]:
        r = self._post("/community/api/v2/community/posts", json_body={
            "title": random.choice(POST_TITLES),
            "content": random.choice(POST_CONTENTS),
        })
        if r and r.status_code == 200:
            post_id = r.json().get("id")
            log.info(f"  create-post: id={post_id}")
            return post_id
        log.warning(f"  create-post: {r.status_code if r else 'ERR'}")
        return None

    def get_post(self, post_id: str) -> None:
        r = self._get(f"/community/api/v2/community/posts/{post_id}")
        log.info(f"  get-post {post_id[:8]}…: {r.status_code if r else 'ERR'}")

    def comment_on_post(self, post_id: str) -> None:
        r = self._post(f"/community/api/v2/community/posts/{post_id}/comment",
                       json_body={"content": f"Great post! {rstr(5)}"})
        log.info(f"  comment {post_id[:8]}…: {r.status_code if r else 'ERR'}")

    def validate_coupon(self, code: str) -> None:
        r = self._post("/community/api/v2/coupon/validate-coupon",
                       json_body={"coupon_code": code})
        log.info(f"  validate-coupon {code}: {r.status_code if r else 'ERR'}")

    # -- workshop / shop -----------------------------------------------------

    def get_products(self) -> List[Dict]:
        r = self._get("/workshop/api/shop/products")
        if r and r.status_code == 200:
            data = r.json()
            products = data.get("products", [])
            log.info(f"  products: {len(products)} found")
            return products
        log.warning(f"  products: {r.status_code if r else 'ERR'}")
        return []

    def apply_coupon(self, code: str) -> None:
        r = self._post("/workshop/api/shop/apply_coupon",
                       json_body={"coupon_code": code, "amount": 75})
        log.info(f"  apply-coupon {code}: {r.status_code if r else 'ERR'}")

    def create_order(self, product_id: int, quantity: int = 1) -> Optional[int]:
        r = self._post("/workshop/api/shop/orders",
                       json_body={"product_id": product_id, "quantity": quantity})
        if r and r.status_code == 200:
            order_id = r.json().get("id")
            if order_id:
                self.orders.append(order_id)
                log.info(f"  create-order: id={order_id}")
                return order_id
        log.warning(f"  create-order: {r.status_code if r else 'ERR'} {(r.text[:120] if r else '')}")
        return None

    def get_all_orders(self) -> List[Dict]:
        r = self._get("/workshop/api/shop/orders/all", params={"limit": 30, "offset": 0})
        if r and r.status_code == 200:
            orders = r.json().get("orders", [])
            log.info(f"  all-orders: {len(orders)} found")
            return orders
        log.warning(f"  all-orders: {r.status_code if r else 'ERR'}")
        return []

    def get_order(self, order_id: int) -> None:
        r = self._get(f"/workshop/api/shop/orders/{order_id}")
        log.info(f"  get-order {order_id}: {r.status_code if r else 'ERR'}")

    def return_order(self, order_id: int) -> None:
        r = self._post("/workshop/api/shop/orders/return_order",
                       params={"order_id": order_id})
        log.info(f"  return-order {order_id}: {r.status_code if r else 'ERR'}")

    # -- workshop / mechanic -------------------------------------------------

    def get_mechanics(self) -> List[Dict]:
        r = self._get("/workshop/api/mechanic/")
        if r and r.status_code == 200:
            mechs = r.json().get("mechanics", [])
            log.info(f"  mechanics: {len(mechs)} found")
            return mechs
        log.warning(f"  mechanics: {r.status_code if r else 'ERR'}")
        return []

    def contact_mechanic(self, mechanic_code: str, vin: str) -> Optional[int]:
        receive_url = f"{CRAPI_URL}/workshop/api/mechanic/receive_report"
        r = self._post("/workshop/api/merchant/contact_mechanic", json_body={
            "mechanic_api": receive_url,
            "mechanic_code": mechanic_code,
            "number_of_repeats": 1,
            "repeat_request_if_failed": False,
            "problem_details": random.choice(PROBLEMS),
            "vin": vin,
        })
        if r and r.status_code == 200:
            resp = r.json().get("response_from_mechanic_api", {})
            report_id = resp.get("id")
            log.info(f"  contact-mechanic {mechanic_code}: report_id={report_id}")
            return report_id
        log.warning(f"  contact-mechanic {mechanic_code}: {r.status_code if r else 'ERR'}")
        return None

    def get_mechanic_report(self, report_id: int) -> None:
        r = self._get("/workshop/api/mechanic/mechanic_report",
                      params={"report_id": report_id})
        log.info(f"  mechanic-report {report_id}: {r.status_code if r else 'ERR'}")

    def get_service_requests(self) -> None:
        r = self._get("/workshop/api/mechanic/service_requests",
                      params={"limit": 30, "offset": 0})
        log.info(f"  service-requests: {r.status_code if r else 'ERR'}")

    # -- unauthenticated public endpoints ------------------------------------

    def hit_public_endpoints(self) -> None:
        for path in ["/apidocs", "/api/docs"]:
            r = self._get(path, auth=False)
            log.info(f"  {path}: {r.status_code if r else 'ERR'}")


# ---------------------------------------------------------------------------
# Mailhog traffic (ensures Noname sees the mailhog endpoints as Done)
# ---------------------------------------------------------------------------


def generate_mailhog_traffic() -> None:
    log.info("  [mailhog] hitting all mailhog API endpoints…")
    msgs_v2 = mailhog_all_messages_v2(50)
    mailhog_all_messages_v1()
    mailhog_outgoing_smtp()
    mailhog_search_v2("@")  # broad search to cover /api/v2/search

    # Hit individual message endpoints (v1)
    for msg in msgs_v2[:3]:
        msg_id = msg.get("ID") or msg.get("id")
        if msg_id:
            mailhog_fetch_message_v1(str(msg_id))


# ---------------------------------------------------------------------------
# Full per-user workflow
# ---------------------------------------------------------------------------


def run_user_workflow(user: Dict, first_run: bool) -> None:
    log.info(f"\n  ── user: {user['email']} (first_run={first_run})")
    sess = CRAPISession(user)

    # ── auth ──────────────────────────────────────────────────────────────
    if first_run:
        if not sess.signup():
            log.error(f"  signup failed, skipping user")
            return
        time.sleep(1)

    if not sess.login():
        log.error(f"  login failed, skipping user")
        return

    # ── public endpoints ──────────────────────────────────────────────────
    sess.hit_public_endpoints()

    # ── user dashboard + profile ──────────────────────────────────────────
    sess.get_dashboard()
    sess.upload_picture()

    vid_id = sess.upload_video()
    if vid_id is None:
        vid_id = sess.video_id
    if vid_id:
        sess.get_video(vid_id)
        sess.update_video(vid_id)
        sess.convert_video(vid_id)

    # ── vehicle ───────────────────────────────────────────────────────────
    vehicles = sess.get_vehicles()

    if not vehicles and first_run:
        log.info("  no vehicles yet — checking mailhog for registration email…")
        info = poll_mailhog_for_vehicle(user["email"])
        if info:
            vin, pin = info
            log.info(f"  found VIN={vin} PIN={pin}")
            sess.add_vehicle(vin, pin)
            time.sleep(2)
            vehicles = sess.get_vehicles()

    if not vehicles:
        sess.resend_vehicle_email()
        time.sleep(4)
        info = poll_mailhog_for_vehicle(user["email"])
        if info:
            sess.add_vehicle(*info)
            time.sleep(2)
            vehicles = sess.get_vehicles()

    for v in vehicles[:2]:
        uuid = v.get("uuid")
        if uuid:
            sess.get_vehicle_location(uuid)

    # ── community ─────────────────────────────────────────────────────────
    if not SERVICE_STATUS.get("community", True):
        log.warning("  [SKIP] community service unreachable")
    else:
        posts = sess.get_recent_posts()
        new_post_id = sess.create_post()
        if new_post_id:
            sess.get_post(new_post_id)
            sess.comment_on_post(new_post_id)

        for post in posts[:2]:
            pid = post.get("id")
            if pid and pid != new_post_id:
                sess.get_post(pid)
                sess.comment_on_post(pid)

        for code in COUPON_CODES:
            sess.validate_coupon(code)

    # ── shop ──────────────────────────────────────────────────────────────
    if not SERVICE_STATUS.get("workshop", True):
        log.warning("  [SKIP] workshop service unreachable")
    else:
        sess.apply_coupon("TRAC75")

        products = sess.get_products()
        order_id: Optional[int] = None

        if products:
            prod_id = products[0].get("id")
            if prod_id:
                order_id = sess.create_order(prod_id, 1)

        sess.get_all_orders()

        if order_id:
            sess.get_order(order_id)
            sess.return_order(order_id)

    # ── mechanics ─────────────────────────────────────────────────────────
    if not SERVICE_STATUS.get("workshop", True):
        log.warning("  [SKIP] workshop service unreachable — skipping mechanic endpoints")
    else:
        mechanics = sess.get_mechanics()
        sess.get_service_requests()
        mech_codes = [m.get("mechanic_code") for m in mechanics if m.get("mechanic_code")]
        if not mech_codes:
            mech_codes = ["TRAC_MECH1", "TRAC_MECH2"]

        vin = (vehicles[0].get("vin") if vehicles else None) or "8UOLV89RGKL908077"

        for code in mech_codes[:2]:
            report_id = sess.contact_mechanic(code, vin)
            if report_id:
                time.sleep(1)
                sess.get_mechanic_report(report_id)

    # ── password reset (hits forget-password + check-otp v2/v3) ──────────
    sess.forgot_password()
    time.sleep(3)
    otp = poll_mailhog_for_otp(user["email"])
    new_pw = f"Reset!{rstr(8)}"
    if otp:
        sess.check_otp_v2(user["email"], otp, new_pw)
        # v3 with a deliberately wrong OTP to generate that traffic too
        sess.check_otp_v3(user["email"], "000000", new_pw)
    else:
        # Still hit both endpoints to ensure Noname sees the traffic
        sess.check_otp_v2(user["email"], "123456", new_pw)
        sess.check_otp_v3(user["email"], "123456", new_pw)

    # ── change email ──────────────────────────────────────────────────────
    sess.change_email()

    # ── mailhog API coverage ──────────────────────────────────────────────
    generate_mailhog_traffic()

    log.info(f"  ── done: {user['email']}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="crAPI Noname API Security — Traffic Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--users", type=int, default=NUM_USERS,
                   help="Number of user accounts to create")
    p.add_argument("--iterations", type=int, default=ITERATIONS,
                   help="Number of full traffic cycles (first creates users, rest re-uses them)")
    p.add_argument("--delay", type=float, default=DELAY,
                   help="Base delay in seconds between API calls")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    global DELAY
    DELAY = args.delay

    log.info("=" * 60)
    log.info("crAPI Noname Traffic Generator")
    log.info(f"  crAPI target   : {CRAPI_URL}")
    log.info(f"  Mailhog        : {MAILHOG_URL}")
    log.info(f"  Users          : {args.users}")
    log.info(f"  Iterations     : {args.iterations}")
    log.info(f"  Delay          : {DELAY}s")
    log.info(f"  Request timeout: {REQUEST_TIMEOUT}s")
    log.info("=" * 60)

    check_connectivity()

    if not SERVICE_STATUS.get("identity", False):
        log.error("Identity service is unreachable — cannot proceed. Check crapi_base_url in config.ini.")
        sys.exit(1)

    unreachable = [k for k, v in SERVICE_STATUS.items() if not v]
    if unreachable:
        log.warning(f"Unreachable services: {unreachable} — their endpoints will be skipped")

    users = [make_user() for _ in range(args.users)]
    log.info(f"Generated {len(users)} user profiles")

    for iteration in range(args.iterations):
        log.info(f"\n{'═'*60}")
        log.info(f"  ITERATION {iteration + 1} / {args.iterations}")
        log.info(f"{'═'*60}")
        first_run = iteration == 0
        for idx, user in enumerate(users, 1):
            log.info(f"\n[user {idx}/{len(users)}]")
            run_user_workflow(user, first_run=first_run)
            time.sleep(random.uniform(0.5, 1.5))

    log.info("\n" + "=" * 60)
    log.info("Traffic generation complete.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
