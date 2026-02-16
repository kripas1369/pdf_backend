# Flutter: Student PDF Upload, Topics/Subjects & Stats – UI & API Task Brief

**App:** Bachelor Question Bank (Flutter + Django REST, JWT)  
**Base URL:** `/api/`  
**Auth:** `Authorization: Bearer <access_token>`

---

## Feature summary

1. **Student PDF upload** – Students upload free (question) PDFs. They can use **existing** topic/subject or **create new topic and new subject** in the same flow (no pre-approval needed). Upload is **pending** until admin approves.
2. **Single approval** – When **admin approves the PDF**, the backend **auto-approves** that PDF’s subject and topic so they appear in the app. When **admin rejects the PDF**, the backend **auto-rejects** that PDF’s subject and topic. So the student only “submits for review”; admin approves or rejects the PDF and topic/subject follow.
3. **Stats API** – One endpoint for dashboard/home: total topics, subjects, PDFs; when authenticated, the user’s upload counts (PDFs, topics, subjects).

---

## Backend APIs (already implemented)

### 1. Upload a PDF (student)

- **Endpoint:** `POST /api/student-pdfs/upload/`
- **Auth:** Required (JWT)
- **Content-Type:** `multipart/form-data`
- **Body fields:**
  - `title` (string, required) – e.g. "Engineering Mathematics 2079"
  - `subtitle` (string, optional) – short description
  - `year` (integer, required) – academic year (e.g. 2078, 2081 BS or 2024 AD); must be between 1990 and 2100
  - `subject` (integer, required) – subject ID (from existing topics/subjects API)
  - `file` (file, required) – PDF file only, max 15MB
- **Success:** `201 Created` with body same shape as “my uploads” item (id, title, year, subject, subject_name, is_approved, status, created_at, etc.).
- **Errors:** `400` with field errors (e.g. missing title, invalid year, file too large, not PDF).

### 2. List my uploads (student)

- **Endpoint:** `GET /api/student-pdfs/my-uploads/`
- **Auth:** Required (JWT)
- **Success:** `200 OK` with JSON array of uploads. Each item includes:
  - `id`, `title`, `subtitle`, `year`, `subject`, `subject_name`, `file` (URL), `is_approved`, `status` (`"pending"` or `"approved"`), `created_at`
- Use this to show “My uploads” / “My PDFs” list and status (pending/approved).

### 3. Student-created Topic (suggest new topic)

- **Endpoint:** `POST /api/student-topics/create/`
- **Auth:** Required (JWT)
- **Content-Type:** `application/json`
- **Body:** `{ "name": "Topic Name" }`
- **Success:** `201 Created` with `{ "id": 1, "name": "Topic Name", "is_approved": false }`. Only **approved** topics appear in `GET /api/topics/`.
- **Errors:** `400` if name is empty or a topic with that name already exists.

### 4. Student-created Subject (suggest new subject)

- **Endpoint:** `POST /api/student-subjects/create/`
- **Auth:** Required (JWT)
- **Content-Type:** `application/json`
- **Body:** `{ "name": "Subject Name", "topic": <topic_id> }` — `topic` can be **any** topic (approved or one the user just created). **Do not show “Topic must be approved”**; the backend accepts any topic.
- **Success:** `201 Created` with e.g. `{ "id": 1, "name": "Subject Name", "topic": 1, "topic_name": "TU", "is_approved": false }`. When admin later approves a PDF that uses this subject (and its topic), the backend auto-approves the subject and topic.
- **Errors:** `400` if name empty or a subject with that name already exists.

### 5. Stats API (dashboard / home)

- **Endpoint:** `GET /api/stats/`
- **Auth:** Optional (more fields when authenticated)
- **Success:** `200 OK` with JSON, e.g.:
  - **Always:** `total_topics`, `total_subjects`, `total_pdfs`, `student_pdf_uploads_pending` (global count of pending student PDF uploads).
  - **When authenticated:** `my_pdf_uploads_count`, `my_pdf_uploads_pending_count`, `my_topics_count`, `my_subjects_count`.
- Use this for home/dashboard cards or “Contribute” section (e.g. “You have 2 pending PDFs”, “3 topics pending approval”).

### 6. Existing APIs you already use (unchanged behavior)

- **Topics:** `GET /api/topics/` – list **approved** topics only.
- **Subjects by topic:** `GET /api/topics/<topic_id>/subjects/` – list **approved** subjects for that topic (need subject `id` for PDF upload).
- **Years by subject:** `GET /api/subjects/<subject_id>/years/` – list years with counts.
- **PDFs by subject and year:** `GET /api/subjects/<subject_id>/years/<year>/pdfs/` – list PDFs (only **approved** PDFs; includes approved student uploads).

