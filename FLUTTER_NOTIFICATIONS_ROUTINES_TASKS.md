# Flutter: Notifications & Subject Routines – Developer Tasks

Backend APIs are ready. Use this doc to implement **notifications** (list, mark read, pin/save for later) and **subject routines** (schedule per subject, start/stop reminder) in the Flutter app.

**All endpoints below require authentication.** Send `Authorization: Bearer <access_token>` (same token as other protected APIs). On 401, refresh token and retry.

---

## Part 1: Notifications

### API base

Base URL: same as your existing API (e.g. `https://yourserver.com/api/`).

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `notifications/` | List my notifications (newest first) |
| GET | `notifications/?pinned_only=1` | Only pinned (saved for later) |
| GET | `notifications/?unread_only=1` | Only unread |
| GET | `notifications/unread-count/` | Unread count (for badge) |
| PATCH | `notifications/<id>/` | Update `is_read` and/or `is_pinned` |
| POST | `notifications/<id>/mark-read/` | Mark as read (no body) |
| POST | `notifications/<id>/pin/` | Pin – save for later (no body) |
| POST | `notifications/<id>/unpin/` | Unpin (no body) |

### Notification model (response item)

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

- `subject` and `subject_name` can be `null` if notification is not linked to a subject.
- `action_url`: optional deep link or URL to open when user taps the notification.

### PATCH body (optional fields)

```json
{ "is_read": true, "is_pinned": true }
```

Send only the fields you want to update. Example: `{ "is_pinned": true }` to pin without changing read state.

### Unread count response

```json
{ "unread_count": 3 }
```

### Flutter tasks – Notifications

#### 1. Data layer
- [ ] Define a `Notification` model (id, title, body, subject, subjectName, actionUrl, isRead, isPinned, createdAt).
- [ ] Add API service methods: `getNotifications({ bool? pinnedOnly, bool? unreadOnly })`, `getUnreadCount()`, `patchNotification(id, { bool? isRead, bool? isPinned })`, `markRead(id)`, `pin(id)`, `unpin(id)`.
- [ ] Handle 401 (refresh token + retry) and 404 for invalid notification id.

#### 2. Notifications screen (list)
- [ ] Screen that lists the user’s notifications (e.g. `GET notifications/`).
- [ ] Support tabs or segment control: **All** | **Unread** | **Pinned** (use query params `unread_only=1` and `pinned_only=1`).
- [ ] Show title, body (truncated), subject name if present, and time (format `created_at` nicely).
- [ ] Visually distinguish unread (e.g. bold or dot) and pinned (e.g. pin icon).
- [ ] Pull-to-refresh to reload list.

#### 3. Unread badge
- [ ] Where you show a notification entry point (e.g. app bar icon or drawer), call `GET notifications/unread-count/` and show a badge with `unread_count`.
- [ ] Update badge after marking notifications as read and when returning to the notifications screen.

#### 4. Mark as read
- [ ] On tap of a notification, call `POST notifications/<id>/mark-read/` or `PATCH notifications/<id>/` with `{ "is_read": true }`, then update local state / list.
- [ ] Optional: navigate to subject screen or open `action_url` when provided.

#### 5. Pin / Unpin (save for later)
- [ ] On each notification, show a pin icon (or “Save for later”). If `is_pinned` is true, show “Unpin” or filled pin.
- [ ] Pin: call `POST notifications/<id>/pin/` and refresh or update state.
- [ ] Unpin: call `POST notifications/<id>/unpin/` and refresh or update state.
- [ ] Pinned notifications appear in the “Pinned” tab/filter.

#### 6. Empty states
- [ ] Empty state when there are no notifications; when Unread is empty; when Pinned is empty.

---

## Part 2: Subject routines

Routine = class schedule for a **subject** (e.g. Physics – Monday 10:00–11:00). User can **start reminder** to “see later” / get notified before class (e.g. 15 minutes before).

### API base

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `subjects/<subject_id>/routines/` | List routines for a subject |
| GET | `subjects/<subject_id>/routines/?day=0` | Filter by day (0=Sunday … 6=Saturday) |
| POST | `routines/<routine_id>/start-reminder/` | Start reminder (optional body below) |
| POST | `routines/<routine_id>/stop-reminder/` | Stop reminder (no body) |
| GET | `routines/my-reminders/` | List my started reminders |

