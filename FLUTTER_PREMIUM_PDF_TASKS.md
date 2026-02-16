# Flutter Premium PDF – Developer Tasks & API Reference

Backend supports **Single PDF**, **Subject package** (all PDFs in one subject), **Topic package** (all subjects in one topic, all PDFs), plus optional year/full packages and Subscription. Use this doc for implementation.

---

## 0. App flow (hierarchy)

**Topic → Subject → PDFs** (inside each subject: years → PDFs)

- User sees **Topics** → taps one → gets **Subjects** in that topic.
- User taps a **Subject** → gets **PDFs** (e.g. by year or list). Each PDF can be question or solution, free or premium (locked).
- When user taps a **locked PDF**, show paywall: **Buy this PDF only** | **This subject** (all PDFs in this subject) | **Whole topic** (all subjects in this topic, all PDFs).

**Purchase options:**

1. **Single PDF** – One PDF only. After approve → that PDF unlocks.
2. **Subject package** – All PDFs in **one subject**. After approve → every PDF in that subject unlocks.
3. **Topic package** – All subjects under **one topic**, all PDFs. After approve → every PDF in every subject of that topic unlocks.
4. (Optional) Year package, Full package, Subscription – as per backend.

**Flutter:** Topic list → Subject list (lock icon if subject has premium PDFs) → PDF list. On locked PDF tap → paywall: **Buy this PDF**, **This subject**, **Whole topic** (and any year/full packages from API).

---

## 1. Auth requirement (critical)

Send **`Authorization: Bearer <access_token>`** on: PDF list, check-access, payment create, payment status, packages list. Without token → **401** on protected endpoints.

---

## 2. Ways to get access

| Option | payment_type | What user gets | API / Backend |
|--------|---------------|----------------|----------------|
| **Single PDF** | `SINGLE_PDF` | One PDF only | Send `purchased_pdf: <pdf_id>`. After approval → that PDF has `has_access: true`. |
| **One year (subject + year)** | `YEAR_PACKAGE` | All PDFs in **this subject for this year** (bulk) | `GET /api/subscription/packages/` with `?subject_id=…&year=…`; pick `package_type: "YEAR"`, send `purchased_package: <id>`. |
| **All years (subject)** | `SUBJECT_PACKAGE` | All PDFs in **this subject, all years** (bulk) | Same; pick `package_type: "SUBJECT"`, send `purchased_package: <id>`. |
| **Full package** | `FULL_PACKAGE` | Admin-defined set of PDFs (all years 1–4) | Pick `package_type: "ALL_YEARS"`, send `purchased_package: <id>`. |
| **Subscription** | `SUBSCRIPTION` | **All** premium PDFs (app-wide) | Send `tier: "gold"` or `"platinum"` (Diamond). |

**Flutter UX:** On a locked PDF (or on subject/year screen), show: “Purchase this PDF (₹X)”, “Buy this year (all PDFs in this subject for this year)”, “Buy all years (all PDFs in this subject)”, “Gold/Diamond – all premium”. Use `GET /api/subscription/packages/?subject_id=<id>` or `?subject_id=<id>&year=<year>` to list relevant packages.

---

## 3. Subjects list (by topic)

- **URL:** `GET /api/topics/{topic_id}/subjects/` (paginated)
- **Response:** Each subject has `id`, `name`, **`has_premium_pdfs`** (bool), **`is_locked`** (bool). Use `has_premium_pdfs` or `is_locked` to show a lock icon on subjects that contain premium/solution PDFs.

## 4. PDF list

- **URL:** `GET /api/subjects/{subject_id}/years/{year}/pdfs/`
- **Headers:** `Authorization: Bearer <access_token>` (required)
- **Response:** Array of PDFs; each has `id`, `title`, `year`, `file`, `is_premium`, `price`, **`has_access`**, **`is_locked`**.

**Lock logic:** Use `is_locked == true` from API (or `is_premium && !has_access`). If locked → open paywall; if not → open PDF.

---

## 5. When user taps locked PDF – show all options (APIs + Flutter tasks)

When the user taps a **locked PDF**, show a paywall with: **single PDF**, **subject-wise package(s)**, **year-wise package(s)**, and **full package** (if any). **For now do not show Subscription (Gold/Diamond)** in this popup. Use the **subject_id** and **year** of the screen the user is on (e.g. PDF list for Physics, year 2081).

### APIs to call (when opening the paywall)

Call the packages API only (subscription plans are not used in the paywall for now):

| # | API | Purpose |
|---|-----|--------|
| 1 | `GET /api/subscription/packages/?subject_id={subject_id}&year={year}` | Subject-wise, year-wise, and full packages to show. Use the **subject_id** and **year** of the current screen. |

- **Base URL:** Your backend base (e.g. `https://yourserver.com` or `http://10.0.2.2:8000` for Android emulator).
- **Auth:** Not required for this GET. Do **not** call `GET /api/subscription/plans/` in the paywall for now (Subscription option removed from popup).

### 1) Get packages (subject-wise, year-wise, full)

- **URL:** `GET /api/subscription/packages/?subject_id={subject_id}&year={year}`
- **Example:** `GET /api/subscription/packages/?subject_id=100&year=2081`
- **Response:** JSON array of packages. Each item:

