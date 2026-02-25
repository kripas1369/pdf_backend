# App Analytics: Users, PDF Views, Time Spent, and Topic Usage

This document explains **how you can know**:
- How many users use the app
- How many times PDFs are viewed and how much time is spent
- Which PDF topics are viewed most

It also describes **what the Flutter app must do** so the backend can record this data.

---

## 1. What the Backend Tracks (once Flutter sends it)

| Metric | Where it's stored | Where you see it in Django Admin |
|--------|-------------------|-----------------------------------|
| **Total users** | `User` model | **Users** list (total count; filter by `is_active`) |
| **Users who have used the app** | Users with `first_opened_at` set or with `UserActivity` / `UserTopicUsage` records | Users list; filter or sort by `first_opened_at`; or **User activity** / **User topic usage** lists |
| **PDF views per user** | `User.pdf_views_count` (lifetime) and `UserActivity.pdfs_viewed` (per day) | **Users** → open a user → see **pdf_views_count**; or **User activity** list for per-day breakdown |
| **Time spent in app** | `UserActivity.time_spent_minutes` per user per day | **User activity** list; or **Users** → inline not shown by default but data is there |
| **Which topic is viewed** | `UserTopicUsage` (user, topic, date, usage_count, time_spent_minutes) | **User topic usage** list; **Topics** list (columns “Topic usage” and “Unique users”); **Users** → inline “Topic usage” |

So:
- **How many users use the app:** Count users (e.g. with `first_opened_at` not null, or with at least one `UserActivity` or `UserTopicUsage`). You can do this in Admin by going to **Users** and using filters/search, or add a custom admin view/dashboard if you want a single number.
- **How many times / how much time PDFs are viewed:** Per user: **Users** → **pdf_views_count** (lifetime). Per day: **User activity** → **pdfs_viewed** and **time_spent_minutes**.
- **Which PDF topic is viewed:** **Topics** list shows “Topic usage” and “Unique users” per topic. **User topic usage** list shows each (user, topic, date) with **usage_count** and **time_spent_minutes**.

---

## 2. Where to See It in Django Admin

- **Users** (`/admin/pdf_app/user/`)  
  - Columns: phone, name, **pdf_views_count**, **first_opened_at**, etc.  
  - Use this for “how many users” and “total PDF views per user”.

- **User activity** (`/admin/pdf_app/useractivity/`)  
  - Per user, per day: **pdfs_viewed**, **time_spent_minutes**, messages_sent.  
  - Use this for “how many PDF views and how much time per day”.

- **User topic usage** (`/admin/pdf_app/usertopicusage/`)  
  - Per user, per topic, per day: **usage_count**, **time_spent_minutes**.  
  - Use this for “which topic is viewed” and “how much per topic”.

- **Topics** (`/admin/pdf_app/topic/`)  
  - Columns: **Topic usage** (total usage_count + time_spent_minutes) and **Unique users** (count of distinct users who used that topic).  
  - Use this for “which PDF topic is viewed” at a glance.

---

## 3. What Flutter Must Do (tracking that feeds these numbers)

The backend **does not** know about PDF opens or topic opens until the Flutter app sends them. All of the above metrics depend on the app calling the usage API with the right payload.

### 3.1 API to call: `POST /api/usage/log/`

- **When to call:** When the app goes to background, or periodically (e.g. every 5 minutes), or when the user leaves a screen. Same request can include time, PDF count, and topic usage.
- **Auth:** Required (Bearer token).

### 3.2 Request body (JSON)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `time_spent_minutes` | int | No* | Minutes spent in app in this session |
| `time_spent_seconds` | int | No | Alternative (converted to minutes) |
| **`pdfs_viewed`** | **int** | **No** | **Number of PDFs viewed in this session** (so we can count “how many times PDF is viewed”) |
| **`topic_usage`** | **array** | **No** | **Which topics were viewed (see below)** |

