# Flutter: TU Notice Feed – Developer Tasks

The **TU Notice Feed** is a Facebook-style feed: users can **create posts** (image + text), **admin approves** them, and everyone can **like**, **bookmark**, and **comment**. Use this doc to implement the **TU Notice Feed** screen and all related flows in Flutter.

**Screen name in app:** **TU Notice Feed**

**Base URL:** Same as your existing API (e.g. `https://yourserver.com/api/`).

---

## API Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `feed/` | No | List **approved** feed posts (newest first) |
| GET | `feed/<id>/` | No | Single post detail |
| POST | `feed/create/` | **Yes** | Create a new post (multipart: image, title, description) → status PENDING |
| GET | `feed/my-posts/` | **Yes** | List current user's posts (all statuses: PENDING, APPROVED, REJECTED) |
| GET | `feed/bookmarks/` | **Yes** | List feed posts the current user has bookmarked (newest first) |
| POST | `feed/<id>/like/` | **Yes** | Like the post (idempotent) |
| POST | `feed/<id>/unlike/` | **Yes** | Remove like |
| POST | `feed/<id>/bookmark/` | **Yes** | Bookmark the post (idempotent) |
| POST | `feed/<id>/unbookmark/` | **Yes** | Remove bookmark |
| GET | `feed/<id>/comments/` | No | List comments for the post |
| POST | `feed/<id>/comments/` | **Yes** | Add a comment (body: `{ "text": "..." }`) |

- **Admin only** (backend): `POST feed/<id>/approve/` and `POST feed/<id>/reject/` (used from Django admin or separate admin app; Flutter app does not need to expose these unless you have an in-app admin flow).

---

## Feed Post Object (response item)

```json
{
  "id": 1,
  "image": "/media/feed_posts/photo.jpg",
  "image_url": "https://yourserver.com/media/feed_posts/photo.jpg",
  "title": "Exam Tips 2079",
  "description": "Important tips for upcoming exams...",
  "created_by": 5,
  "created_by_phone": "+9779812345678",
  "status": "APPROVED",
  "like_count": 42,
  "is_liked": true,
  "comment_count": 8,
  "is_bookmarked": false,
  "created_at": "2026-02-16T10:00:00Z",
  "updated_at": "2026-02-16T10:00:00Z"
}
```

- **image_url** – Use this in Flutter to display the image (full URL). `image` can be `null` (show placeholder).
- **created_by** – User ID of the author; **created_by_phone** – phone (for display, e.g. “Posted by 98***678”).
- **status** – Shown only to **admin** or **post author**; values: `PENDING`, `APPROVED`, `REJECTED`. In the public feed list you only get approved posts; in **my-posts** you see your own with status.
- **like_count**, **is_liked** – Like count and whether current user liked.
- **comment_count**, **is_bookmarked** – Comment count and whether current user bookmarked.

---

## Create Post (POST feed/create/)

- **Content-Type:** `multipart/form-data`
- **Auth:** Required (Bearer token)
- **Fields:**
  - `image` – (optional) image file
  - `title` – (required) string
  - `description` – (optional) string
- **Response:** 201 and the created post object (with `status: "PENDING"`). Post will **not** appear in the main feed until admin approves it.

---

## My Bookmarks (GET feed/bookmarks/)

- **Auth:** Required (Bearer token).
- Returns only the **current user's bookmarked** feed posts (approved, active), same shape as feed list. Ordered by newest first. Each item has `is_bookmarked: true`.

---

## My Posts (GET feed/my-posts/)

- **Auth:** Required
- Returns only the **current user’s** posts, with **all statuses** (PENDING, APPROVED, REJECTED). Use this so the user can see “Under review”, “Approved”, or “Rejected” and act accordingly (e.g. show a status badge).

---

## Like / Unlike

- **POST `feed/<id>/like/`** – No body. Returns 200/201 and the updated post (use it to update `like_count` and `is_liked`).
- **POST `feed/<id>/unlike/`** – No body. Returns 200 and the updated post.

Use the returned post to update local state so the UI stays in sync.

---

## Bookmark / Unbookmark

- **POST `feed/<id>/bookmark/`** – No body. Idempotent. Returns 200/201 and the updated post (`is_bookmarked: true`).
- **POST `feed/<id>/unbookmark/`** – No body. Returns 200 and the updated post (`is_bookmarked: false`).

Use the returned post to update local state.

---

## Comments

- **GET `feed/<id>/comments/`** – No auth. Returns a list of comment objects, e.g.:

```json
[
  {
    "id": 1,
    "user": 3,
    "user_phone": "+9779812345678",
    "text": "Great post!",
    "created_at": "2026-02-16T11:00:00Z"
  }
]
```

- **POST `feed/<id>/comments/`** – Auth required. Body: `{ "text": "Your comment text" }`. Returns 201 and the created comment object. Then refresh the comment list or append the new comment and increment `comment_count` on the post.

---

## Flutter Tasks Checklist

### 1. Data layer

