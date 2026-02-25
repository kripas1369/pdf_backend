# Send Feedback — Flutter (in-app form)

One screen: **dropdown** (feedback type) + **one text field** (message) + **Submit**.

**API base:** `https://your-domain.com/api/`  
**Auth:** Optional. If you send the **Bearer token** (logged-in user), the backend stores **which user** created the feedback. If no token, feedback is stored with `user: null` (anonymous).

---

## API: Submit feedback

**POST** `/api/feedback/`  
**Content-Type:** `application/json`  
**Headers (optional):** `Authorization: Bearer <access_token>` — if sent, feedback is linked to that user.

### Request body

| Field         | Type   | Required | In your UI        |
|---------------|--------|----------|-------------------|
| `name`        | string | Yes      | **Dropdown** value (e.g. "Bug", "Suggestion", "Other") |
| `description` | string | Yes      | **Text field** (user’s message) |

### Example request

```json
{
  "name": "Bug",
  "description": "App crashes when I open PDF in landscape."
}
```

### Success: 201 Created

Response includes **who created it**: `user` (id or null) and `user_display` (name/phone for display).

```json
{
  "id": 1,
  "user": 42,
  "user_display": "9841234567",
  "name": "Bug",
  "description": "App crashes when I open PDF in landscape.",
  "created_at": "2025-02-25T10:30:00Z"
}
```

If submitted without auth: `"user": null`, `"user_display": null`.

### Error: 400 Bad Request (validation)

```json
{
  "name": ["This field may not be blank."],
  "description": ["This field may not be blank."]
}
```

---

## Flutter: Send feedback screen

**UI:** One dropdown + one text field + Submit button.

- **Dropdown** → send as `name` (e.g. "Bug", "Suggestion", "General", "Other").
- **Text field** → send as `description`.

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

const baseUrl = 'https://your-domain.com/api';

// Dropdown options (value sent as "name")
const feedbackTypes = ['Bug', 'Suggestion', 'General', 'Other'];

Future<void> submitFeedback({
  required String type,       // from dropdown
  required String message,    // from text field
  String? accessToken,        // if user is logged in, so backend stores who created it
}) async {
  final headers = {'Content-Type': 'application/json'};
  if (accessToken != null) {
    headers['Authorization'] = 'Bearer $accessToken';
  }

  final response = await http.post(
    Uri.parse('$baseUrl/feedback/'),
    headers: headers,
    body: jsonEncode({
      'name': type,
      'description': message,
    }),
  );

  if (response.statusCode == 201) {
    final data = jsonDecode(response.body);
    // data['id'], data['user'], data['user_display'], data['created_at']
  } else if (response.statusCode == 400) {
    // Show validation errors: jsonDecode(response.body)
  }
}
```

**Example screen layout:**

- **Dropdown:** `type` → `name` (e.g. `feedbackTypes` above).
- **TextField:** `message` → `description` (multiline if you want).
- **Button:** on tap call `submitFeedback(type: selectedType, message: messageController.text, accessToken: currentUserToken)`. Pass the JWT if the user is logged in so the backend records who created the feedback.

**In the feed / list:** Each feedback has `user` (id or null) and `user_display` (e.g. phone or name) so you can show “Created by &lt;user_display&gt;” or “Anonymous”.
