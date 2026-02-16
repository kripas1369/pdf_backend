# Notifications & Subject Routines API

Backend support for **user notifications** (all users; pin/save for later) and **subject routines** (per-subject schedule; start reminder).

---

## Notifications

All notifications are per-user. Admin can send one notification to **all users** from Django admin (check "Send to all users"). Students can list, mark read, and **pin** (save for later).

### Endpoints (all require `Authorization: Bearer <access_token>`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/` | List my notifications (newest first) |
| GET | `/api/notifications/?pinned_only=1` | Only pinned (saved for later) |
| GET | `/api/notifications/?unread_only=1` | Only unread |
| GET | `/api/notifications/unread-count/` | Unread count (for badge) |
| PATCH | `/api/notifications/<id>/` | Update `is_read` and/or `is_pinned` |
| POST | `/api/notifications/<id>/mark-read/` | Mark as read |
| POST | `/api/notifications/<id>/pin/` | Pin (save for later) |
| POST | `/api/notifications/<id>/unpin/` | Unpin |

### Notification object

```json
{
  "id": 1,
  "title": "New PDF added",
  "body": "Physics 2079 solutions are now available.",
  "subject": 5,
  "subject_name": "Physics",
  "action_url": "",
  "is_read": false,
  "is_pinned": true,
  "created_at": "2026-02-16T10:00:00Z"
}
```

### PATCH body (optional fields)

```json
{ "is_read": true, "is_pinned": true }
```

---

## Subject routines

Routine is the class schedule **per subject** (e.g. Physics – Monday 10:00–11:00). Students can view routines and **start reminder** to get notified before a class (e.g. 15 minutes before).

### Endpoints (all require auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/subjects/<subject_id>/routines/` | List routines for a subject |
| GET | `/api/subjects/<subject_id>/routines/?day=1` | Filter by day (0=Sun … 6=Sat) |
| POST | `/api/routines/<routine_id>/start-reminder/` | Subscribe to reminder (optional body: `{ "notify_minutes_before": 15 }`) |
| POST | `/api/routines/<routine_id>/stop-reminder/` | Stop reminder for this routine |
| GET | `/api/routines/my-reminders/` | List my pinned/started reminders |

### Routine object

```json
{
  "id": 1,
  "subject": 3,
  "subject_name": "Physics",
  "day_of_week": 1,
  "day_display": "Monday",
  "start_time": "10:00:00",
  "end_time": "11:00:00",
  "title": "Unit 1 – Mechanics",
  "description": "",
  "order": 0,
  "user_has_reminder": true
}
```

### Start-reminder response

Returns a `UserRoutineReminder` object with `routine`, `notify_minutes_before`, `created_at`. Use this list to schedule local push notifications (or poll from backend later when you add push).

---

## Admin (Django)

- **Notifications:** Add notification; optionally check **Send to all users** to create one notification per active user. Users can then pin/read on their side.
- **Subject routines:** Add/edit routines per subject (day, start_time, end_time, title, description).
- **User routine reminders:** View which users have started reminders for which routines.

---

## Flutter tasks (summary)

1. **Notifications screen**
   - List notifications (tabs or filters: All / Unread / Pinned).
   - Badge with unread count (call `GET /api/notifications/unread-count/`).
   - Tap to mark read; pin/unpin (save for later) with PATCH or pin/unpin endpoints.
   - Optional: open `action_url` or subject when tapping a notification.

2. **Routine per subject**
   - On subject detail, call `GET /api/subjects/<id>/routines/` and show weekly schedule.
   - Optional filter by day.

3. **Start reminder (pin routine)**
   - On each routine row, show “Notify me” / “Start reminder” if `user_has_reminder` is false.
   - Call `POST /api/routines/<id>/start-reminder/` (optional body `{ "notify_minutes_before": 15 }`).
   - “Stop reminder” calls `POST /api/routines/<id>/stop-reminder/`.
   - “My reminders” screen: `GET /api/routines/my-reminders/` to show list of pinned routines for later notification (actual push can be implemented later).