**Approval flow:** Student uploads a PDF (with existing or new topic/subject). Only the PDF is “pending.” When **admin approves the PDF**, the backend auto-approves that PDF’s subject and topic so they appear in topic/subject lists. When **admin rejects the PDF**, the backend auto-rejects that PDF’s subject and topic. So the user never sees “Topic must be approved” or “Subject must be approved”; they just submit the full PDF (with new topic/subject if needed) and admin approves or rejects once.

---

## Flutter tasks (UI & integration)

### Task 1: “Upload PDF” entry point

- Add a clear entry point in the app for “Upload PDF” / “Contribute PDF” (e.g. in profile, home, or a “Contribute” tab).
- Only show for **logged-in** users; if not logged in, show a short message and a button to log in / register.

### Task 2: Upload form screen (with optional new topic & subject)

- **Title:** e.g. “Upload a free PDF” or “Contribute a PDF”.
- **Subtitle (short):** Explain that only question (free) PDFs are allowed and that the upload needs admin approval; when admin approves the PDF, the topic and subject (if new) are approved too.
- **Form fields:**
  - **Title** (required) – text field, placeholder e.g. “e.g. Engineering Mathematics 2079”.
  - **Subtitle** (optional) – text field, short description.
  - **Topic** – dropdown built from: `GET /api/topics/` (approved) **plus** any topic(s) the user created in this session (from `POST /api/student-topics/create/`). Add an option like **“+ Add new topic”**; when chosen, show a small input/dialog for topic name → call `POST /api/student-topics/create/` → add the returned topic to the dropdown and select it. **Do not show “Topic must be approved.”**
  - **Subject** (required) – dropdown built from: `GET /api/topics/<selected_topic_id>/subjects/` (approved for that topic) **plus** any subject(s) the user created in this session for that topic (from `POST /api/student-subjects/create/`). Add an option **“+ Add new subject”**; when chosen, show a small input for subject name → call `POST /api/student-subjects/create/` with `{ "name": "...", "topic": <selected_topic_id> }` (selected topic can be the one they just created) → add the returned subject to the dropdown and select it. **Do not show “Topic must be approved” or “Subject must be approved.”**
  - **Year** (required) – academic year (e.g. 2078, 2081); backend accepts 1990–2100. You can use a dropdown of common years or a number input.
  - **File** (required) – file picker that allows **PDF only**. Show file name and size after selection; validate size ≤ 15MB and show an error if larger.
- **Submit button:** “Upload” / “Submit for review”.
- **Loading state:** Disable form and show loader while `POST /api/student-pdfs/upload/` is in progress.
- **Success:** Show a success message (e.g. “PDF submitted for review. When admin approves it, your topic and subject will appear in the app too.”) and navigate back or to “My uploads”.
- **Error:** Show API error message (e.g. “Title is required”, “File too large”, “Only PDF allowed”) in a snackbar or inline.

### Task 3: “My uploads” screen

- **Entry:** From profile or “Upload PDF” area, a button/link like “My uploads” / “My contributed PDFs”.
- **Auth:** Required; if not logged in, redirect to login.
- **API:** `GET /api/student-pdfs/my-uploads/` with JWT.
- **List:** Show each upload with:
  - Title (and optional subtitle)
  - Subject name, year
  - **Status:** “Pending” or “Approved” (use `status` or `is_approved` from API). Use different color/chip (e.g. orange for pending, green for approved).
  - Optional: tap to open the PDF (using `file` URL) if you want to let the user preview their own upload.
- **Empty state:** If list is empty, show a short message and a button to go to “Upload PDF”.
- **Pull-to-refresh:** Refresh the list from the API.

### Task 4: Integration with existing PDF list

- No change required on the existing “PDF list by subject & year” screen. Backend already returns only **approved** PDFs there. Once admin approves a student upload, it will appear in that list automatically; user just needs to refresh or re-open that subject/year.

### Task 5: Validation and UX

- **Client-side:** Check title not empty; subject and year selected; file chosen and PDF; file size ≤ 15MB. Show clear error messages.
- **After upload:** Optionally show a one-line note like “Approved PDFs will appear under Topic → Subject → Year for everyone.”

### Task 6: “Suggest Topic” (optional)