| Field | Type | Use in app |
|-------|------|------------|
| `id` | number | Send as `purchased_package` when user buys this package |
| `name` | string | Show as option title |
| `package_type` | string | `"SUBJECT"` = this subject only, `"TOPIC"` = whole topic (all subjects), `"YEAR"` = year, `"ALL_YEARS"` = full |
| `topic` | number or null | Topic id (for TOPIC package); use `topic_name` for label |
| `topic_name` | string or null | e.g. "TU" – show for Topic package |
| `subject` | number or null | Subject id (for SUBJECT package) |
| `subject_name` | string or null | Subject name for label |
| `year` | number or null | Year (for YEAR package) |
| `price` | string | Show price (e.g. "199.00") |
| `pdf_count` | number | Show e.g. "24 PDFs" |

**How to show:**

- **This subject:** `package_type == "SUBJECT"`. Label e.g. "This subject – {name} – ₹{price} ({pdf_count} PDFs)". On tap → `payment_type: "SUBJECT_PACKAGE"`, `purchased_package: id`.
- **Whole topic:** `package_type == "TOPIC"`. Label e.g. "Whole topic ({topic_name}) – {name} – ₹{price} ({pdf_count} PDFs)". On tap → `payment_type: "TOPIC_PACKAGE"`, `purchased_package: id`. After approve → all PDFs in every subject of that topic unlock.
- **Year-wise:** `package_type == "YEAR"`. On tap → `payment_type: "YEAR_PACKAGE"`.
- **Full package:** `package_type == "ALL_YEARS"`. On tap → `payment_type: "FULL_PACKAGE"`.

If the array is empty, still show **Single PDF** only.

### What to show on the paywall (order) – no Subscription for now

1. **Buy this PDF only** – ₹{price} (use the tapped PDF’s `id` and `price`). On tap → payment with `payment_type: "SINGLE_PDF"`, `purchased_pdf: pdf.id`, `amount: pdf.price`.
2. **Subject-wise packages** – From packages API where `package_type == "SUBJECT"`. One card/row per package. On tap → payment with `payment_type: "SUBJECT_PACKAGE"`, `purchased_package: package.id`, `amount: package.price`.
3. **Year-wise packages** – From packages API where `package_type == "YEAR"`. One card/row per package. On tap → payment with `payment_type: "YEAR_PACKAGE"`, `purchased_package: package.id`, `amount: package.price`.
4. **Full package** – From packages API where `package_type == "ALL_YEARS"`. On tap → payment with `payment_type: "FULL_PACKAGE"`, `purchased_package: package.id`, `amount: package.price`.

**Do not show Subscription (Gold/Diamond) in the paywall for now.**

### Paywall popup layout: show four sections separately

In the popup, show **four clearly separated sections** so the user can easily choose. Use section titles or dividers.

**Section 1 – One PDF buy**  
- Title: e.g. **"Buy this PDF only"**  
- One row/card: “This PDF – ₹{price}” (use tapped PDF’s price).  
- On tap → payment: `payment_type: "SINGLE_PDF"`, `purchased_pdf: pdf.id`, `amount: pdf.price`.

**Section 2 – Year wise**  
- Title: e.g. **"Year wise"** or **"Buy all PDFs in this year"**  
- List all packages from API where `package_type == "YEAR"`. Each row: “{name} – ₹{price} ({pdf_count} PDFs)”.  
- On tap → payment: `payment_type: "YEAR_PACKAGE"`, `purchased_package: package.id`, `amount: package.price`.  
- If there are no year packages, show this section with one line like “No year package for this year” or hide the section.

**Section 3 – Subject wise**  
- Title: e.g. **"Subject wise"** or **"Buy all PDFs in this subject"**  
- List all packages from API where `package_type == "SUBJECT"`. Each row: “{name} – ₹{price} ({pdf_count} PDFs)”.  
- On tap → payment: `payment_type: "SUBJECT_PACKAGE"`, `purchased_package: package.id`, `amount: package.price`.  
- If there are no subject packages, show “No subject package” or hide the section.

**Section 4 – Subscription**  
- Title: e.g. **"Full access (Subscription)"**  
- Two rows: “Gold – ₹499” and “Diamond – ₹899” (from `GET /api/subscription/plans/`).  
- On tap Gold → payment: `payment_type: "SUBSCRIPTION"`, `tier: "gold"`, `amount: 499`.  
- On tap Diamond → payment: `payment_type: "SUBSCRIPTION"`, `tier: "platinum"`, `amount: 899`.

**Optional: Full package section**  
- If you have packages with `package_type == "ALL_YEARS"`, add a section **"Full package"** after Subject wise and list those packages. No Subscription section for now.

**UI idea:** Use a scrollable list with section headers. User sees: **One PDF buy** → **Year wise** → **Subject wise** → (optional **Full package**). Do not show Subscription in the paywall for now.

### Flutter developer tasks (simple checklist)

- [ ] On **locked PDF tap**, open a paywall/bottom sheet (do not open PDF).
- [ ] When paywall opens, call **only** `GET /api/subscription/packages/?subject_id={current_subject_id}&year={current_year}` (do not call plans API for the paywall for now).
- [ ] Show **"Buy this PDF only – ₹{price}"** using the tapped PDF’s `id` and `price`.
- [ ] From **packages** response, show:
  - All items with `package_type == "SUBJECT"` as **this subject** options (name, price, pdf_count).
  - All items with `package_type == "TOPIC"` as **whole topic** options (all subjects in topic).
  - All items with `package_type == "YEAR"` as **year-wise** options.
  - All items with `package_type == "ALL_YEARS"` as **full package** option(s).