### Routine model (response item)

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

- `day_of_week`: 0 = Sunday, 1 = Monday, … 6 = Saturday.
- `start_time` / `end_time`: time strings (e.g. format as “10:00 AM – 11:00 AM”).
- `user_has_reminder`: true if the current user has started a reminder for this routine.

### Start-reminder request (optional)

```json
{ "notify_minutes_before": 15 }
```

Default is 15. Use this to let the user choose “Notify me 15 / 30 minutes before”.

### Start-reminder response (UserRoutineReminder)

```json
{
  "id": 1,
  "routine": { ... routine object ... },
  "routine_id": 1,
  "notify_minutes_before": 15,
  "created_at": "2026-02-16T10:00:00Z"
}
```

### My-reminders response

List of `UserRoutineReminder` objects (each has `routine`, `notify_minutes_before`, `created_at`). Use this to show “My reminders” and, later, to schedule local notifications.

### Flutter tasks – Routines

#### 1. Data layer
- [ ] Define `Routine` model (id, subject, subjectName, dayOfWeek, dayDisplay, startTime, endTime, title, description, order, userHasReminder).
- [ ] Define `UserRoutineReminder` model (id, routine, notifyMinutesBefore, createdAt).
- [ ] API methods: `getSubjectRoutines(subjectId, { int? day })`, `startRoutineReminder(routineId, { int? notifyMinutesBefore })`, `stopRoutineReminder(routineId)`, `getMyReminders()`.

#### 2. Routine list on subject screen
- [ ] On the subject detail screen (where you show PDFs by year, etc.), add a section or tab “Routine” / “Schedule”.
- [ ] Call `GET subjects/<subject_id>/routines/` and show a list or weekly view (e.g. by day).
- [ ] Optional: day filter (e.g. segment 0–6 or dropdown) using `?day=<0-6>`.
- [ ] Display: day, time range (e.g. “10:00 AM – 11:00 AM”), title, and description if present.

#### 3. Start / stop reminder (pin routine)
- [ ] On each routine row, if `user_has_reminder` is false: show “Notify me” / “Start reminder” (e.g. button or icon).
- [ ] On tap: call `POST routines/<routine_id>/start-reminder/`. Optional: show a dialog to pick “Notify 15 / 30 minutes before” and send `{ "notify_minutes_before": 15 }` (or 30).
- [ ] After start: set `user_has_reminder` to true in UI (or refetch routines).
- [ ] If `user_has_reminder` is true: show “Stop reminder” / “Unpin”. On tap: call `POST routines/<routine_id>/stop-reminder/` and update UI.

#### 4. My reminders screen
- [ ] Screen (e.g. under Profile or Notifications) “My reminders” / “Saved routines”.
- [ ] Call `GET routines/my-reminders/` and list reminders with subject name, day, time, and “Notify X min before”.
- [ ] Each item: option to “Stop reminder” (call `stopRoutineReminder(routineId)` and remove from list or refetch).

#### 5. Empty states
- [ ] Subject has no routines: show “No schedule added for this subject.”
- [ ] User has no reminders: show “You haven’t started any reminders. Open a subject and tap ‘Notify me’ on a routine.”

---

## Part 3: Optional (later)

- [ ] When user opens a notification with `action_url`, open that URL (in-app WebView or browser) or handle as deep link.
- [ ] When `subject` is set, “Tap to open” could navigate to that subject’s screen.
- [ ] Use `my-reminders` + local notification plugin to schedule “Class in 15 minutes” (e.g. `flutter_local_notifications`). Backend only stores preference; scheduling can be done in Flutter.

---

## Summary checklist

| Area | Task |
|------|------|
| Notifications | Model + API service for all notification endpoints |
| Notifications | Notifications screen with All / Unread / Pinned |
| Notifications | Unread count badge on notification icon/entry |
| Notifications | Mark as read on tap |
| Notifications | Pin / Unpin (save for later) |
| Routines | Model + API service for routines and reminders |
| Routines | Show routines on subject detail (section or tab) |
| Routines | Start reminder / Stop reminder per routine |
| Routines | “My reminders” screen |

Use the same base URL and auth (Bearer token) as the rest of the app. On 401, use refresh token and retry once.
