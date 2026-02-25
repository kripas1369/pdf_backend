# Forgot Password (OTP) — Flutter Testing Task

**Backend:** Forgot-password uses **two APIs**. OTP is sent via **SMS (AakashSMS)** when the server is configured. Use the flows below to implement and test the feature in the Flutter app.

---

## API base

- **Base URL:** `https://your-domain.com/api/` (e.g. `https://pdfserver.nest.net.np/api/`)
- **Auth:** None required for forgot-password (public endpoints).

---

## 1. Send OTP

**POST** `/api/auth/forgot-password/send-otp/`  
**Content-Type:** `application/json`

### Request body

| Field   | Type   | Required | Notes |
|--------|--------|----------|--------|
| `phone` | string | Yes      | Same format as login/register (e.g. `9841234567` or `+9779841234567`). Backend normalizes to `+977...`. |

### Example request

```json
{
  "phone": "9841234567"
}
```

### Success: 200 OK

```json
{
  "message": "OTP sent successfully",
  "phone": "+9779841234567"
}
```

- **SMS:** User receives a 6-digit OTP on this number (via AakashSMS when configured).
- **OTP validity:** 5 minutes (backend).
- **Rate limit:** Max 3 OTP requests per phone per hour; after that user gets 429.

### Error responses

| Status | Body (example) | Flutter action |
|--------|----------------|----------------|
| 400 | `{"phone": ["Invalid phone number format"]}` | Show “Invalid phone number”. |
| 404 | `{"error": "No account found with this phone number"}` | Show “No account found with this number. Please register first.” |
| 429 | `{"error": "Too many OTP requests. Please try after 1 hour."}` | Show “Too many attempts. Try again after 1 hour.” |
| 500 | `{"error": "Failed to send OTP. Please try again."}` | Show “Could not send OTP. Please try again.” |

---

## 2. Reset password (verify OTP + set new password)

**POST** `/api/auth/forgot-password/reset/`  
**Content-Type:** `application/json`

### Request body

| Field           | Type   | Required | Notes |
|----------------|--------|----------|--------|
| `phone`        | string | Yes      | Same value used in “Send OTP”. |
| `otp`          | string | Yes      | 6-digit code from SMS. |
| `new_password` | string | Yes      | Min 6 characters (same rule as registration). |

### Example request

```json
{
  "phone": "9841234567",
  "otp": "123456",
  "new_password": "newSecurePass123"
}
```

### Success: 200 OK

```json
{
  "message": "Password reset successfully. You can now login."
}
```

- Navigate to login and show a short success message (e.g. “Password reset. You can now log in.”).

### Error responses

| Status | Body (example) | Flutter action |
|--------|----------------|----------------|
| 400 | `{"error": "Invalid OTP"}` | “Wrong OTP. Check the code and try again.” |
| 400 | `{"error": "OTP expired or already used"}` | “This code has expired or was already used. Request a new OTP.” |
| 400 | `{"new_password": ["Ensure this field has at least 6 characters."]}` | “Password must be at least 6 characters.” |
| 404 | `{"error": "User not found"}` | Show generic error and option to register. |

---

## Flutter: What to build and test

### Screens / flow

1. **Forgot password entry**
   - One field: **phone** (same format as login/register).
   - Button: “Send OTP” → call **POST** `/api/auth/forgot-password/send-otp/`.
   - Handle 200, 400, 404, 429, 500 and show the messages from the table above.

2. **OTP + new password**
   - After “OTP sent” success:
     - Show fields: **OTP** (6 digits), **New password**, **Confirm password** (optional but recommended).
     - Button: “Reset password” → call **POST** `/api/auth/forgot-password/reset/` with `phone`, `otp`, `new_password`.
   - On 200: show success and navigate to login.
   - On 400: show “Invalid OTP” or “OTP expired or already used” or validation error for `new_password`.

### Testing checklist

- [ ] **Send OTP**
  - Use a **registered** phone number → must get 200 and “OTP sent successfully”; user receives SMS with 6-digit OTP.
  - Use an **unregistered** phone → must get 404 “No account found with this phone number”.
  - Use invalid phone (e.g. too short) → must get 400 “Invalid phone number format”.
  - Send OTP 4+ times in quick succession for same phone → must get 429 “Too many OTP requests” after 3rd request.

- [ ] **Reset password**
  - With correct OTP and `new_password` (≥6 chars) → 200 and “Password reset successfully”; then login with same phone + new password works.
  - With wrong OTP → 400 “Invalid OTP”.
  - With expired or already-used OTP → 400 “OTP expired or already used”.
  - With `new_password` &lt; 6 characters → 400 with validation error on `new_password`.

- [ ] **UX**
  - Show loading state on “Send OTP” and “Reset password”.
  - Show clear error messages from the API (no generic “Something went wrong” when API returns a specific message).
  - After success, redirect to login and optionally pre-fill phone.

### Phone format (for reference)

- Backend accepts: `9841234567`, `9779841234567`, `+9779841234567`.
- It normalizes to `+977...` and sends SMS to the 10-digit number. Use the same format as in login/register in your app.

---

## Summary for Flutter dev

| Step | Endpoint | Method | Body |
|------|----------|--------|------|
| 1. Send OTP | `/api/auth/forgot-password/send-otp/` | POST | `{"phone": "9841234567"}` |
| 2. Reset password | `/api/auth/forgot-password/reset/` | POST | `{"phone": "9841234567", "otp": "123456", "new_password": "yourNewPass"}` |

Use a **real registered phone number** to confirm SMS delivery (AakashSMS). For quick tests without SMS, backend can log OTP to terminal when `DEBUG_PRINT_OTP` is True—ask backend dev for the log if needed.