- **Entry:** e.g. from “Contribute” or profile: “Don’t see your topic? Suggest one.”
- **Form:** Single field – topic **name**. Submit with `POST /api/student-topics/create/` (JSON body `{ "name": "..." }`).
- **Success:** Show exactly: **“Topic suggested! It will appear in the list after admin approval.”**  
  **Important:** Right after a successful create, **add the new topic to the topic dropdown and select it automatically.** The API returns the created topic (e.g. `{ "id": 5, "name": "My Topic", "is_approved": false }`). Append this to your topic list and set it as the selected topic so the user can immediately suggest a subject under it or continue the flow. Admin will approve it later; until then it appears only in this user’s dropdown from the create response.
- **Error:** Show API message (e.g. “A topic with this name already exists”).

### Task 7: “Suggest Subject” (inside upload flow or standalone)

- **Entry:** From the PDF upload form (subject dropdown: “+ Add new subject”) or a “Suggest subject” screen.
- **Form:** Topic (dropdown: approved topics from `GET /api/topics/` **plus** any topic the user just created in this session), Subject **name**. Submit with `POST /api/student-subjects/create/` (JSON body `{ "name": "...", "topic": <id> }`). **Topic can be any topic** (including the one they just created); do not show “Topic must be approved.”
- **Success:** “Subject added! Use it below and submit your PDF. It will appear in the list after admin approves your PDF.” Right after create, **add the new subject to the subject dropdown and select it** so the user can continue and upload the PDF.
- **Error:** Show API message (e.g. “A subject with this name already exists”).

### Task 8: Use Stats API (dashboard / home)

- Call `GET /api/stats/` on home or “Contribute” load (with JWT if user is logged in).
- Use **public** fields for generic stats: e.g. “X topics, Y subjects, Z PDFs” on home.
- Use **authenticated** fields when user is logged in: e.g. “Your uploads: N total, M pending” or “You have suggested P topics and Q subjects.” Optionally show a short “Pending approval” summary (e.g. “2 PDFs and 1 topic pending”).

---

## API summary (quick reference)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET  | `/api/stats/` | Optional | Dashboard stats (totals; when auth: my upload counts) |
| POST | `/api/student-topics/create/` | Required | Suggest new topic (JSON: name) |
| POST | `/api/student-subjects/create/` | Required | Suggest new subject (JSON: name, topic) |
| POST | `/api/student-pdfs/upload/` | Required | Upload a free PDF (multipart: title, subtitle, year, subject, file) |
| GET  | `/api/student-pdfs/my-uploads/` | Required | List current user’s PDF uploads (pending + approved) |
| GET  | `/api/topics/` | Optional | List approved topics |
| GET  | `/api/topics/<id>/subjects/` | Optional | List approved subjects for topic |
| GET  | `/api/subjects/<id>/years/` | Optional | List years (optional for upload form) |
| GET  | `/api/subjects/<id>/years/<year>/pdfs/` | Required | List PDFs for subject+year (approved only) |

---

## Notes for Flutter developer

- Use **multipart/form-data** for `POST /api/student-pdfs/upload/`: send `title`, `subtitle` (optional), `year`, `subject` (integer id), and `file` (PDF). Use the same JWT header as for other authenticated requests.
- Subject **id** in the upload request must be one of the ids from `GET /api/topics/<topic_id>/subjects/`.
- `year` is an academic year integer between 1990 and 2100 (e.g. 2078, 2081 BS or 2024 AD).
- **Stats:** Call `GET /api/stats/` with or without JWT; include JWT when the user is logged in to get `my_*` counts.
- **Topic/Subject suggest:** Send JSON body. Names must be unique (backend returns 400 if duplicate). **Subject can be created under any topic** (approved or the one the user just created). **Do not show “Topic must be approved”** anywhere in the app.
- **Dropdown after create:** After creating a topic or subject, **add it to the dropdown and select it** so the user can add a subject under the new topic or upload a PDF with the new subject. Topic dropdown = approved topics + topics created this session. Subject dropdown = approved subjects for selected topic + subjects created this session for that topic.
- **Admin approval:** When admin **approves** a student PDF, the backend **auto-approves** that PDF’s subject and topic. When admin **rejects** the PDF, the backend **auto-rejects** that PDF’s subject and topic. So the student only submits the full PDF (with new topic/subject if needed); one admin action approves or rejects PDF + subject + topic together.
- No Flutter code is provided here; implement UI and API calls in your project structure and state management (Provider, Riverpod, Bloc, etc.) as you already use in the app.
