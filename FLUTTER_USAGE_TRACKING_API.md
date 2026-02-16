# App usage tracking API (Flutter)

**Base URL:** `/api/`  
**Auth:** Required for both endpoints. Use: `Authorization: Bearer <access_token>`.

---

## Why track usage

- Know how long each user spends in the app (per day and total).
- Use for analytics, engagement, or premium limits (e.g. “X minutes per day”).

---

## 1. Report usage (log app time)

**Endpoint:** `POST /api/usage/log/`  
**Auth:** Required (JWT).  
**Content-Type:** `application/json`

Call this when the user leaves the app (e.g. app to background), when they leave a screen, or on a timer (e.g. every 5 minutes). Time is accumulated **per user per day** (server date).

**Request body (JSON) – at least one of the following:**

| Field                | Type   | Required | Description |
|----------------------|--------|----------|-------------|
| `time_spent_minutes` | int    | No*      | Minutes spent in app in this session (0–1440). |
| `time_spent_seconds` | int    | No*      | Alternatively, seconds spent (0–86400); converted to minutes. |
| `pdfs_viewed`        | int    | No*      | Optional: number of PDFs viewed in this session to add. |

\* At least one of `time_spent_minutes`, `time_spent_seconds`, or `pdfs_viewed` must be sent (and > 0).

**Examples:**

```json
{ "time_spent_minutes": 5 }
```

```json
{ "time_spent_seconds": 300 }
```

```json
{ "time_spent_minutes": 2, "pdfs_viewed": 3 }
```

**Success:** `201 Created` with body:

```json
{
  "message": "Usage logged",
  "today_minutes": 12,
  "today_pdfs_viewed": 5
}
```

**Errors:** `400` if body is invalid or all values are 0.

---

## 2. Get usage summary

**Endpoint:** `GET /api/usage/summary/`  
**Auth:** Required (JWT).  
**Query params:** `days` (optional) – number of days to return (default 30, max 365).

**Success:** `200 OK` with body:

```json
{
  "by_date": [
    {
      "date": "2026-02-15",
      "pdfs_viewed": 5,
      "messages_sent": 0,
      "time_spent_minutes": 12
    },
    {
      "date": "2026-02-14",
      "pdfs_viewed": 3,
      "messages_sent": 2,
      "time_spent_minutes": 8
    }
  ],
  "total_time_minutes": 120,
  "total_pdfs_viewed": 45
}
```

- `by_date`: list of daily activity (most recent first), up to `days` entries.
- `total_time_minutes`: all-time total minutes for this user.
- `total_pdfs_viewed`: all-time total PDFs viewed for this user.

---

## Flutter implementation notes

1. **When to call `POST /api/usage/log/`**
   - On app pause / going to background (e.g. `WidgetsBindingObserver.didChangeAppLifecycleState`).
   - On a timer (e.g. every 5 minutes) while the app is in foreground.
   - Optionally when leaving a “session” (e.g. closing PDF reader).

2. **What to send**
   - Track session start time when app opens or user returns; on log, send `time_spent_seconds` or `time_spent_minutes` for that session.
   - Optionally increment a “PDFs viewed” counter and send `pdfs_viewed` with the same request.

3. **Summary screen**
   - Use `GET /api/usage/summary/?days=30` to show “Last 30 days” and totals (e.g. total time, total PDFs viewed).

4. **Date**
   - Server uses its own date (UTC) for “today”; no need to send date from the client.

---

## Summary

| Method | Endpoint              | Auth   | Purpose                          |
|--------|------------------------|--------|----------------------------------|
| POST   | `/api/usage/log/`     | Required | Report session time (and optional PDFs viewed) |
| GET    | `/api/usage/summary/` | Required | Get user’s usage by day and totals |
