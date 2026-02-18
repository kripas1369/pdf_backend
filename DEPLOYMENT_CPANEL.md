# Deploy Django (pdf_server) to cPanel

This guide helps you publish the Bachelor Question Bank API on a cPanel host.

---

## 0. Clone from GitHub on cPanel

If you **cloned this repo** on cPanel (no manual upload):

1. **Clone** the repo into your app folder (e.g. `~/pdf_server/` or `~/public_html/your-api/`). **`db.sqlite3`** is in the repo. **`media/`** is not – upload your `media/` folder to the project root if you have existing PDFs/images.
2. Set **permissions**: chmod 664 for `db.sqlite3`, 775 for `media/` and its subfolders (cPanel File Manager → Change Permissions).
3. **Set environment variables** in cPanel (see section 1.1): `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=yourdomain.com`.
4. **Install and run:**
   ```bash
   cd /home/youruser/pdf_server   # or your app path
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
5. **Restart** the Python app in cPanel.

After that, follow the rest of this guide (Setup Python App, passenger_wsgi, etc.) if needed.

---

## 0.1 After cloning – venv and run (step-by-step)

You cloned the project; next steps depend on how your cPanel runs Python.

### Option A: cPanel “Setup Python App” (recommended)

cPanel will create the virtual environment for you when you create the app.

1. **Create the Python app in cPanel**
   - Go to **Setup Python App** → **Create Application**.
   - **Python version:** e.g. 3.12.11 (whatever your host offers).
   - **Application root:** the folder where you cloned (e.g. `pdf_backend` → full path like `/home/youruser/pdf_backend`).
   - **Application URL:** your domain or subdomain.
   - **Application startup file:** `passenger_wsgi.py`
   - **WSGI callable:** `application`
   - Save. cPanel creates a virtualenv (e.g. `/home/youruser/virtualenv/pdf_backend/3.12`).

2. **Add environment variables** in the same app:
   - `DJANGO_SECRET_KEY` = generate: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
   - `DJANGO_DEBUG` = `0`
   - `DJANGO_ALLOWED_HOSTS` = `yourdomain.com,www.yourdomain.com`

3. **Install dependencies and run Django** (SSH or cPanel “Run” / terminal):
   ```bash
   cd /home/youruser/pdf_backend
   source /home/youruser/virtualenv/pdf_backend/3.12/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
   Use the **exact** virtualenv path cPanel shows for your app (e.g. 3.11 or 3.12 in the path).

4. **Restart** the app in Setup Python App.

### Option B: SSH only (create .venv yourself)

If you are not using Setup Python App and only have SSH:

1. **Go to project folder and create a venv**
   ```bash
   cd /home/youruser/pdf_backend
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies and run Django**
   ```bash
   pip install -r requirements.txt
   export DJANGO_SECRET_KEY="your-generated-secret"
   export DJANGO_DEBUG=0
   export DJANGO_ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

3. **Run the server** (for testing only; in production cPanel/Passenger will run the app):
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   For production you still need to use **Setup Python App** (Option A) so cPanel serves the app via Passenger.

### Permissions (both options)

