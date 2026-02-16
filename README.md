# Bachelor Question Bank – API (Django)

Backend API for the Bachelor Question Bank Flutter app: auth, PDFs, subscriptions, books marketplace, student uploads, and more.

---

## Run locally

```bash
python -m venv venv
source venv/bin/activate   # or: venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

- API base: `http://127.0.0.1:8000/api/`
- Admin: `http://127.0.0.1:8000/admin/`

---

## Deploy on cPanel

1. Clone this repo on your server (or upload the project). **`db.sqlite3`** is in the repo; **`media/`** is not – upload your `media/` folder to the project root if you have existing uploads.
2. Set env vars: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=yourdomain.com`.
3. See **[DEPLOYMENT_CPANEL.md](DEPLOYMENT_CPANEL.md)** for full steps (Python app, passenger_wsgi, static/media).

---

## Repo contents

- **In the repo:** App code, `requirements.txt`, `passenger_wsgi.py`, `db.sqlite3`, templates, docs.
- **Not in the repo** (in `.gitignore`): `media/`, `staticfiles/`, `venv/`, `.env`, logs.
