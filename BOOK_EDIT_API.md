# Book Edit API

Users (sellers) can edit their own book details with this endpoint.

---

## Edit book (update details)

**Endpoint:** `PATCH` or `PUT`  
**URL:** `https://pdfserver.nest.net.np/api/books/<book_id>/update/`

**Auth:** Required. Send JWT in header:
```http
Authorization: Bearer <access_token>
```

**Who can edit:** Only the **seller** (user who created the book). Others get `403 Forbidden`.

---

### Request (partial update)

Send **only the fields you want to change**. Omitted fields stay unchanged.

**Content-Type:** `multipart/form-data` (if you include a new image) or `application/json` (if only text fields).

| Field           | Type   | Required on edit | Description                    |
|----------------|--------|------------------|--------------------------------|
| `title`        | string | No               | Book title                     |
| `description`  | string | No               | Description                    |
| `price`        | decimal| No               | Price (must be > 0)            |
| `location`     | string | No               | Location                       |
| `contact_number` | string | No             | Contact number                 |
| `front_image`  | file   | No               | New cover image (omit to keep current) |
| `category`     | string | No               | One of: `ENGINEERING`, `MEDICAL`, `MANAGEMENT`, `LAW`, `SCIENCE`, `ARTS`, `OTHER` |
| `condition`    | string | No               | One of: `NEW`, `LIKE_NEW`, `GOOD`, `FAIR`, `POOR` |

**Example (JSON – only change title and price):**
```json
{
  "title": "Updated Book Title",
  "price": "450"
}
```

**Example (multipart – change image and description):**  
Send form fields `description` and `front_image` (file). Omit other fields to keep them as is.

---

### Response

**Success (200 OK):** Full book detail (same shape as `GET /api/books/<id>/`):

```json
{
  "id": 1,
  "title": "Updated Book Title",
  "description": "...",
  "price": "450.00",
  "location": "Kathmandu",
  "contact_number": "98...",
  "front_image": "https://pdfserver.nest.net.np/media/book_images/...",
  "condition": "GOOD",
  "condition_display": "Good",
  "category": "ENGINEERING",
  "category_display": "Engineering",
  "seller_name": "...",
  "seller_phone": "...",
  "is_available": true,
  "is_owner": true,
  "total_bookings": 2,
  "has_booked": false,
  "views_count": 10,
  "created_at": "2025-02-20T..."
}
```

**Errors:**

| Status | Meaning |
|--------|--------|
| `401 Unauthorized` | Missing or invalid token |
| `403 Forbidden`   | Not the seller of this book |
| `404 Not Found`   | Book with this id does not exist |
| `400 Bad Request` | Validation error (e.g. invalid category, price ≤ 0, image too large). Body has field errors. |

---

### Summary

- **URL:** `PATCH` or `PUT` `/api/books/<book_id>/update/`
- **Auth:** Bearer token (seller only)
- **Body:** Partial – only fields to change (form-data or JSON)
- **Response:** 200 with full book detail, or 4xx with error
