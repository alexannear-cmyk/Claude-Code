# Calendar Sync

Automatically keep your partner informed about your schedule. When you add an event to your Google Calendar, the app detects it, asks you via a simple web dashboard if your partner should know, and creates a shared calendar event with an invite.

**Cost: $0/month.** No paid services required.

## How It Works

```
You add "Movie at Alamo Drafthouse" to your calendar
    → App detects it within the hour
    → Dashboard shows: 'Notify Sara about "Movie at Alamo"? [Yes] [Skip]'
    → You click Yes
    → App creates "Alex at movie (Alamo Drafthouse)" on your calendar
    → Sara gets a Google Calendar invite automatically
```

## Prerequisites

- Python 3.11+
- A Google account (for Google Cloud Console — no billing required)

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

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External**, click **Create**
3. Fill in:
   - App name: `Calendar Sync`
   - User support email: your email
   - Developer contact: your email
4. Click **Save and Continue**
5. On the **Scopes** page, click **Add or Remove Scopes**
   - Find and check `https://www.googleapis.com/auth/calendar`
   - Click **Update**, then **Save and Continue**
6. On the **Test users** page, click **Add Users**
   - Add your email AND Sara's email (`annear.sara@gmail.com`)
   - Click **Save and Continue**
7. Click **Back to Dashboard**

### Step 4: Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name: `Calendar Sync Desktop`
5. Click **Create**
6. Click **Download JSON** on the popup
7. Save the downloaded file as `credentials.json` in the `calendar-sync/` folder

### Step 5: Configure

```bash
cd calendar-sync
cp .env.example .env
```

Edit `.env` with your email addresses:
```
ALEX_EMAIL=your-email@gmail.com
SARA_EMAIL=annear.sara@gmail.com
```

### Step 6: Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 7: Authorize Both Users

This opens a browser window for each user to sign in with Google:

```bash
python setup_auth.py --user alex
# A browser window opens — sign in with YOUR Google account
# Click through the consent prompts and allow access

python setup_auth.py --user sara
# A browser window opens — Sara signs in with HER Google account
# She clicks through consent prompts and allows access
```

Tokens are saved locally in the `tokens/` folder. You only need to do this once.

### Step 8: Run the App

```bash
python app.py
```

Open your browser to **http://127.0.0.1:5000** to see the dashboard.

The app will check both calendars every hour in the background. You can also click to trigger a manual check.

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask web app + background scheduler |
| `calendar_service.py` | Google Calendar API (read events, create shared events) |
| `event_filter.py` | Rule-based filtering (decides what's worth sharing) |
| `database.py` | SQLite storage (processed events, pending prompts) |
| `config.py` | Configuration from environment variables |
| `setup_auth.py` | One-time Google OAuth authorization |
| `templates/dashboard.html` | Web dashboard UI |
| `tests/` | Test suite (32 tests) |

## Running Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

## How Event Filtering Works

The app uses keyword-based rules to decide which events are worth asking about:

**Shared** (you'll be prompted): dinner, lunch, drinks, movie, concert, doctor,
dentist, trip, travel, haircut, pick up kids, events with a location set, etc.

**Skipped** (not prompted): standups, 1:1s, focus time, gym, reminders,
work meetings on work calendars, etc.

No AI or external API is used — filtering runs locally and is completely free.

## Cost

| Component | Cost |
|---|---|
| Google Calendar API | Free |
| Python + Flask | Free (runs locally) |
| SQLite | Free (local file) |
| **Total** | **$0/month** |