- [ ] **Do not show Subscription (Gold/Diamond)** in the paywall for now.
- [ ] When user picks an option, go to payment screen with: screenshot upload, amount, payment_method, and the right `payment_type` + `purchased_pdf` (single) or `purchased_package` (package). Call `POST /api/payment/create/` with **Bearer token**.
- [ ] After payment is **APPROVED**, go back and **refetch** the PDF list so the unlocked PDF shows `has_access: true`.

---

## 5a. Fix: App only shows 1 package and subscription (show ALL options)

**Problem:** Paywall shows only one PDF package and subscription, but not single PDF, other subject/year packages, or full package.

**Cause (pick one and fix):**

1. **Packages API called without subject_id and year**  
   If you call `GET /api/subscription/packages/` with no query, the backend returns packages that match no filter (e.g. only one or none). You must pass the **current screen’s subject_id and year** so the backend returns all packages for that subject and that year (subject-wise, year-wise, and full if any).

2. **Only one package shown in UI**  
   The packages API returns an **array**. You must show **every item** in the array (one row/card per package), not just the first one. Loop over the full list and render each package.

3. **Single PDF option missing**  
   “Buy this PDF only” is not from any API. You must always add it in the paywall using the **tapped PDF’s `id` and `price`** (from the PDF list screen). Show it as the first option.

4. **Only one package_type shown**  
   The response can contain `package_type: "SUBJECT"`, `"YEAR"`, and `"ALL_YEARS"`. Show **all** of them: do not filter to only SUBJECT or only YEAR. Render every package in the list.

### Tasks for Flutter developer (do these)

- [ ] **Pass context to packages API**  
  When opening the paywall, you must have **subject_id** and **year** (from the screen that shows the PDF list). Call:  
  `GET /api/subscription/packages/?subject_id={subject_id}&year={year}`  
  Use the same subject_id and year the user used to open the PDF list. If you don’t pass them, the backend may return fewer or wrong packages.

- [ ] **Call packages API with query params**  
  Do not call `/api/subscription/packages/` without query. Always append `?subject_id=X&year=Y`. Example:  
  `GET /api/subscription/packages/?subject_id=100&year=2081`

- [ ] **Show every package in the response**  
  The response is a JSON **array**. Use a list builder (e.g. `ListView.builder` or `Column` of cards) and show **one option per item** in the array. Do not show only `packages[0]` or only one package_type.  
  - For each item with `package_type == "SUBJECT"` → show one “Subject-wise” option.  
  - For each item with `package_type == "YEAR"` → show one “Year-wise” option.  
  - For each item with `package_type == "ALL_YEARS"` → show one “Full package” option.

- [ ] **Always show “Buy this PDF only”**  
  Add this as the first option in the paywall. Use the locked PDF’s `id` and `price` (the one the user tapped). This is not in the packages API; it comes from the PDF list screen.

- [ ] **Do not show Subscription (Gold/Diamond) in the paywall for now.** Only One PDF buy, Year wise, Subject wise, Full package (if any).

- [ ] **Check backend has multiple packages**  
  In Django admin, create at least: one **Subject package** (subject selected, year empty), one **Year package** (year selected, subject empty) for the same subject/year the app uses. If the backend has only one package, the app will only get one. Call the packages API in a browser or Postman with `?subject_id=X&year=Y` and confirm you get an array with multiple items if you expect more.

**Summary:** Pass `subject_id` and `year` in the packages URL, loop over the **entire** packages array and show every item, always show “Buy this PDF only” and both subscription options. Then all options will appear.

**Backend (already fixed):** When you call `GET /api/subscription/packages/?subject_id=X` (optionally `&year=Y`), the backend returns **all relevant** packages: subject package(s) for that subject, **topic package(s)** for that subject’s topic (all subjects in the topic), and year/full packages. Show every item; include **Topic** option with `payment_type: "TOPIC_PACKAGE"`.

---

## 5b. Topic / Subject / Single PDF – quick summary for Flutter

**Hierarchy:** Topic → Subject → PDFs. When user taps a **locked PDF** (inside a subject):

1. **API:** `GET /api/subscription/packages/?subject_id={current_subject_id}` (no auth). Backend returns packages for this subject and for this subject’s **topic** (all subjects under that topic).
2. **Paywall – show three main options:**
   - **Buy this PDF only** → `payment_type: "SINGLE_PDF"`, `purchased_pdf: pdf.id`, `amount: pdf.price`. After approve → that PDF unlocks.
   - **This subject** (all PDFs in this subject) → `package_type == "SUBJECT"` → `payment_type: "SUBJECT_PACKAGE"`, `purchased_package: package.id`. After approve → all PDFs in this subject unlock.
   - **Whole topic** (all subjects in this topic, all PDFs) → `package_type == "TOPIC"` → `payment_type: "TOPIC_PACKAGE"`, `purchased_package: package.id`. After approve → all PDFs in every subject of that topic unlock.
