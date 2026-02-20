# Flutter: Blue Tick Verification – Developer Tasks

Users can have a **verified** (blue tick) account. The backend sets this when:
- The user **buys any paid package** (subscription, single PDF, subject/topic/year/full package) and admin approves the payment, **or**
- Admin **manually verifies** the account from Django Admin.

Use this doc to show the blue tick in the Flutter app wherever the current user or another user is displayed.

**Feature name in app:** Verified account / Blue tick

**Backend:** User model has `is_verified` (boolean). It is exposed in all user/profile responses.

---

## API Summary

| What | Change |
|------|--------|
| **Login response** | `user` object now includes `is_verified` (boolean). |
| **Profile / me** | Same: `is_verified` in the user object. |
| **Any endpoint that returns a user** | Include `is_verified` so you can show the blue tick next to that user (e.g. post author, comment author). |

### User object (in login, profile, or nested in feed/comment)

```json
{
  "id": 5,
  "phone": "+9779812345678",
  "name": "John",
  "referral_code": "SATHI23456842",
  "is_verified": true,
  "pdf_views_count": 10,
  "days_since_install": 30,
  "has_profile": true,
  "subscription_tier": "GOLD",
  "messages_remaining": 50,
  "created_at": "2026-01-15T10:00:00Z"
}
```

- **`is_verified`** – `true` = show blue tick next to this user’s name/avatar; `false` = no tick.
- This field is **read-only** for the app (only backend/admin can set it).

---

## Where to Show the Blue Tick

- **Current user:** Profile screen, app bar, drawer header (e.g. name + optional blue tick).
- **Other users:** Any place you show another user’s identity:
  - **TU Notice Feed:** Next to post author (e.g. “Posted by 98***678” + tick if that user is verified).
  - **Comments:** Next to comment author name/phone.
  - **Study groups / chat / any “created by” or “author”** – show tick when that user’s `is_verified` is true.

If the API returns a **user object** (with `is_verified`), use it. If it only returns `created_by` (user id) or `created_by_phone`, you may need a small backend change to include `created_by_verified` for list/detail (or the full user); until then, you can show the tick only for the **current user** on profile/header.

---

## Flutter Tasks

### 1. Data layer

- [ ] Add **`isVerified`** (bool) to your **User** (or AuthUser) model.
- [ ] Parse **`is_verified`** from:
  - Login response `user`
  - Profile / me response
  - Any other API that returns user data.
- [ ] After login or profile fetch, persist/update `isVerified` in your auth state (e.g. shared preferences, provider, bloc) so the whole app can read it.

### 2. Current user – Profile / Header

- [ ] On **Profile** (or “Me”) screen: show blue tick next to the user’s name (or phone) when `isVerified == true`.
- [ ] In **app bar** or **drawer header** where you show the logged-in user’s name: show blue tick when verified.
- [ ] Use a small icon (e.g. checkmark badge or verified icon) in your design system; keep it consistent across the app.

### 3. TU Notice Feed – Post author

- [ ] In feed list and post detail, where you show the **post author** (e.g. “Posted by 98***678”):
  - If the API returns author’s **`is_verified`** (or a nested user with `is_verified`), show the blue tick next to the author label when `is_verified == true`.
  - If the API does **not** yet return verification for the author, you can:
    - **Option A:** Ask backend to add `created_by_verified` (or include minimal user with `is_verified`) in feed post payload.
    - **Option B:** Only show blue tick for the **current user** until backend is extended.

### 4. Comments – Comment author

- [ ] Where you display **comment author** (name/phone):
  - If the comment payload includes **`is_verified`** for the commenter (or user object), show blue tick when true.
  - If not, follow same approach as feed (request backend to add it, or show only for current user).

### 5. Other screens

- [ ] **Study groups / any “created by” or member list:** If the API returns user objects with `is_verified`, show blue tick next to verified users.
- [ ] **Settings / Account:** You can add a short line like “Verified account” with the blue tick when `isVerified == true`; no tick when false.

### 6. Asset and styling

- [ ] Add a **verified / blue tick** icon (e.g. small checkmark in a circle, or your preferred style). Use a consistent color (e.g. blue `#1d9bf0` or your brand blue).
- [ ] Ensure the tick is visible but not overwhelming (small, next to name or avatar).
- [ ] Handle **accessibility**: e.g. semantic label “Verified account” for the icon.

### 7. No backend change required for “current user only”

- [ ] You can ship **current user** blue tick (profile + header) using only **login** and **profile/me** responses; both already include `is_verified`.

---

## Backend Support (for showing tick on others)

- **Already available:** `user` in login and profile has `is_verified`.
- **Optional (for feed/comment authors):** If you want to show the tick next to **post author** or **comment author**, the backend can add:
  - In **feed post** (list/detail): e.g. `created_by_verified` (boolean), or nested `created_by_user: { id, phone, is_verified }`.
  - In **comment** (list): e.g. `commenter_verified` or nested user with `is_verified`.

If those fields are not yet in the API, Flutter can still implement the tick for the **current user** everywhere (profile, header, account).

---

## Summary

| Task | Description |
|------|-------------|
| Model & API | Add `isVerified` to User model; parse from login, profile, and any user payload |
| Profile / Header | Show blue tick next to current user’s name when `isVerified == true` |
| Feed author | Show blue tick next to post author when API provides `is_verified` (or `created_by_verified`) |
| Comment author | Show blue tick next to comment author when API provides verification |
| Icon & UX | Add verified icon; consistent size/color; optional “Verified account” label for a11y |
| Other screens | Use `is_verified` wherever you display a user (groups, members, etc.) |

**Minimal ship:** Implement blue tick for the **current user** on profile and app bar using existing `user.is_verified` from login/profile. Then extend to feed and comments when backend exposes verification for post/comment authors.
