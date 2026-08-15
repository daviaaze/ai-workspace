---
name: browser-companion
description: Authenticated web scraping via Zen/Firefox/Chrome cookies. Access job boards (LinkedIn, Indeed, Glassdoor), company career pages, and any authenticated content using the browser's existing login session. Use when the user wants to scrape a page that requires login, fetch job postings from authenticated sources, or research companies behind auth walls.
---

# Browser Companion

Authenticated scraping using the browser's existing login session. No API keys, no re-login — just reuse the cookies you already have.

## Three Modes

### 1. CDP Mode (recommended for dynamic pages)

Connect to a running browser via Chrome DevTools Protocol. The browser handles all auth, JavaScript rendering, and anti-bot checks.

**Prerequisites:**
- Browser running with remote debugging enabled
- Zen Browser: `zen --remote-debugging-port=9222`
- Firefox: `firefox --remote-debugging-port=9222`
- Chrome/Chromium: `chromium --remote-debugging-port=9222`

```bash
# Screenshot of authenticated page
browser-companion cdp --url "https://linkedin.com/jobs/view/123" --action screenshot --output job.png

# Extract rendered text (after JS execution)
browser-companion cdp --url "https://linkedin.com/jobs/view/123" --action text --output job.html

# Get full HTML content
browser-companion cdp --url "https://linkedin.com/jobs/view/123" --action content

# Execute JavaScript in page context
browser-companion cdp --url "https://linkedin.com/jobs/view/123" --action evaluate --script "document.querySelector('.description').innerText"

# List all open tabs
browser-companion list
```

### 2. Cookie Mode (lightweight, browser closed)

Directly reads cookies from browser's SQLite database. Browser must be closed.

```bash
# List all cookies for a domain
browser-companion cookies --browser zen --domain linkedin.com

# Save cookies to JSON for reuse
browser-companion cookies --browser zen --domain .linkedin.com --output /tmp/linkedin-cookies.json
```

### 3. Session Mode (requests-based scraping)

Creates a `requests.Session` pre-loaded with browser cookies. Best for simple HTTP scraping.

```bash
# Fetch an authenticated page
browser-companion session --browser zen --domain linkedin.com --url "https://linkedin.com/jobs/view/123"

# Save HTML
browser-companion session --browser zen --domain linkedin.com --url "https://linkedin.com/jobs/view/123" --output job.html
```

## Supported Browsers

| Browser | Cookie DB | Notes |
|---------|-----------|-------|
| Zen Browser | ✅ | Firefox-based, cookies in `~/.zen/` |
| Firefox | ✅ | Standard `~/.mozilla/firefox/` |
| LibreWolf | ✅ | Firefox-based |

> **CDP mode (Playwright)** requires Firefox binaries with system libs — works best on standard Linux. On NixOS, the **cookie/sqlite mode** is recommended.

## How It Works

1. **Copy** `cookies.sqlite` from Zen profile to temp (avoids lock if browser open)
2. **Read** cookies from sqlite (Firefox 133+ stores plaintext — no keyring needed)
3. **Build** a `requests.Session` pre-loaded with those cookies
4. **Fetch** any URL as if you were logged in

## Job Board Usage

### Any site you're logged into in Zen

```bash
# Generic: works for any authenticated site
browser-companion fetch --url "https://example.com/profile" --domain example.com

# Export cookies for external tools
browser-companion cookies --domain linkedin.com --output /tmp/li-cookies.json

# Check you're logged in
browser-companion whoami --domain linkedin.com
```

### LinkedIn (when logged in)

```bash
# Get current user info
browser-companion whoami

# Fetch job page HTML (200 OK with auth; SPA means content needs parsing)
browser-companion fetch --url "https://linkedin.com/jobs/view/123" --domain linkedin.com --output job.html

# Voyager API (may need additional headers — fragile)
browser-companion linkedin-job --job-id 123 --output job.json
```

### Server-rendered job boards (Indeed, Seek, etc.)

```bash
# Works when logged in; some boards serve public content without auth
browser-companion fetch --url "https://au.indeed.com/jobs?q=backend" --domain indeed.com
browser-companion fetch --url "https://www.seek.com.au/backend-jobs" --domain seek.com.au
```

## Integration with job-tracker

Feed authenticated scraping directly into the job tracker:

```bash
# 1. Scrape job posting with browser companion
browser-companion cdp --url "$JOB_URL" --action text --output /tmp/jd.txt

# 2. Analyze fit with job-tracker
aiw-job-fit analyze --jd-file /tmp/jd.txt

# 3. Save to pipeline
aiw-job add --company "$COMPANY" --role "$ROLE" --source linkedin --url "$JOB_URL"
```

## Troubleshooting

**"No cookies found":**
- You're not logged into that domain in Zen
- Open Zen, log in to the site, then retry
- Check domain spelling: `linkedin.com` vs `.linkedin.com`

**LinkedIn Voyager API returns 403:**
- LinkedIn's API requires CSRF token rotation + `li_at` cookie
- The voyager API is fragile — use `fetch` to get HTML instead
- For reliable LinkedIn scraping, consider their official API or browser automation

**"database is locked":**
- The script copies the sqlite to temp first — this should not happen
- If it does, close Zen and retry

**Cookies empty/encrypted:**
- Firefox 133+ stores plaintext — no keyring needed
- If you see empty `value` column, the cookies may be encrypted with a master password
- Solution: remove master password in Zen → Settings → Privacy → Passwords

## Architecture

```
┌─────────────────────────────────────────────┐
│ Browser (Zen/Firefox/Chrome)                │
│  ├── Logged into LinkedIn, Indeed, etc.     │
│  ├── Cookies in cookies.sqlite              │
│  └── CDP endpoint on localhost:9222         │
└───────────┬──────────────┬──────────────────┘
            │              │
     ┌──────▼──────┐ ┌────▼──────────┐
     │ CDP Mode    │ │ Cookie Mode   │
     │ (browser    │ │ (browser      │
     │  running)   │ │  closed)      │
     └──────┬──────┘ └────┬──────────┘
            │              │
            └──────┬───────┘
                   │
            ┌──────▼──────┐
            │ Session Mode│
            │ (requests)  │
            └─────────────┘
```

## Security Notes

- Cookies never leave your machine
- No third-party services involved
- CDP only connects to localhost
- Cookie database is read-only