3. **After payment APPROVED:** Refetch the PDF list(s) the user can see. For **Topic package**, refetch or invalidate cache for **all subjects in that topic** so every unlocked PDF shows as unlocked when user navigates.

---

## 5c. Flutter developer: show Year, Subject, and Full package (not only single PDF)

**Current issue:** Paywall shows only “Buy this PDF” (single PDF). Year package, Subject package, and Full package options are not shown.

**Goal:** On the same paywall, show **all** of these:
1. Buy this PDF only (single PDF) – already working  
2. **Subject package(s)** – “All PDFs in this subject (all years)”  
3. **Year package(s)** – “All PDFs in this year”  
4. **Full package(s)** – “Full package (all years)”  
5. Full subscription (Gold / Diamond)

**Tasks for Flutter developer (do in order):**

1. **When user taps a locked PDF**, you already have:
   - The **PDF** (id, price, etc.) from the PDF list.
   - The **subject_id** and **year** of the screen (the same subject and year used to load the PDF list).
   Keep these in state or pass them into the paywall screen/dialog.

2. **When the paywall opens**, call this API (do not skip):
   ```
   GET {baseUrl}/api/subscription/packages/?subject_id={subject_id}&year={year}
   ```
   Example: `GET https://yourserver.com/api/subscription/packages/?subject_id=100&year=2081`  
   Use the **same** subject_id and year as the current PDF list screen. No auth needed for this GET.

3. **Parse the response** as a JSON **array** of packages. Each item has:
   - `id` (number)
   - `name` (string)
   - `package_type` (string): `"SUBJECT"` | `"YEAR"` | `"ALL_YEARS"`
   - `price` (string, e.g. `"199.00"`)
   - `pdf_count` (number)

4. **In the paywall UI**, build a **list** (e.g. `ListView` or `Column` of cards) with:
   - **First row:** “Buy this PDF only – ₹{pdf.price}” (use the tapped PDF’s id and price). On tap → payment with `payment_type: "SINGLE_PDF"`, `purchased_pdf: pdf.id`, `amount: pdf.price`.
   - **Next rows:** Loop over the **entire** packages array from step 3. For **each** package in the array, add one row/card:
     - If `package_type == "SUBJECT"` → show label like “Subject – {name} – ₹{price} ({pdf_count} PDFs)”. On tap → payment with `payment_type: "SUBJECT_PACKAGE"`, `purchased_package: package.id`, `amount: package.price`.
     - If `package_type == "YEAR"` → show label like “Year – {name} – ₹{price} ({pdf_count} PDFs)”. On tap → payment with `payment_type: "YEAR_PACKAGE"`, `purchased_package: package.id`, `amount: package.price`.
     - If `package_type == "ALL_YEARS"` → show label like “Full package – {name} – ₹{price}”. On tap → payment with `payment_type: "FULL_PACKAGE"`, `purchased_package: package.id`, `amount: package.price`.
   - Do **not** show Gold/Diamond subscription in the paywall for now.

5. **Do not** show only the first package. Use `ListView.builder` (or similar) with `itemCount: packages.length` and show **every** package. If the API returns 2 subject packages, 1 year package, and 1 full package, the user must see **4 package options** plus single PDF. No Subscription for now.

6. **If the packages array is empty**, still show “Buy this PDF only” and “Gold / Diamond” (do not show Subscription). You can hide or show a message like “No packages for this subject/year” for the middle section.

7. **Payment screen:** When user taps any option, open the payment screen and on submit call `POST /api/payment/create/` with:
   - `screenshot`, `amount`, `payment_method`, `payment_type`
   - For single PDF: `purchased_pdf: pdfId`
   - For any package: `purchased_package: packageId` (and **no** `purchased_pdf`)
   - (Subscription not used in paywall for now.)

**Summary:** Call packages API with subject_id and year → get array → show one row per package (Subject / Year / Full) in the paywall, plus single PDF. Do not show Subscription (Gold/Diamond) for now.

---

## 6. Get packages (reference)

- **URL:** `GET /api/subscription/packages/`
- **Auth:** Not required (public list of buyable packages)
- **Query (recommended):** `?subject_id=<id>` – packages for this subject. `?subject_id=<id>&year=<year>` – packages for this subject and year (e.g. “this year” package).
- **Response (200):** Array of packages, e.g.:

```json
[
  {
    "id": 1,
    "name": "Electricity and Magnetism 2081",
    "package_type": "YEAR",
    "package_type_display": "One year (subject + year) – all PDFs in this subject for this year",
    "subject": 100,
    "subject_name": "Electricity and Magnetism Notes",
    "year": 2081,
    "price": "199.00",
    "pdf_count": 8,
    "is_solution_package": false
  },
  {
    "id": 2,
    "name": "Electricity and Magnetism – All years",
    "package_type": "SUBJECT",
    "package_type_display": "All years (subject) – all PDFs in this subject, all years",
    "subject": 100,
    "subject_name": "Electricity and Magnetism Notes",
    "year": null,
    "price": "499.00",
    "pdf_count": 24,
    "is_solution_package": false
  }
]
```

