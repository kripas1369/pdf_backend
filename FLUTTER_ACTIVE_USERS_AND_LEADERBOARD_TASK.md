# Flutter Task: Active Online Users & PDF Time Leaderboard

This document describes the **two new backend APIs** and the **Flutter developer tasks** to show active online users and the PDF time-spent leaderboard in the app.

---

## 1. Active Online Users

### Backend APIs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `POST /api/presence/heartbeat/` | POST | **Required** (Bearer) | Call while app is in foreground so this user is counted as "online". |
| `GET /api/presence/active-count/?minutes=5` | GET | **Not required** | Returns count of users with `last_seen` in the last N minutes (default 5). |

#### POST `/api/presence/heartbeat/`

- **When to call:** Every **1–2 minutes** while the app is in **foreground** (user is actively using the app).
- **Headers:** `Authorization: Bearer <access_token>`
- **Body:** None (or empty JSON `{}`).
- **Response:** `{ "status": "ok" }`

**Note:** The backend also updates `last_seen` when the app calls `POST /api/usage/log/` (e.g. on background or when leaving a screen). So users who send usage are also counted as online. For more accurate real-time count, call the heartbeat every 1–2 minutes in addition to usage log.

#### GET `/api/presence/active-count/`

- **Query params:** `minutes` (optional, default `5`) – consider "online" if `last_seen` within this many minutes.
- **Auth:** Not required (so you can show "X users online" on home or before login if desired).
- **Response:** `{ "active_count": 12 }`

### Flutter tasks for active online users

1. **Heartbeat timer**
   - When the app is in foreground and the user is logged in, start a periodic timer (e.g. every 90 seconds).
   - On each tick, call `POST /api/presence/heartbeat/` with the current auth token.
   - Cancel the timer when the app goes to background or the user logs out.
   - Use `WidgetsBindingObserver` (or your app lifecycle) to pause/resume the timer with app state.

2. **Fetch and show active count**
   - Decide where to show "X users online" (e.g. home screen, dashboard, or a small badge).
   - Call `GET /api/presence/active-count/` when that screen is visible. Optionally refresh every 1–2 minutes while the screen is open.
   - Display `response['active_count']` (e.g. "12 users online" or "12 online").

3. **Error handling**
   - If heartbeat fails (e.g. network error), do not show an error to the user; optionally retry on next tick.
   - If active-count fails, either hide the "online" widget or show a placeholder (e.g. "— online").

---

## 2. PDF Time Leaderboard

### Backend API

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `GET /api/leaderboard/pdf-time/?limit=50&period=all` | GET | **Not required** | Returns leaderboard of users by total time spent in app (PDF reading). |

#### GET `/api/leaderboard/pdf-time/`

- **Query params:**
  - `limit` (optional): Number of top users to return. Default `50`, max `100`.
  - `period` (optional): `all` | `week` | `month`. Default `all`.
    - `all` – total time ever.
    - `week` – time in the last 7 days.
    - `month` – time in the last 30 days.

- **Response:** JSON array of objects:

```json
[
  {
    "rank": 1,
    "display_name": "Ram Sharma",
    "total_minutes": 420,
    "total_pdfs_viewed": 45,
    "is_verified": true
  },
  {
    "rank": 2,
    "display_name": "Anonymous",
    "total_minutes": 380,
    "total_pdfs_viewed": 32,
    "is_verified": false
  }
]
```

- Only users with at least 1 minute of tracked time are included.
- `display_name` is the user’s name, or `"Anonymous"` if no name is set.
- `is_verified` can be used to show a badge (e.g. blue tick) next to the name.

### Flutter tasks for leaderboard

1. **Leaderboard screen (or section)**
   - Add a screen or tab/section for "Study leaderboard" / "Top readers" / "PDF time leaderboard".
   - Call `GET /api/leaderboard/pdf-time/?limit=50&period=all` (or let the user choose `period`: All time / This week / This month).
   - Display a list: rank (e.g. #1, #2), display name (with optional verified badge), total minutes (e.g. "7h 0m" or "420 min"), and optionally total PDFs viewed.

2. **Formatting**
   - Convert `total_minutes` to a readable string (e.g. "7h 30m" or "450 min").
   - Optionally show `total_pdfs_viewed` as "45 PDFs viewed".

3. **Highlight current user**
   - If the leaderboard is shown to a logged-in user, you can call `GET /api/usage/summary/` for the current user to get their total time and compare. Then find their rank by matching their total with the leaderboard list, or add a backend endpoint later that returns "my_rank" and "my_total_minutes" for the current user. For now, you can:
     - Show the list and optionally show "Your stats" elsewhere (from usage/summary) without exact rank, or
     - Compute rank on the client by comparing current user’s total with the list (if their total is in the top N).

4. **Empty / loading state**
   - Show a loading indicator while fetching.
   - If the list is empty, show a message like "No data yet" or "Be the first to appear on the leaderboard."

---

## Summary for Flutter

| Feature | API | Flutter action |
|--------|-----|----------------|
| **Active online users** | `POST /api/presence/heartbeat/` | Call every 1–2 min in foreground when logged in. |
| **Active online users** | `GET /api/presence/active-count/?minutes=5` | Fetch and show "X users online" on home/dashboard. |
| **PDF time leaderboard** | `GET /api/leaderboard/pdf-time/?limit=50&period=all` | New leaderboard screen; show rank, name, time, PDFs; optional period filter and current user highlight. |

Base URL: use your existing API base (e.g. `https://your-domain.com/api/`). All paths above are relative to that base.
