# Flutter: In-App Feed (Image, Title, Description) + Like – Developer Tasks

The app has a **feed** of items: each item has an **image**, **title**, and **description**. Users can **like** an item (heart/like button). Use this doc to implement the feed and like in Flutter.

**Base URL:** Same as your existing API (e.g. `https://yourserver.com/api/`).

---

## API Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `feed/` | No | List all active feed posts (newest first) |
| GET | `feed/<id>/` | No | Single post detail |
| POST | `feed/<id>/like/` | **Yes** | Like the post (idempotent) |
| POST | `feed/<id>/unlike/` | **Yes** | Remove like |

- **List and detail** work without login; `is_liked` is `false` when not logged in.
- **Like and unlike** require `Authorization: Bearer <access_token>`. On 401, refresh token and retry.

---

## Feed Post Object (response item)

```json
{
  "id": 1,
  "image": "/media/feed_posts/photo.jpg",
  "image_url": "https://yourserver.com/media/feed_posts/photo.jpg",
  "title": "Exam Tips 2079",
  "description": "Important tips for upcoming exams...",
  "like_count": 42,
  "is_liked": true,
  "created_at": "2026-02-16T10:00:00Z",
  "updated_at": "2026-02-16T10:00:00Z"
}
```

- **image_url** – Use this in Flutter to display the image (full URL). `image` is the relative path.
- **like_count** – Total number of likes (always present).
- **is_liked** – `true` if the **current user** has liked this post (only meaningful when user is logged in; otherwise `false`).
- **image** can be `null` if the post has no image (show a placeholder).

---

## Like / Unlike

- **POST `feed/<id>/like/`**  
  - No body.  
  - If already liked: returns **200** and the updated post (idempotent).  
  - If newly liked: returns **201** and the updated post.  
  - Response = same feed post object (with updated `like_count` and `is_liked: true`).

- **POST `feed/<id>/unlike/`**  
  - No body.  
  - Returns **200** and the updated post with `like_count` and `is_liked: false`.

Use the returned post to update your local state (like count and is_liked) so the UI stays in sync.

---

## Flutter Tasks Checklist

### 1. Data layer

- [ ] Define a **FeedPost** model: `id`, `image`, `imageUrl`, `title`, `description`, `likeCount`, `isLiked`, `createdAt`, `updatedAt`.
- [ ] Add API service methods:
  - `getFeedPosts()` → `GET feed/`
  - `getFeedPost(id)` → `GET feed/<id>/`
  - `likeFeedPost(id)` → `POST feed/<id>/like/` (auth required)
  - `unlikeFeedPost(id)` → `POST feed/<id>/unlike/` (auth required)
- [ ] Handle 401 on like/unlike (refresh token + retry). Handle 404 for invalid post id.

### 2. Feed screen (list)

- [ ] A **Feed** screen that shows a list (or grid) of posts.
- [ ] Each item shows:
  - **Image** – use `image_url`; if null, show a placeholder (e.g. icon or colored box).
  - **Title** – below or over the image.
  - **Description** – truncated (e.g. 2 lines) with “read more” on detail.
  - **Like count** and **like button** (heart icon).
- [ ] Pull-to-refresh to reload the list.
- [ ] Tap item → open **post detail** screen (or bottom sheet).

### 3. Like button behavior

- [ ] Show a heart (or thumb) icon; **filled** when `is_liked` is true, **outline** when false.
- [ ] Show **like count** next to the icon (e.g. “42”).
- [ ] On tap:
  - If **not logged in**: show a short message “Login to like” and optionally navigate to login.
  - If **logged in**:
    - If `is_liked` is false → call `POST feed/<id>/like/`, then set `is_liked = true` and `like_count += 1` (or use response).
    - If `is_liked` is true → call `POST feed/<id>/unlike/`, then set `is_liked = false` and `like_count -= 1` (or use response).
- [ ] Optimistic update: toggle icon and count immediately, then revert if the API call fails.

### 4. Post detail screen

- [ ] Single post: full image (if any), full title, full description, like button + count.
- [ ] Same like/unlike logic as in the list (login check, then like/unlike API, update state).
- [ ] Optional: share button (share title + image_url or link).

### 5. Empty and error states

- [ ] Empty state when there are no posts: e.g. “No posts yet” with illustration or message.
- [ ] Loading state while fetching list or detail.
- [ ] Error state if the request fails (retry or “Something went wrong”).

---

## UI/UX Hints

- **Image:** Use a cached network image (e.g. `cached_network_image`). Aspect ratio: e.g. 16:9 or 1:1; crop or fit per design.
- **Like:** One tap to like, tap again to unlike (toggle). Optional: short haptic or animation on like.
- **Placement:** Feed can be the home tab, or a “Feed” / “Updates” section in the app.

---

## Summary

| Task | Description |
|------|-------------|
| Model + API | FeedPost model; get list, get detail, like, unlike |
| Feed list | Screen with image, title, description, like count, like button |
| Like button | Filled when liked; tap to like/unlike (auth required); show count |
| Detail screen | Full post + same like behavior |
| States | Loading, empty, error; optional optimistic like |

Use **image_url** for displaying images and **like_count** / **is_liked** from the API to keep the UI in sync after like/unlike.
