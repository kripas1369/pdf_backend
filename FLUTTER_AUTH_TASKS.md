# Flutter Auth Integration Tasks

Backend authentication has been updated. **OTP is now used only for forgot password**, not for login or registration.

---

## New Auth Flow Summary

| Action | Method | OTP Used? |
|--------|--------|-----------|
| Register | Phone + Password | No |
| Login | Phone + Password | No |
| Forgot Password | OTP (SMS when configured) | Yes (only here) |

---

## API Changes

### REMOVED (do not use anymore)
- `POST /api/auth/send-otp/` (was for login)
- `POST /api/auth/verify-otp/` (was for login/register)

### NEW / UPDATED

#### 1. Register
- **Endpoint:** `POST /api/auth/register/`
- **Body:** `{ "phone": "+977XXXXXXXXX", "password": "min6chars", "name": "optional", "referral_code": "optional" }`
- **Response:** `{ "access", "refresh", "user" }` (JWT tokens + user object)
- **Errors:** 400 if phone already registered

#### 2. Login
- **Endpoint:** `POST /api/auth/login/`
- **Body:** `{ "phone": "+977XXXXXXXXX", "password": "..." }`
- **Response:** `{ "access", "refresh", "user" }`
- **Errors:** 401 if invalid phone or password

#### 3. Forgot Password – Send OTP
- **Endpoint:** `POST /api/auth/forgot-password/send-otp/`
- **Body:** `{ "phone": "+977XXXXXXXXX" }`
- **Response:** `{ "message": "OTP sent...", "phone": "..." }`
- **Errors:** 404 if no account with that phone; 429 if too many requests (max 3/hour)

#### 4. Forgot Password – Reset
- **Endpoint:** `POST /api/auth/forgot-password/reset/`
- **Body:** `{ "phone": "+977XXXXXXXXX", "otp": "123456", "new_password": "min6chars" }`
- **Response:** `{ "message": "Password reset successfully..." }`
- **Errors:** 400 if invalid/expired OTP

#### 5. Logout
- **Endpoint:** `POST /api/auth/logout/`
- **Body:** `{ "refresh": "<refresh_token>" }` (the same refresh token you got from login/register)
- **Response (200):** `{}` or `{ "detail": "Successfully logged out." }`
- **Errors:** 400 if refresh token missing/invalid or already blacklisted
- **Flutter:** After a successful logout call, **clear both access and refresh tokens** from local storage (e.g. secure_storage). The server blacklists the refresh token so it cannot be used for `/auth/refresh/` anymore.

#### 6. Unchanged
- `POST /api/auth/refresh/` – get new access token using refresh token
- `GET /api/auth/me/` – current user (requires Bearer access token)
- `PATCH /api/auth/update/` – update name (requires Bearer access token)

---

## Token lifetime (session timeout)

| Token   | Lifetime | Notes |
|---------|----------|--------|
| Access  | **3 days** | After 3 days the access token expires; use refresh token to get a new one. |
| Refresh | 30 days | Use for `POST /api/auth/refresh/`. After logout, refresh is blacklisted. |

---

## Flutter Tasks Checklist

### 1. Registration Screen
- [ ] Phone input (format: +977XXXXXXXXX)
- [ ] Password input (min 6 chars)
- [ ] Optional name input
- [ ] Optional referral code input
- [ ] Call `POST /api/auth/register/`
- [ ] Store tokens and user; navigate to home
- [ ] Show error if phone already registered

### 2. Login Screen
- [ ] Phone input
- [ ] Password input
- [ ] Call `POST /api/auth/login/`
- [ ] Store tokens and user; navigate to home
- [ ] Show error for invalid credentials
- [ ] Add "Forgot Password?" link

### 3. Forgot Password Flow
- [ ] Screen 1: Phone input only
- [ ] Call `POST /api/auth/forgot-password/send-otp/`
- [ ] Show error if phone not found (404)
- [ ] Screen 2: OTP input + New password + Confirm password
- [ ] Call `POST /api/auth/forgot-password/reset/` with phone, otp, new_password
- [ ] On success, navigate to login and show "Password reset successfully"
- [ ] Handle OTP expiry / invalid OTP errors

### 4. Remove Old OTP Login
- [ ] Remove any UI that sends OTP for login
- [ ] Remove any UI that verifies OTP for login/register
- [ ] Remove calls to `/api/auth/send-otp/` and `/api/auth/verify-otp/` for login/register

### 5. Token Handling
- [ ] Store access + refresh tokens securely (e.g. flutter_secure_storage)
- [ ] Send `Authorization: Bearer <access_token>` for protected APIs
- [ ] Access token expires in **3 days**; on 401 use refresh token with `POST /api/auth/refresh/` then retry
- [ ] **Logout:** Call `POST /api/auth/logout/` with body `{ "refresh": "<refresh_token>" }`, then **clear both tokens** from storage and go to login screen

---

## Phone Format

Always use `+977` followed by 10 digits (e.g. `+9779841234567`). Backend normalizes numbers; send in consistent format from Flutter.

---

## Password Rules

- Minimum 6 characters (enforced on register and reset)