**Flutter task:** When user is on **Subject** screen: call `GET /api/subscription/packages/?subject_id=<subject_id>` and show “Buy all years (this subject)” (SUBJECT) and any YEAR packages for that subject. When user is on **Year** screen (subject + year): call `...?subject_id=<id>&year=<year>` and show “Buy this year” (YEAR) and “Buy all years (subject)” (SUBJECT). Use `payment_type: "YEAR_PACKAGE"` or `"SUBJECT_PACKAGE"` or `"FULL_PACKAGE"` and `purchased_package: <id>`.

---

## 7. Payment submission (upload screenshot)

- **URL:** `POST /api/payment/create/`
- **Headers:** `Authorization: Bearer <access_token>`, `Content-Type: multipart/form-data`
- **Body (form fields):**

| Field | Type | Required | When |
|-------|------|----------|------|
| screenshot | File (image) | Yes | Always (max 5MB) |
| amount | String/Decimal | Yes | Always |
| payment_method | String | Yes | e.g. "eSewa", "Khalti" |
| payment_type | String | Yes | `SINGLE_PDF` \| `SUBJECT_PACKAGE` \| `TOPIC_PACKAGE` \| `YEAR_PACKAGE` \| `FULL_PACKAGE` \| `SUBSCRIPTION` |
| transaction_note | String | No | Optional |
| purchased_pdf | String (ID) | If SINGLE_PDF | PDF id |
| purchased_package | String (ID) | If SUBJECT_PACKAGE, TOPIC_PACKAGE, YEAR_PACKAGE, or FULL_PACKAGE | Package id from `GET /api/subscription/packages/?subject_id=<id>` |
| tier | String | If SUBSCRIPTION | "gold" or "platinum" (Diamond) |

**Success (201):** JSON with `id`, `payment_id`, `status: "PENDING"`, `amount`, `payment_type`, etc. Store `payment_id` for status polling.

**Errors:** 400 (validation), 401 (not authenticated).

---

## 8. After purchase

1. Poll **`GET /api/payment/status/<payment_id>/`** (with auth) until `status` is `"APPROVED"` or `"REJECTED"`.
2. When **APPROVED**, **refetch PDF list(s)** so the UI shows unlocked state:
   - **Single PDF:** Refetch the current subject+year PDF list (or the list where that PDF appears). That PDF will have `has_access: true`, `is_locked: false`.
   - **Subject package:** Backend unlocks all PDFs in that subject. Refetch PDF list(s) for that subject (all years) so they show unlocked.
   - **Topic package:** Backend unlocks all PDFs in every subject of that topic. Refetch PDF lists for **all subjects in that topic** (or invalidate caches) so every newly unlocked PDF shows as unlocked when the user navigates.
   - **Year / Full package:** Refetch the relevant PDF list(s) the user can see so newly unlocked PDFs show as unlocked.
3. Use same auth token: `GET /api/subjects/{id}/years/{year}/pdfs/` (and any other list in scope).

---

