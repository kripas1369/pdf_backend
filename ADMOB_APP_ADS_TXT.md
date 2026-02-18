# app-ads.txt – AdMob Verification (Bachelor Question Bank)

## Backend implementation

The file is served at: **`https://pdfserver.nest.net.np/app-ads.txt`**  
(Developer website in Play Console must be exactly: **https://pdfserver.nest.net.np**)

Content (IAB format; exact AdMob snippet with spaces):
```
google.com, pub-9127715515165521, DIRECT, f08c47fec0942fa0
```

---

## If AdMob says "details don't match"

### 1. Domain must match exactly

The **Developer website** in Google Play Console must point to the same domain that serves app-ads.txt.

- **Play Console** → Your app → **Store presence** → **App details** → **Developer website**
- That URL’s domain must be the one serving app-ads.txt.

**Example:** If your backend is at `https://api.bachelorquestionbank.com`, then:
- Developer website must be: `https://api.bachelorquestionbank.com` (or root domain that redirects there)
- app-ads.txt must be at: `https://api.bachelorquestionbank.com/app-ads.txt`

**Typical problems:**
- Developer website = `https://www.example.com` but app-ads.txt is on `https://api.example.com` → **verification fails**
- Developer website = `https://example.com` but app-ads.txt is on `https://www.example.com` → **verification fails** (www vs non-www)

**Fix:** In Play Console, set **Developer website** to the exact URL of your deployed backend (the domain that serves app-ads.txt).

### 2. Check publisher ID

Confirm `pub-9127715515165521` in your AdMob account:

- [AdMob Console](https://admob.google.com) → **Account** → **Publisher IDs**

If it’s different, update `pdf_server/views.py` in `app_ads_txt()`.

### 3. HTTPS and accessibility

- app-ads.txt must be reachable over **HTTPS** in production.
- No login or auth required.
- No redirects (301/302) – direct 200 response.

### 4. "Bot Verification" page instead of app-ads.txt

If opening `https://pdfserver.nest.net.np/app-ads.txt` in a browser shows **"Verifying that you are not a robot..."** (or similar), the file is **not** being served to Google’s crawler. That page is from your **hosting or CDN** (e.g. Cloudflare, cPanel/Imunify360), not from Django.

**What to do:**

- **Cloudflare:** In **Security** → **WAF** or **Bot Fight Mode**, add a rule or exception so that requests to `/app-ads.txt` are **not** challenged (or allow known good bots). Alternatively, use **Page Rules** or **Configuration Rules** to disable bot protection for the path `/app-ads.txt`.
- **cPanel / Imunify360 / other:** In the security or firewall settings, whitelist the path `/app-ads.txt` or allow **Googlebot** so it receives the real file (plain text), not a challenge page.
- **Goal:** A direct `GET https://pdfserver.nest.net.np/app-ads.txt` (e.g. with `curl` or a browser) should return **only** the one line of app-ads.txt with status **200**, no captcha and no redirect.

Until the crawler can read the actual file content, AdMob will keep reporting that app-ads.txt is not found or doesn’t match.

### 5. Check the live file

```bash
curl -v https://your-domain.com/app-ads.txt
```

Response should be:
- Status: `200 OK`
- Content-Type: `text/plain; charset=utf-8`
- Body: `google.com, pub-9127715515165521, DIRECT, f08c47fec0942fa0` (one line, optional trailing newline)

### 6. Re-verify in AdMob

After any change:

1. Wait 5–10 minutes.
2. AdMob → **App-ads.txt** → **Check for updates**.

---

## Optional: custom content

To change the app-ads.txt line, edit `pdf_server/views.py` in the `app_ads_txt()` function.
