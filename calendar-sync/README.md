# Calendar Sync

Automatically keep your partner informed about your schedule. When you add an event to your Google Calendar, the app detects it, asks you to confirm via a mobile-friendly web app, and creates a shared calendar event with an invite.

Works as a PWA (Progressive Web App) — add it to your iPhone home screen and it looks and feels like a native app.

**Cost: $0/month.** No paid services required.

## How It Works

```
You add "Movie at Alamo Drafthouse" to your calendar
    → App detects it within the hour
    → You get a notification-style prompt on the web app:
      'Notify Sara about "Movie at Alamo"? [Yes] [Skip]'
    → You tap Yes
    → App creates "Alex at movie (Alamo Drafthouse)" on your calendar
    → Sara gets a Google Calendar invite automatically
```

## Prerequisites

- A Google account (for Google Cloud Console — no billing required)
- A free [PythonAnywhere](https://www.pythonanywhere.com) account (hosts the app)

## Setup

### Step 1: Google Cloud Project (Free, No Billing Required)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a project** (top bar) → **New Project**
3. Name it `calendar-sync-app`, click **Create**
4. Make sure the new project is selected in the top bar

### Step 2: Enable Google Calendar API

1. In the Cloud Console, go to **APIs & Services → Library**
2. Search for **Google Calendar API**
3. Click it, then click **Enable**

### Step 3: Set Up OAuth Consent Screen

The OAuth settings are under **Google Auth platform** in the left sidebar.

**3a. Branding**
1. Go to **Google Auth platform → Branding**
2. If you see "Get Started", click it
3. Fill in:
   - App name: `Calendar Sync`
   - User support email: your email
   - Developer contact: your email
4. Save

**3b. Audience**
1. Go to **Google Auth platform → Audience**
2. Set user type to **External** (if not already)
3. Under **Test users**, click **Add Users**
4. Add your email AND Sara's email (`annear.sara@gmail.com`)
5. Save

**3c. Data Access (Scopes)**
1. Go to **Google Auth platform → Data Access**
2. Click **Add or Remove Scopes**
3. Search for `calendar` or paste: `https://www.googleapis.com/auth/calendar`
4. Check it, click **Update**
5. Save

### Step 4: Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name: `Calendar Sync Desktop`
5. Click **Create**
6. Click **Download JSON** on the popup
7. Save the file — you'll upload it to PythonAnywhere in Step 6

### Step 5: Create a PythonAnywhere Account

1. Go to [pythonanywhere.com](https://www.pythonanywhere.com) and sign up for a free **Beginner** account
2. Note your username (e.g., `alexnear`) — your app will be at `https://alexnear.pythonanywhere.com`

### Step 6: Upload the Code to PythonAnywhere

1. On PythonAnywhere, go to the **Files** tab
2. Navigate to `/home/YOUR_USERNAME/`
3. Upload all files from the `calendar-sync/` folder, keeping the folder structure:
   - Upload `app.py`, `calendar_service.py`, `config.py`, `database.py`, `event_filter.py`, `requirements.txt`, `setup_auth.py`, `wsgi.py`, `scheduled_check.py`, `.env.example`
   - Create a `templates/` folder and upload `dashboard.html` into it
   - Create a `static/` folder and upload `manifest.json`, `service-worker.js`, `icon-192.png`, `icon-512.png` into it
   - Upload your `credentials.json` file (from Step 4)
4. Copy `.env.example` to `.env` and edit it with your email addresses

Alternatively, open a **Bash console** on PythonAnywhere and clone from git:
```bash
cd ~
git clone -b claude/evaluate-app-ideas-CoQpD https://github.com/alexannear-cmyk/Claude-Code.git
mv Claude-Code/calendar-sync ~/calendar-sync
rm -rf Claude-Code
cd calendar-sync
cp .env.example .env
# Edit .env with your emails:
nano .env
```
Then upload your `credentials.json` file via the Files tab into `~/calendar-sync/`.

### Step 7: Set Up Virtual Environment on PythonAnywhere

Open a **Bash console** on PythonAnywhere:

```bash
mkvirtualenv calendar-sync --python=python3.11
cd ~/calendar-sync
pip install -r requirements.txt
```

### Step 8: Authorize Both Users

Still in the PythonAnywhere Bash console:

```bash
cd ~/calendar-sync
python setup_auth.py --user alex
```

This will print a URL since PythonAnywhere can't open a browser. Copy the URL, open it in your browser, sign in with your Google account, authorize the app, and paste the authorization code back into the console.

```bash
python setup_auth.py --user sara
```

Do the same with Sara's Google account. You only need to do this once.

### Step 9: Configure the Web App on PythonAnywhere

1. Go to the **Web** tab on PythonAnywhere
2. Click **Add a new web app**
3. Choose **Manual configuration** (not Flask)
4. Select **Python 3.11**
5. In the **Code** section:
   - Set **Source code** to: `/home/YOUR_USERNAME/calendar-sync`
   - Set **Working directory** to: `/home/YOUR_USERNAME/calendar-sync`
6. In the **Virtualenv** section:
   - Set path to: `/home/YOUR_USERNAME/.virtualenvs/calendar-sync`
7. Click the **WSGI configuration file** link and replace its entire contents with:
   ```python
   import sys
   import os

   project_dir = '/home/YOUR_USERNAME/calendar-sync'
   if project_dir not in sys.path:
       sys.path.insert(0, project_dir)

   # Load environment variables from .env
   from dotenv import load_dotenv
   load_dotenv(os.path.join(project_dir, '.env'))

   from app import app as application
   from database import init_db
   init_db()
   ```
8. Save and click **Reload** on the Web tab

Your app is now live at `https://YOUR_USERNAME.pythonanywhere.com`!

### Step 10: Set Up Hourly Calendar Check

1. Go to the **Tasks** tab on PythonAnywhere
2. Add a new **Hourly** task with this command:
   ```
   cd ~/calendar-sync && /home/YOUR_USERNAME/.virtualenvs/calendar-sync/bin/python scheduled_check.py
   ```
3. Save

The app will now check both calendars every hour for new events.

### Step 11: Add to iPhone Home Screen

On your iPhone (and Sara's):

1. Open Safari and go to `https://YOUR_USERNAME.pythonanywhere.com`
2. Tap the **Share** button (square with arrow)
3. Scroll down and tap **Add to Home Screen**
4. Name it "CalSync" (or whatever you like)
5. Tap **Add**

It now appears on your home screen like a regular app. When you open it, it runs fullscreen without the Safari toolbar.

Sara can do the same on her Mac — just bookmark it or add it as a PWA in Chrome/Safari.

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask web app with dashboard and event checking logic |
| `wsgi.py` | WSGI entry point for PythonAnywhere |
| `scheduled_check.py` | Script for PythonAnywhere's hourly scheduled task |
| `calendar_service.py` | Google Calendar API (read events, create shared events) |
| `event_filter.py` | Rule-based filtering (decides what's worth sharing) |
| `database.py` | SQLite storage (processed events, pending prompts) |
| `config.py` | Configuration from environment variables |
| `setup_auth.py` | One-time Google OAuth authorization |
| `templates/dashboard.html` | Web dashboard UI (PWA-enabled) |
| `static/` | PWA manifest, service worker, app icons |
| `tests/` | Test suite (32 tests) |

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## How Event Filtering Works

The app uses keyword-based rules to decide which events are worth asking about:

**Shared** (you'll be prompted): dinner, lunch, drinks, movie, concert, doctor,
dentist, trip, travel, haircut, pick up kids, events with a location set, etc.

**Skipped** (not prompted): standups, 1:1s, focus time, gym, reminders,
work meetings on work calendars, etc.

No AI or external API is used — filtering runs entirely within the app and is completely free.

## Cost

| Component | Cost |
|---|---|
| Google Calendar API | Free |
| PythonAnywhere hosting | Free (Beginner plan) |
| SQLite database | Free (hosted file) |
| **Total** | **$0/month** |