- [ ] Extend/define **FeedPost** model: `id`, `image`, `imageUrl`, `title`, `description`, `createdBy`, `createdByPhone`, `status`, `likeCount`, `isLiked`, `commentCount`, `isBookmarked`, `createdAt`, `updatedAt`.
- [ ] Define **FeedPostComment** model: `id`, `user`, `userPhone`, `text`, `createdAt`.
- [ ] API service methods:
  - `getFeedPosts()` → `GET feed/`
  - `getFeedPost(id)` → `GET feed/<id>/`
  - `createFeedPost({image, title, description})` → `POST feed/create/` (multipart, auth)
  - `getMyFeedPosts()` → `GET feed/my-posts/` (auth)
  - `getMyFeedBookmarks()` → `GET feed/bookmarks/` (auth)
  - `likeFeedPost(id)` → `POST feed/<id>/like/` (auth)
  - `unlikeFeedPost(id)` → `POST feed/<id>/unlike/` (auth)
  - `bookmarkFeedPost(id)` → `POST feed/<id>/bookmark/` (auth)
  - `unbookmarkFeedPost(id)` → `POST feed/<id>/unbookmark/` (auth)
  - `getFeedPostComments(id)` → `GET feed/<id>/comments/`
  - `createFeedPostComment(id, text)` → `POST feed/<id>/comments/` with `{ "text": "..." }` (auth)
- [ ] Handle 401 on authenticated calls (refresh token + retry). Handle 404 for invalid post id.

### 2. TU Notice Feed screen (list)

- [ ] **Screen name:** **TU Notice Feed**
- [ ] List of **approved** posts (from `GET feed/`): image (or placeholder), title, description (truncated), author (e.g. created_by_phone masked), like count, comment count, like button, bookmark button.
- [ ] Pull-to-refresh to reload the list.
- [ ] Tap post → open **post detail** screen (full content, comments, like, bookmark).
- [ ] **FAB or header button:** “Create post” → open **Create post** screen (only when logged in; otherwise prompt login).

### 3. Create post screen

- [ ] Form: **image** (optional; pick from gallery/camera), **title** (required), **description** (optional).
- [ ] Submit with **multipart/form-data** to `POST feed/create/`.
- [ ] On success: show message “Post submitted. It will appear in the feed after approval.” and navigate back (e.g. to feed or to “My posts”).
- [ ] On 401: prompt login and retry after auth.

### 4. My posts

- [ ] Entry point: e.g. “My posts” in profile/drawer or from the feed screen when logged in.
- [ ] Screen that calls `GET feed/my-posts/` and shows the user’s posts with a **status badge**: PENDING (Under review), APPROVED (Approved), REJECTED (Rejected).
- [ ] Optional: empty state “You haven’t posted yet” with a button to create a post.

### 4b. My bookmarks

- [ ] Entry point: e.g. "Bookmarks" or "Saved" in profile/drawer or feed menu when logged in.
- [ ] Screen that calls `GET feed/bookmarks/` and shows the same post cards as the main feed (each will have `is_bookmarked: true`). Tap opens post detail; unbookmark from detail updates list.
- [ ] Empty state: "No bookmarked posts" when the list is empty.

### 5. Like button

- [ ] Heart (or thumb) icon: **filled** when `is_liked`, **outline** when not. Show **like count** next to it.
- [ ] If not logged in: on tap show “Login to like” (and optionally navigate to login).
- [ ] If logged in: tap toggles like → call like/unlike API and update state from response (or optimistic update + revert on error).

### 6. Bookmark button

- [ ] Bookmark icon: **filled** when `is_bookmarked`, **outline** when not.
- [ ] If not logged in: on tap show “Login to bookmark”.
- [ ] If logged in: tap toggles bookmark → call bookmark/unbookmark API and update state from response.

### 7. Comments

- [ ] On **post detail**: show **comment count** and a list of comments (from `GET feed/<id>/comments/`).
- [ ] At bottom (or below comments): **comment input** + submit. If not logged in, show “Login to comment”. If logged in, on submit call `POST feed/<id>/comments/` with `{ "text": "..." }`, then refresh comments (or append new comment) and update post’s `comment_count`.

### 8. Post detail screen

- [ ] Full image (if any), title, description, author, like button + count, bookmark button, comment count.
- [ ] Comment list and add-comment input as above.
- [ ] Same like/bookmark behavior as in the list.

### 9. Empty and error states

- [ ] Empty feed: “No posts yet” (and optional “Create the first post” if logged in).
- [ ] Loading states for list, detail, comments, and create post.
- [ ] Error states with retry or “Something went wrong” message.

---

## UI/UX Hints

- **Screen title:** Use **“TU Notice Feed”** consistently (app bar, navigation, documentation).
- **Images:** Use `image_url`; if null, show a placeholder. Prefer cached network images.
- **Author:** Display `created_by_phone` masked (e.g. “98***678”) or “Anonymous” if not present.
- **Status (my posts):** Use distinct colors/labels for PENDING (e.g. orange “Under review”), APPROVED (green), REJECTED (red).
- **Create post:** Validate title required; show clear error if image upload fails or server returns 4xx/5xx.

---

## Summary

| Task | Description |
|------|-------------|
| Data layer | FeedPost + FeedPostComment models; all API methods (list, detail, create, my-posts, like, unlike, bookmark, unbookmark, comments list/create) |
| TU Notice Feed list | Screen “TU Notice Feed”: list approved posts, like + bookmark buttons, create post FAB/button |
| Create post | Form: image (optional), title, description; multipart POST; success message about approval |
| My posts | Screen “My posts”: user’s posts with status badges (PENDING/APPROVED/REJECTED) |
| Like / Bookmark | Toggle buttons; auth required; update state from API response |
| Comments | List comments on detail; add comment (auth required); update comment count |
| Detail screen | Full post + like, bookmark, comments list, add comment |
| States | Loading, empty, error for list/detail/comments/create |

All authenticated endpoints require `Authorization: Bearer <access_token>`. Use **image_url** for display and the returned post/comment objects to keep the UI in sync after like, bookmark, and comment actions.
