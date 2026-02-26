# Flutter: Two-Level Topic UI (Program → Years)

The app currently shows all topics in one flat list (e.g. "BBS 1st Year", "BSC 2nd Year", "BBA 1st Year"). This document describes how to show **programs first** (BBS, BSC, BBA) and on tap show **years** (1st, 2nd, 3rd) for that program.

---

## Backend API

### Grouped-by-program endpoint

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `GET /api/topics/grouped-by-program/` | GET | **Not required** | Returns programs, each with a list of topics (years). Use this for the two-level UI. |

#### Response shape

```json
[
  {
    "program": "BBA",
    "topics": [
      { "id": 5, "name": "BBA 1st Year", "year_label": "1st Year" },
      { "id": 6, "name": "BBA 2nd Year", "year_label": "2nd Year" }
    ]
  },
  {
    "program": "BBS",
    "topics": [
      { "id": 1, "name": "BBS 1st Year", "year_label": "1st Year" },
      { "id": 2, "name": "BBS 2nd Year", "year_label": "2nd Year" }
    ]
  },
  {
    "program": "BSC",
    "topics": [
      { "id": 3, "name": "BSC 1st Year", "year_label": "1st Year" },
      { "id": 4, "name": "BSC 2nd Year", "year_label": "2nd Year" }
    ]
  }
]
```

- **program**: Display name for the first level (e.g. "BBS", "BSC", "BBA").
- **topics**: List of topics (years) under that program. Each has `id`, `name`, and `year_label` (e.g. "1st Year", "2nd Year").
- Programs are sorted alphabetically; topics under each program are sorted by year (1st, 2nd, 3rd, 4th).

---

## Flutter implementation

### 1. First screen: list of programs

- Call `GET /api/topics/grouped-by-program/`.
- Show a list of **program** names (e.g. BBS, BSC, BBA). Do **not** show the full topic names here.

### 2. On program tap: list of years (topics)

- When the user taps a program (e.g. "BBS"), use the **topics** array for that program from the same response.
- Show a second screen (or expandable section) with **year_label** and/or **name** (e.g. "1st Year", "2nd Year").
- When the user taps a topic (e.g. "BBS 1st Year"), use that topic’s **id** to load subjects:  
  `GET /api/topics/<topic_id>/subjects/` (existing API).

### 3. Flow summary

```
Screen 1: Programs (BBS, BSC, BBA, …)
    → tap "BBS"
Screen 2: Years for BBS (1st Year, 2nd Year, …)
    → tap "1st Year"
Screen 3: Subjects for BBS 1st Year (existing subjects-by-topic API)
```

---

## Optional: flat topic list

- **Flat list** (all topics in one list): keep using `GET /api/topics/` (existing). Each topic now also has `program` and `year_label` in the response if you need them for display or filtering.

---

## Backend: filling program and year_label

- In Django admin (**Topics**), you can set **program** and **year_label** per topic.
- If they are left blank, the API derives them from the topic **name** (e.g. "BBS 1st Year" → program "BBS", year_label "1st Year"). For consistent grouping, prefer filling program and year_label in admin for existing topics.
