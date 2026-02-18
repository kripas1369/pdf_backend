# Fix 404 on pdfserver.nest.net.np

## Step 1: Find the domain document root

1. In cPanel go to **Domains** → **Domains** (or **Addon Domains**)
2. Find **pdfserver.nest.net.np** and note its **Document Root**

Common values:
- `public_html` (main domain)
- `pdfserver.nest.net.np` or `public_html/pdfserver.nest.net.np` (addon)

## Step 2: Align application root with document root

**Option A – Document root = pdf_backend**

In **Setup Python App** → Edit your app:
- **Application root:** `/home2/pdfserve/pdf_backend` (use full path)
- Ensure `passenger_wsgi.py` exists in `/home2/pdfserve/pdf_backend/`

Then change the domain’s document root to `/home2/pdfserve/pdf_backend`:
- Domains → Manage → Change document root to `pdf_backend` (or `/home2/pdfserve/pdf_backend`)

**Option B – Document root is different (e.g. public_html/pdfserver.nest.net.np)**

If the document root is elsewhere:

1. Copy `passenger_wsgi_bootstrap.py` into the document root
2. Rename it to `passenger_wsgi.py` in that folder
3. Update `APP_ROOT` in the bootstrap to:
   ```python
   APP_ROOT = '/home2/pdfserve/pdf_backend'
   ```

## Step 3: Verify Setup Python App settings

- **Application root:** `/home2/pdfserve/pdf_backend`
- **Application URL:** `pdfserver.nest.net.np`
- **Application startup file:** `passenger_wsgi.py`
- **Application entry point:** `application`

## Step 4: Environment variables

In Setup Python App, add:
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG` = `0`
- `DJANGO_ALLOWED_HOSTS` = `pdfserver.nest.net.np,www.pdfserver.nest.net.np`

## Step 5: Fix Passenger (if supported)

If your host allows it, run as root or ask support:

```bash
/usr/local/bin/ea-passenger-runtime-applications-settings --fix
```

## Step 6: Restart the app

- Click **Restart** in Setup Python App
- Touch restart file:  
  `touch /home2/pdfserve/pdf_backend/tmp/restart.txt`

## Step 7: Test these URLs

- https://pdfserver.nest.net.np/admin/
- https://pdfserver.nest.net.np/api/
(Do not rely on the root `/` – it has no page.)
