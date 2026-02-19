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
| POST | `feed/create/` | **Yes** | Create a new post (multipart: **up to 5 images** as `images`, title, description) → status PENDING |
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
  "image_urls": [
    "https://yourserver.com/media/feed_posts/photo1.jpg",
    "https://yourserver.com/media/feed_posts/photo2.jpg"
  ],
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

- **image_urls** – **List of up to 5 image URLs** for this post. Use this in Flutter to show a carousel/gallery (e.g. PageView or horizontal list). Order is preserved from upload.
- **image_url** – First image URL (backward compatibility). Prefer **image_urls** for multi-photo support.
- **image** – Legacy relative path; can be `null`. Prefer **image_url** or **image_urls** for display.
- **created_by** – User ID of the author; **created_by_phone** – phone (for display, e.g. “Posted by 98***678”).
- **status** – Shown only to **admin** or **post author**; values: `PENDING`, `APPROVED`, `REJECTED`. In the public feed list you only get approved posts; in **my-posts** you see your own with status.
- **like_count**, **is_liked** – Like count and whether current user liked.
- **comment_count**, **is_bookmarked** – Comment count and whether current user bookmarked.

---

## Create Post (POST feed/create/)

- **Content-Type:** `multipart/form-data`
- **Auth:** Required (Bearer token)
- **Fields:**
  - **`images`** – (optional) **up to 5 image files**. Send as **multiple parts with the same field name** `images` (e.g. in Flutter: add 1–5 file parts each with key `images`).
  - `title` – (required) string
  - `description` – (optional) string
- **Response:** 201 and the created post object (with `status: "PENDING"`, `image_urls` array). Post will **not** appear in the main feed until admin approves it.

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

- [ ] Extend/define **FeedPost** model: `id`, `image`, `imageUrl`, **`imageUrls`** (list of up to 5 URLs), `title`, `description`, `createdBy`, `createdByPhone`, `status`, `likeCount`, `isLiked`, `commentCount`, `isBookmarked`, `createdAt`, `updatedAt`.
- [ ] Define **FeedPostComment** model: `id`, `user`, `userPhone`, `text`, `createdAt`.
- [ ] API service methods:
  - `getFeedPosts()` → `GET feed/`
  - `getFeedPost(id)` → `GET feed/<id>/`
  - `createFeedPost({images, title, description})` → `POST feed/create/` (multipart: **up to 5 files** under field name `images`, auth)
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
- [ ] List of **approved** posts (from `GET feed/`): **first image from `image_urls`** (or placeholder if empty), title, description (truncated), author (e.g. created_by_phone masked), like count, comment count, like button, bookmark button.
- [ ] Pull-to-refresh to reload the list.
- [ ] Tap post → open **post detail** screen (full content, comments, like, bookmark).
- [ ] **FAB or header button:** “Create post” → open **Create post** screen (only when logged in; otherwise prompt login).

### 3. Create post screen

- [ ] Form: **1–5 images** (optional; pick from gallery/camera; allow adding multiple, max 5), **title** (required), **description** (optional).
- [ ] Submit with **multipart/form-data** to `POST feed/create/`: send each image as a part with the **same field name** `images` (e.g. `request.files['images']` list or append 1–5 parts with key `images`).
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

- [ ] **Image carousel/gallery**: use **`image_urls`** (up to 5 images). Show as PageView or horizontal scroll; dots or “1/5” indicator. If no images, show placeholder.
- [ ] Title, description, author, like button + count, bookmark button, comment count.
- [ ] Comment list and add-comment input as above.
- [ ] Same like/bookmark behavior as in the list.

### 9. Empty and error states

- [ ] Empty feed: “No posts yet” (and optional “Create the first post” if logged in).
- [ ] Loading states for list, detail, comments, and create post.
- [ ] Error states with retry or “Something went wrong” message.

---

## UI/UX Hints

- **Screen title:** Use **“TU Notice Feed”** consistently (app bar, navigation, documentation).
- **Images:** Use **`image_urls`** for multi-photo posts (carousel on detail; first image on list). Fallback to `image_url`; if null/empty, show a placeholder. Prefer cached network images.
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

All authenticated endpoints require `Authorization: Bearer <access_token>`. Use **image_urls** (and **image_url** as fallback) for display and the returned post/comment objects to keep the UI in sync after like, bookmark, and comment actions.

---

## Flutter update: support up to 5 photos per post

**Backend change:** Feed posts now support **up to 5 images** per post. Use the following in your Flutter app.

### API changes

| What | Before | After |
|------|--------|--------|
| Create post | Single optional `image` file | **Up to 5 images** with the **same field name** `images` (multipart) |
| Post response | `image_url` (single) | **`image_urls`** (list of strings, max 5). `image_url` still present (first image) |

### Flutter tasks

1. **Model**  
   - Add `imageUrls` (e.g. `List<String>?`) to your FeedPost model and parse from API `image_urls`.  
   - Keep `imageUrl` for backward compatibility (first image).

2. **Create post**  
   - Let user pick **1–5 photos** (gallery/camera).  
   - Build multipart request: for each chosen file, add a part with **name `images`** (same key for all).  
   - Example (concept): `multipartRequest.files.addAll([MapEntry('images', file1), MapEntry('images', file2), ...])` so the server receives multiple files under `images`.  
   - Do **not** send a single field `image`; use **`images`** (plural) and up to 5 files.

3. **Feed list**  
   - Show **first image** from `image_urls` (or `image_url`) as the post thumbnail; if empty, show placeholder.

4. **Post detail**  
   - Show all images in **`image_urls`** in a **PageView** or horizontal carousel with dots/indicator (e.g. “1/5”).  
   - Fallback to `image_url` if `image_urls` is null or empty.
