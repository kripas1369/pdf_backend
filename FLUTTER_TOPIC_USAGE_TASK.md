# Flutter: Topic Usage Tracking (for Admin Analytics)

## Goal

The backend now tracks **which topic each user uses** so that admins can see:
- Which topics are most used in the app (Topic list in Django admin shows "Topic usage" and "Unique users").
- Which user used which topic (User admin shows "Topic usage" inline; **User topic usage** list shows all records).

To make this work, the **Flutter app must send topic usage** when the user spends time in a topic or opens/views content under that topic.

---

## API to Use: Existing Usage Log (extended)

**Endpoint:** `POST /api/usage/log/`  
**Auth:** Required (Bearer token)

**When to call:** Same as now (e.g. when app goes to background, or periodically, or when user leaves a screen). In the same request, include optional **topic_usage** so the backend can attribute usage to topics.

### Request body (JSON)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `time_spent_minutes` | int | No* | Minutes spent in app in this session |
| `time_spent_seconds` | int | No | Alternative to minutes (converted to minutes) |
| `pdfs_viewed` | int | No | Number of PDFs viewed in this session |
| **`topic_usage`** | **array** | **No** | **List of topic usage items (see below)** |

*At least one of `time_spent_minutes`, `time_spent_seconds`, `pdfs_viewed`, or `topic_usage` must be sent.

### `topic_usage` item

Each element is an object:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topic_id` | int | Yes | ID of the topic (from `/api/topics/` list) |
| `usage_count` | int | No (default 1) | Number of times user opened/viewed this topic in this session (e.g. opened topic screen, or viewed a PDF under this topic) |
| `time_spent_minutes` | int | No (default 0) | Minutes spent in this topic in this session |

- **No duplicate `topic_id`** in one request (each topic at most once per request).
- You can send multiple topics in one request if the user interacted with several (e.g. opened Physics and Math).

### Example request (with topic usage)

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

### Example (topic only, e.g. user only opened topic list / topic screen)

```json
{
  "topic_usage": [
    { "topic_id": 5, "usage_count": 1 }
  ]
}
```

---

## What to Implement in Flutter

1. **Track topic context in the app**
   - When the user opens a **topic** (e.g. from topic list → selects "Physics"), store the current `topic_id` (and topic name if needed).
   - When the user views a **PDF**, you already know its subject → subject has `topic` (topic_id). So you can associate that view with a topic.

2. **Accumulate topic usage per session**
   - Keep a map (e.g. `Map<int, { count: int, minutes: int }>`) for the current session:
     - When user opens a topic screen or enters a topic: increment `usage_count` for that `topic_id`.
     - Optionally: when user is on a topic/screen, track time spent there and add to `time_spent_minutes` for that `topic_id`.

3. **Send topic_usage in the existing usage log call**
   - When you call `POST /api/usage/log/` (e.g. on pause/background or every N minutes), add the accumulated `topic_usage` to the body as in the examples above.
   - After a successful log, clear or reset the in-memory topic usage for the next session.

4. **Minimal implementation (if you don’t track time per topic)**
   - When user opens a topic (topic list item tap) or opens a subject under a topic: increment that topic’s count once.
   - When sending usage log, send `topic_usage: [ { "topic_id": id, "usage_count": count } ]` for each topic that was used in the session (no need to send `time_spent_minutes`).

---

## Backend Summary (for reference)

- **Model:** `UserTopicUsage` – (user, topic, date, usage_count, time_spent_minutes). One row per user per topic per day; counts are summed when the app sends multiple logs in the same day.
- **Admin:**
  - **Topic list:** Columns "Topic usage" (total opens + minutes) and "Unique users".
  - **User topic usage:** Full list of records (filter by topic or user, search, date hierarchy).
  - **User edit:** Inline "Topic usage" showing that user’s topic usage (last 50).

No new API endpoints; only the existing `POST /api/usage/log/` body is extended with optional `topic_usage`.