## 9. Other APIs (reference)

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /api/payment/qr/` | No | QR image URL for scan-and-pay |
| `GET /api/payment/my-payments/` | Yes | User’s payment history |
| `GET /api/subscription/plans/` | No | Subscription plans (Gold/Diamond – all premium) |
| `GET /api/subscription/packages/` | No | Subject / Year packages (names, prices, ids) |
| `GET /api/subscription/my-subscription/` | Yes | Current user subscription |
| `GET /api/subscription/check-access/<pdf_id>/` | Yes | Check if user can open PDF |

---

## 10. Flutter checklist

- [ ] **Auth:** Send Bearer token on PDF list, check-access, payment create, payment status.
- [ ] **Subjects:** Use `GET /api/topics/{id}/subjects/`; show lock icon when `subject.has_premium_pdfs` or `subject.is_locked` is true.
- [ ] **PDF list:** Use `GET /api/subjects/{id}/years/{year}/pdfs/` with auth; handle 401.
- [ ] **Lock UI:** `isLocked = pdf.is_premium && !pdf.has_access`; show lock + price when locked.
- [ ] **Paywall (critical):** When user taps a locked PDF, call **both** (1) `GET /api/subscription/packages/?subject_id=<id>&year=<year>` and (2) `GET /api/subscription/plans/`. Show: Single PDF, Year package(s), Subject package(s), Full package(s) if any, and Gold/Diamond. If you only call plans, only “full access subscription” will show.
- [ ] **Payment create:** Support all five types. SINGLE_PDF → `purchased_pdf`; SUBJECT_PACKAGE / YEAR_PACKAGE / FULL_PACKAGE → `purchased_package` (id from packages API); SUBSCRIPTION → `tier`.
- [ ] **After purchase:** Poll payment status until APPROVED; then refetch PDF list so unlocked content shows `has_access: true`.

---

## 11. Flutter UI method – how to build it (prompt for developer)

Use this as the **UI implementation guide** or paste it as a **prompt** for the Flutter developer (or for AI-assisted Flutter coding).

---

### Flutter UI prompt (copy-paste)

**Context:** We have a PDF app. User navigates: **Topic → Subject → Year → PDF list**. Each PDF can be free or premium (locked). User can buy: (1) single PDF, (2) subject-wise package, (3) single year package, (4) full package (all years 1–4 in one), (5) subscription (all premium). Backend APIs are ready; we need the Flutter UI.

**Screens and flow:**

1. **PDF list screen** (existing or to build)
   - Call `GET /api/subjects/{subject_id}/years/{year}/pdfs/` with `Authorization: Bearer <access_token>`.
   - For each PDF item: show title, year; if **locked** (`is_premium && !has_access`) show lock icon and price. If **unlocked**, show open/view.
   - **Tap unlocked PDF** → open PDF viewer. **Tap locked PDF** → navigate to **Paywall** (pass `pdf`: id, title, price).

2. **Paywall / Purchase options screen** (when user taps a locked PDF) — **must show all options**
   - You need **two API calls** so the popup shows both packages and subscription:
     - **Call 1 – Packages:** `GET /api/subscription/packages/?subject_id=<current_subject_id>&year=<current_year>`  
       Use the **subject_id** and **year** of the screen the user is on (e.g. PDF list for “Physics, 2081”). This returns year-wise and subject-wise packages for this context. **If you don’t call this, year/subject packages will not appear.**
     - **Call 2 – Subscription plans:** `GET /api/subscription/plans/`  
       This returns Gold and Diamond (full access). **If you only call this, the popup will only show “full access subscription” and no other options.**
   - Show: “This PDF is locked. Choose how to unlock:”
   - **Option A – Single PDF:** “Purchase this PDF only – ₹{pdf.price}” → Payment upload with `payment_type: SINGLE_PDF`, `purchased_pdf: pdf.id`, `amount: pdf.price`.
   - **Option B – This year (year package):** From **packages** response, show each item with `package_type == "YEAR"` as “{name} – ₹{price} ({pdf_count} PDFs)”. On tap → Payment upload with `payment_type: YEAR_PACKAGE`, `purchased_package: package.id`, `amount: package.price`.
   - **Option C – All years (subject package):** From **packages** response, show each item with `package_type == "SUBJECT"` as “{name} – ₹{price} ({pdf_count} PDFs)”. On tap → Payment upload with `payment_type: SUBJECT_PACKAGE`, `purchased_package: package.id`, `amount: package.price`.
   - **Option D – Full package:** From **packages** response, show items with `package_type == "ALL_YEARS"` (if any). On tap → Payment upload with `payment_type: FULL_PACKAGE`, `purchased_package: package.id`, `amount: package.price`.
   - **Option E – Full access (subscription):** From **plans** response, show Gold (₹499) and Diamond (₹899). On tap → Payment upload with `payment_type: SUBSCRIPTION`, `tier: "gold"` or `"platinum"`, `amount: 499` or `899`.
   - Use a list or cards; one CTA per option. If packages API returns an empty list for this subject/year, still show Single PDF and Subscription.

3. **Payment upload screen**
   - Show: amount, payment method (eSewa, Khalti), optional note, **screenshot image picker**. Show QR from `GET /api/payment/qr/`.
   - On submit: `multipart/form-data` with `screenshot`, `amount`, `payment_method`, `payment_type`, and: `purchased_pdf` (single), or `purchased_package` (SUBJECT_PACKAGE / YEAR_PACKAGE / FULL_PACKAGE), or `tier` (SUBSCRIPTION). Call `POST /api/payment/create/` with Bearer token.
   - On 201: save `payment_id`; go to **Payment status screen**.

4. **Payment status / waiting screen**
   - Show: “Payment submitted. Waiting for approval.”
   - Poll `GET /api/payment/status/<payment_id>/` with auth every few seconds (e.g. 5–10 s). When `status == "APPROVED"` → show success, then **pop back to PDF list** (or subject/year screen) and **refetch** the PDF list so `has_access` updates. When `status == "REJECTED"` → show “Rejected” and option to go back.
   - Optional: “Back to list” button that goes back without waiting; user can refetch list later.

5. **Packages / plans screen** (optional standalone)
   - Tab or section **Packages:** call `GET /api/subscription/packages/`, show Subject and Year packages in a list (name, price, pdf_count). Tap → open Paywall or directly Payment upload with that package.
   - Tab or section **Subscription:** call `GET /api/subscription/plans/`, show Gold and Diamond; tap → Payment upload with SUBSCRIPTION + tier.

**State and data:**
- Store `access_token` (and refresh) in secure storage. Attach `Authorization: Bearer <access_token>` to every request to PDF list, payment create, payment status, check-access.
- After any successful payment approval, refetch the PDF list(s) the user was viewing so `has_access` and `is_locked` update.
- Lock logic everywhere: `bool isLocked = pdf.is_premium && !pdf.has_access`.

**Summary:** Build (1) PDF list with lock/unlock UI, (2) Paywall with five options (single PDF / subject package / single year package / full package / subscription), (3) Payment upload (screenshot + form), (4) Status polling then back + refetch. Use the APIs in this document; keep flows simple and linear.

---

## 11a. Solutions Tab – bulk buy only (no subscription)

**Rule:** All solution PDFs = Rs 15 each. For bulk buy, use **packages only** – do **not** show Subscription (Gold/Diamond) in the Solutions tab paywall.

### API for Solutions tab paywall

When the user taps a locked solution PDF, call:

```
GET /api/subscription/packages/?subject_id={subject_id}&year={year}&solution_package_only=true
```

**Important:** `solution_package_only=true` returns only **solution** packages (Year solutions, Subject solutions, Topic solutions).

### What to show (Solutions tab paywall)

1. **Buy this PDF only** – ₹15 (single solution).  
   On tap → `payment_type: "SINGLE_PDF"`, `purchased_pdf: pdf.id`, `amount: 15`.

2. **Year solutions** – “All solutions in this year”  
   Packages with `package_type == "YEAR"` and `content_type == "SOLUTIONS"`.  
   On tap → `payment_type: "YEAR_PACKAGE"`, `purchased_package: package.id`.

3. **Subject solutions** – “All solutions in this subject”  
   Packages with `package_type == "SUBJECT"` and `content_type == "SOLUTIONS"`.  
   On tap → `payment_type: "SUBJECT_PACKAGE"`, `purchased_package: package.id`.

4. **Topic solutions** – “All solutions in this topic (all subjects)”  
   Packages with `package_type == "TOPIC"` and `content_type == "SOLUTIONS"`.  
   On tap → `payment_type: "TOPIC_PACKAGE"`, `purchased_package: package.id`.

5. **Do not show Subscription** in the Solutions tab paywall.

### Flutter checklist (Solutions tab)

- [ ] Call `GET /api/subscription/packages/?subject_id=X&year=Y&solution_package_only=true`
- [ ] Show “Buy this PDF only – ₹15” first
- [ ] Show all returned packages (Year / Subject / Topic solutions)
- [ ] Do **not** show Gold/Diamond subscription
- [ ] Use `action` field from response for `payment_type` when creating payment

---

## 12. Admin panel – how to create year-wise and subject-wise packages

**Where:** Django Admin → **PDF Packages** → **Add PDF Package**.

**Hierarchy in the app:** Topic → Subject → Year → PDFs. So each **Subject** has many **Years**, and each **Year** has many **PDFs**. Packages let the user buy either “all PDFs in this subject for this year” (year-wise) or “all PDFs in this subject, all years” (subject-wise).

### Subject package (all PDFs in one subject)

1. Click **Add PDF Package**.
2. **Name:** e.g. `Electricity and Magnetism 2081` or `Physics 2081`.
3. **Package type:** choose **“One year (subject + year) – all PDFs in this subject for this year”**.
4. **Subject:** select the subject (e.g. Electricity and Magnetism Notes).
5. **Year:** select the year (e.g. 2081).
6. **Price:** set the package price (e.g. 199).
7. **Is solution package:** leave **unchecked** for a normal “all PDFs for this year” package (questions + solutions). **Tick it** only if this package should contain **solutions only** (e.g. “Year 2081 Solutions”) so the app can show “Buy all solutions for this year” on the solutions tab.
8. Leave **PDFs** as is (do not add manually).
9. Click **Save**.  
   → Backend **auto-fills** the package: all PDFs for that subject+year, or **only solution PDFs** if “Is solution package” was ticked. After save you will see the correct **pdf_count** and the list of PDFs in “PDFs in this package”.

If no PDFs are in that subject+year yet, the package will have 0 PDFs; add PDFs to that subject/year first under **PDF Files**, then edit the package and save again to refresh the list.

### Year package (all PDFs in one year)

1. Click **Add PDF Package**.
2. **Name:** e.g. `Electricity and Magnetism – All years` or `Physics – All years`.
3. **Package type:** choose **“All years (subject) – all PDFs in this subject, all years”**.
4. **Subject:** select the subject.
5. **Year:** leave empty.
6. **Is solution package:** leave **unchecked** for “all PDFs (questions + solutions)”. **Tick** for “all solutions in this subject” (solutions-only package).
7. **Price:** set the package price.
8. Click **Save**.  
   → Backend **auto-fills** the package with **all PDFs** for that subject (or only solution PDFs if “Is solution package” was ticked). You will see the total pdf_count and the PDF list after save.

### Full package (optional)

- **Package type:** **“Full package (all years 1–4, admin selects PDFs)”**. Leave **Subject** and **Year** empty, then manually add PDFs in the **PDFs in this package** field. This is for a custom “full” bundle defined by admin.

### Solution packages (bulk buy – no subscription)

**Pricing:** Single solution = Rs 15. Bulk: Year solutions = Rs 50, Topic solutions = Rs 150.

**Quick setup – run management command:**

```bash
python manage.py create_solution_packages
```

This creates:
- **Year solutions** (Rs 50 each): All solution PDFs in that year (e.g. Year 2081 Solutions)
- **Topic solutions** (Rs 150 each): All solution PDFs in all subjects of that topic (e.g. BBS First year Solutions – All subjects)

Optional: `--year-price 50 --topic-price 150` to change prices. Use `--dry-run` to preview.

**Manual creation in Admin** (Django Admin → PDF Packages → Add):

| Type | Package type | Content type | Price | Scope |
|---|---|---|---|---|
| Year solutions | YEAR | Solutions only | Rs 50 | All solution PDFs in one year |
| Topic solutions | TOPIC | Solutions only | Rs 150 | All solution PDFs in all subjects of topic |
| Subject solutions | SUBJECT | Solutions only | (custom) | All solution PDFs in one subject |

- **Year:** Package type = YEAR, Year = 2081, Subject/Topic = empty, Content type = Solutions only, Price = 50. Save.
- **Topic:** Package type = TOPIC, Topic = select, Content type = Solutions only, Price = 150. Save.
- **Subject:** Package type = SUBJECT, Subject = select, Content type = Solutions only. Save.

Backend auto-fills PDFs. Do **not** show Subscription in Solutions tab – only Single PDF (Rs 15) and these bulk packages.

### Subscription (Gold/Diamond)

- **Subscription** is not created as a package. It comes from **Subscription plans** (`GET /api/subscription/plans/`): Gold and Diamond. Admin does not create “year-wise subscription” in PDF Package. Year-wise and subject-wise options in the app are the **packages** above (YEAR and SUBJECT). Full access to all premium is the **Subscription** (Gold/Diamond) from plans.

### Payment (Admin)

- When you **approve** a payment:  
  - **SINGLE_PDF** → one PdfAccess for that PDF.  
  - **YEAR_PACKAGE** / **SUBJECT_PACKAGE** / **TOPIC_PACKAGE** / **FULL_PACKAGE** → PdfAccess for every PDF in the purchased package.  
  - **SUBSCRIPTION** → user gets Gold/Diamond subscription (all premium unlocked for 6 months).

---

## 13. Why the paywall might only show “full access subscription”

If the app only shows **“full access subscription”** (Gold/Diamond) and **not** “Buy this PDF”, “Buy this year”, or “Buy all years (this subject)”:

- The paywall is likely calling **only** `GET /api/subscription/plans/` and **not** `GET /api/subscription/packages/?subject_id=...&year=...`.
- **Fix:** When opening the paywall (e.g. when user taps a locked PDF), the app must:
  1. Call **`GET /api/subscription/packages/?subject_id=<current_subject_id>&year=<current_year>`** (use the subject and year of the current screen). Use the response to show **year-wise** and **subject-wise** package options (and full package if any).
  2. Call **`GET /api/subscription/plans/`** to show **Gold/Diamond** (full access).
  3. Always show **“Purchase this PDF only – ₹{price}”** using the tapped PDF’s `id` and `price`.

So the **full flow** in the app is: **Topic → Subject → Year → PDF list**. When the user taps a locked PDF, the app has **subject_id** and **year** from the current screen. Pass those into the packages API so the popup can show Single PDF, This year (YEAR package), All years (SUBJECT package), and Full access (Subscription).

---

## 14. Backend verification – Flutter developer guide

This section confirms the **backend behaviour** against the Flutter “Backend Developer Guide” so there is no confusion.

### 1. PDF access logic (PDF list) — **correct, one addition**

- Your logic **“Locked: is_premium == true AND has_access == false”** is correct. The backend also returns **`is_locked`** (boolean). You can use **`is_locked`** directly as the single source of truth: **Locked = is_locked == true**. That way you don’t need to combine is_premium and has_access yourself.
- **Solution PDFs:** Backend always returns **is_premium: true** and **price: 15** for solution PDFs, so your logic works for both question and solution PDFs.

### 2. Fetching purchase options (paywall) — **correct**

- **GET /api/subscription/plans/** → Gold/Diamond (full access). Correct.
- **GET /api/subscription/packages/?subject_id={id}&year={year}** → use the **subject_id** and **year** of the current screen. Correct.
- If the packages response is **empty []**, still show **Single PDF** and **Subscription**; hide or disable only the package options that aren’t in the response.

### 3. Submitting payment (POST /api/payment/create/) — **correct, one clarification**

| Payment type     | Required fields      | Backend behaviour |
|------------------|----------------------|-------------------|
| SINGLE_PDF       | purchased_pdf (ID)   | ✅ Correct         |
| YEAR_PACKAGE     | purchased_package (ID)| ✅ Correct; package must have package_type "YEAR" |
| SUBJECT_PACKAGE  | purchased_package (ID)| ✅ Correct; package must have package_type "SUBJECT" |
| FULL_PACKAGE      | purchased_package (ID)| ✅ Correct; package must have package_type "ALL_YEARS" |
| SUBSCRIPTION     | tier                 | ✅ See below       |

- **SUBSCRIPTION tier:** Backend accepts **"gold"** or **"platinum"** (or **"diamond"**). For Diamond tier you can send **tier: "platinum"** or **tier: "diamond"** (backend normalizes to DIAMOND). So: Gold → `tier: "gold"`, Diamond → `tier: "platinum"` or `tier: "diamond"`.
- **Common fields:** amount (decimal/string), payment_method (string), screenshot (file), transaction_note (optional). All correct.

### 4. Post-payment flow — **correct**

- 201 returns **payment_id** (UUID). Poll **GET /api/payment/status/{payment_id}/** with **Authorization: Bearer &lt;token&gt;**. On **APPROVED**, refetch the PDF list so **has_access** and **is_locked** update. All correct.

### Summary

- There is **no backend bug** in this flow. The backend matches the Flutter developer guide.
- If the paywall only shows “Full Access Subscription” and not year/subject packages, the app is likely **not** calling **GET /api/subscription/packages/?subject_id=…&year=…** with the current screen’s subject_id and year, or not rendering those results. Ensure both **plans** and **packages** are requested and displayed.
- Admin must create **packages** (PDF Packages in Django admin) for each subject/year or subject so that the packages API returns them. If no packages exist for that subject (and year), the API returns an empty list and only Single PDF + Subscription can be shown.

---

*Backend: Single PDF, Subject package, Year package, and Subscription are all implemented. PDF list returns correct has_access and is_locked. Refetch list after approval to see unlocked content.*