- **db.sqlite3:** `chmod 664 db.sqlite3`
- **media/** (if you create or upload it): `chmod -R 775 media`

---

## 1. Before you upload

### 1.1 Environment variables (production)

Your project reads these from the server environment. Set them in cPanel **Setup Python App** → **Environment variables** (or in the app’s `passenger_wsgi` / `.env` if your host supports it):

| Variable | Example | Purpose |
|----------|--------|--------|
| `DJANGO_SECRET_KEY` | (long random string) | **Required in production.** Generate: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `0` | Set to `0` on production. |
| `DJANGO_ALLOWED_HOSTS` | `yourdomain.com,www.yourdomain.com` | Comma-separated list of domains. |

### 1.2 Optional: OTP / SMS provider

OTP for forgot password is currently printed to terminal only. When you add a 3rd party SMS/OTP API, plug it into `pdf_app/utils.py` in `send_whatsapp_otp()` and keep any API keys in environment variables.

### 1.3 Database and media

- **`db.sqlite3`** is in the repo (pushed to GitHub); it comes with the clone. Set permissions so the app can write to it (e.g. chmod 664).
- **`media/`** is not in the repo. Upload your `media/` folder to the project root if you have existing uploads; set 775 for the folder and subfolders.

### 1.4 Don’t upload (exclude when uploading)

- `__pycache__/`, `*.pyc`
- `venv/` or `.venv/` (you’ll create a new one on the server)
- `staticfiles/` (you’ll run `collectstatic` on the server)
- `.env` (if you use one locally; use cPanel env vars instead)
- `*.log`, `debug.log`

---

## 2. What to upload to cPanel

Upload the whole project (e.g. via **File Manager** or **Git**) into a folder under your home, for example:

- `~/pdf_server/`  
  or  
- `~/public_html/pdf_api/` (if you want the API under a subdomain/subpath)

**`db.sqlite3`** is in the repo and comes with the clone. **`media/`** is not – upload it to the project root if you have existing PDFs/images.

Typical structure on server:

```
home/youruser/
  pdf_server/           ← project root
    manage.py
    passenger_wsgi.py
    requirements.txt
    db.sqlite3          ← upload your existing DB (users, PDFs, data)
    media/              ← upload your existing media (PDFs, images)
      pdfs/
      book_images/
    pdf_server/
      settings.py
      urls.py
      wsgi.py
    pdf_app/
    books/
    templates/
    static/
```

After upload, set permissions so the web/app user can write to `db.sqlite3` and to the `media/` directory (e.g. chmod 664 for `db.sqlite3`, 775 for `media/` and its subfolders). In cPanel File Manager use **Change Permissions**.

---

## 3. cPanel “Setup Python App” (typical steps)

Many cPanel hosts use **Setup Python App** or **Application Manager**.

1. **Create the application**
   - **Setup Python App** → **Create Application**.
   - **Python version:** 3.10 or 3.11 (match your local).
   - **Application root:** folder that contains `manage.py` (e.g. `pdf_server`).
   - **Application URL:** domain or subdomain (e.g. `api.yourdomain.com` or `yourdomain.com`).
   - **Application startup file:** often `passenger_wsgi.py` (see below).
   - **Application entry point:** `application` (WSGI callable).

2. **Set environment variables**
   - In the same interface, add:
     - `DJANGO_SECRET_KEY` = (generated secret)
     - `DJANGO_DEBUG` = `0`
     - `DJANGO_ALLOWED_HOSTS` = `yourdomain.com,www.yourdomain.com,api.yourdomain.com`
   - Save.

3. **Virtual environment and dependencies**
   - In the app’s **Configuration** or **Run** section, use the virtualenv and install deps, for example:
     - `source /home/youruser/virtualenv/pdf_server/3.10/bin/activate`
     - `cd /home/youruser/pdf_server`
     - `pip install -r requirements.txt`
   - Or run the same via **SSH** if available.

4. **Run migrations and collectstatic**
   - In the same env:
     - `python manage.py migrate`   (safe even if you uploaded `db.sqlite3` – applies any missing migrations)
     - `python manage.py collectstatic --noinput`
   - If you did **not** upload `db.sqlite3`, create superuser for admin:  
     `python manage.py createsuperuser`  
     If you **did** upload your DB, your existing admin user(s) already work.

5. **Restart the app**
   - Use **Restart** in Setup Python App so the new env vars and code are loaded.

---

## 4. WSGI entry point for cPanel (Passenger)

cPanel often uses **Passenger** and looks for `passenger_wsgi.py` in the **application root** (the folder with `manage.py`).

Create this file in the **project root** (same level as `manage.py`):

**passenger_wsgi.py** (in project root, next to `manage.py`):

```python
import os
import sys

# Optional: add your project directory to path (some hosts need this)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Required for Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdf_server.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Point the Python app’s **startup file** to `passenger_wsgi.py` and **entry point** to `application`.

---

## 5. Static and media files

- **Static (CSS, JS, admin):**  
  Run once (and after any static change):  
  `python manage.py collectstatic --noinput`  
  Files go to `STATIC_ROOT` (e.g. `staticfiles/`).  
  In cPanel/Apache you can add an **Alias** for `/static` to that folder so the server serves them (recommended). If not, Django can serve them in production by adding the static URL in `urls.py` (less efficient).

- **Media (user uploads – PDFs, images):**  
  Stored in `MEDIA_ROOT` (e.g. `media/`).  
  The project is set up to serve `/media/` via Django in production so uploads work even without an Apache alias. For high traffic, later you can alias `/media` to `media/` in Apache.

---

## 6. Database (SQLite vs MySQL)

- **SQLite (default):**  
  Works on cPanel. The file will be at `BASE_DIR / 'db.sqlite3'`. Ensure the app user has **write** permission on that directory. No extra DB setup.

- **MySQL (optional):**  
  If your host prefers MySQL:
  1. Create a database and user in cPanel (MySQL® Databases).
  2. In `settings.py` (or via env), set:
     - `ENGINE': 'django.db.backends.mysql'`
     - `NAME'`, `USER'`, `PASSWORD'`, `HOST'`, `PORT'`
  3. Install: `pip install mysqlclient`
  4. Run `migrate` again.

---

## 7. Checklist after deploy

- [ ] `DJANGO_DEBUG=0` and `DJANGO_ALLOWED_HOSTS` set.
- [ ] `DJANGO_SECRET_KEY` set (new, not the one from the repo).
- [ ] `migrate` and `collectstatic` run.
- [ ] Superuser created if you need admin.
- [ ] Visit `https://yourdomain.com/admin/` and log in.
- [ ] Test API: `https://yourdomain.com/api/` (e.g. topics or auth).
- [ ] Flutter app: set base URL to `https://yourdomain.com/api/` and use HTTPS.

---

## 8. Common issues

- **500 error:** Check the app’s error log in cPanel (or `error_log` in the app directory). Often: wrong `DJANGO_SETTINGS_MODULE`, missing env vars, or import errors.
- **Static/admin CSS missing:** Run `collectstatic` and ensure `/static` is served (alias or Django).
- **Media uploads 404:** Ensure `MEDIA_ROOT` exists and is writable; the project is configured to serve `/media/` in production.
- **CSRF / CORS:** For Flutter (or a web app on another domain), keep `CORS_ALLOW_ALL_ORIGINS = True` only if you accept that; for production you may restrict `CORS_ALLOWED_ORIGINS` to your app’s domain(s).

---

## 9. Quick reference – URLs on production

- Admin: `https://yourdomain.com/admin/`
- API base: `https://yourdomain.com/api/`
- Examples:  
  `https://yourdomain.com/api/auth/login/`  
  `https://yourdomain.com/api/topics/`  
  `https://yourdomain.com/api/books/`  
  `https://yourdomain.com/app-ads.txt`  
  `https://yourdomain.com/privacy_policy`

Update your Flutter app’s base URL to this API base and use HTTPS.