\* At least one of: `time_spent_minutes`, `time_spent_seconds`, `pdfs_viewed`, or `topic_usage` must be sent.

### 3.3 `topic_usage` (which PDF topic is viewed)

Each element is an object:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topic_id` | int | Yes | Topic ID from `/api/topics/` (PDF’s subject belongs to a topic) |
| `usage_count` | int | No (default 1) | Number of times user opened/viewed this topic (or PDFs under it) in this session |
| `time_spent_minutes` | int | No (default 0) | Minutes spent in this topic in this session |

- No duplicate `topic_id` in one request (one entry per topic per request).
- Multiple topics allowed in one request (e.g. Physics and Math).

**Example (full):**

```json
{
  "time_spent_minutes": 15,
  "pdfs_viewed": 3,
  "topic_usage": [
    { "topic_id": 1, "usage_count": 2, "time_spent_minutes": 10 },
    { "topic_id": 2, "usage_count": 1, "time_spent_minutes": 5 }
  ]
}
```

**Example (only topic, e.g. user opened topic screen):**

```json
{
  "topic_usage": [
    { "topic_id": 5, "usage_count": 1 }
  ]
}
```

### 3.4 Flutter implementation checklist

1. **When user opens a PDF**  
   - Increment a session counter for “PDFs viewed” and, from the PDF’s subject, get `topic_id` and add it to the session’s topic usage (increment `usage_count` for that `topic_id`; optionally add time when they leave the PDF/screen).

2. **When user opens a topic** (e.g. from topic list) or a subject under a topic  
   - Add that topic to session topic usage (e.g. `usage_count` += 1; optionally track time on that screen).

3. **Session accumulation**  
   - Keep in memory for the current session:
     - Total PDFs viewed (number).
     - Per topic: `usage_count` and optionally `time_spent_minutes`.

4. **When sending usage** (on background, periodically, or on screen leave)  
   - Call `POST /api/usage/log/` with:
     - `time_spent_minutes` and/or `time_spent_seconds` (app/session time),
     - `pdfs_viewed` (session PDF view count),
     - `topic_usage`: list of `{ "topic_id": id, "usage_count": count, "time_spent_minutes": mins }` for each topic used in the session.
   - After a successful log, clear or reset the in-memory session counters so the next session doesn’t double-count.

5. **Minimal option**  
   - If you don’t track time per topic, still send `topic_usage` with at least `topic_id` and `usage_count` (e.g. 1 when user opens a topic or views a PDF under that topic). That is enough for “which PDF topic is viewed.”

If Flutter does the above, you get:
- **How many users use the app:** From Users + first_open/activity.
- **How many times PDF is viewed / how much time:** From `pdfs_viewed` and `time_spent_minutes` (and User.pdf_views_count, UserActivity).
- **Which PDF topic is viewed:** From `topic_usage` (UserTopicUsage and Topics admin).

---

## 4. Optional: “First opened app” and new users

- **first_opened_at:** Set by the backend when the user registers (or on first login, depending on your flow). Used to know “users who have opened the app at least once.”
- Flutter does not need to send anything extra for “first opened”; ensure your app triggers the normal login/register flow so the backend can set it.

---

## 5. Summary for Flutter developer

- **Endpoint:** `POST /api/usage/log/` (authenticated).
- **Send:**
  - `pdfs_viewed`: number of PDFs viewed in the current session.
  - `topic_usage`: list of `{ "topic_id": <id>, "usage_count": <n>, "time_spent_minutes": <m> }` for each topic the user opened or viewed (e.g. when opening a topic screen or viewing a PDF under that topic).
  - Optionally `time_spent_minutes` / `time_spent_seconds` for app/session time.
- **When:** On background, periodically, or when leaving a screen; then clear session counters after a successful log.

More detail for Flutter (including examples and minimal implementation) is in **FLUTTER_TOPIC_USAGE_TASK.md**.
