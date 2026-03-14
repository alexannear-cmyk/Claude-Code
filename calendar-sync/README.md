# Calendar Sync

Automatically keep your partner informed about your schedule. When you add an event to your Google Calendar, the app uses AI to decide if your partner should know about it, texts you to confirm, and creates a shared calendar event with an invite.

## How It Works

```
You add "Movie at Alamo Drafthouse" to your calendar
    → App detects it within the hour
    → You get a text: 'Notify Sara about "Movie at Alamo"? Reply Y or N'
    → You reply Y
    → App creates "Alex at movie (Alamo Drafthouse)" on your calendar
    → Sara gets a Google Calendar invite automatically
```

## Prerequisites

- Python 3.12+
- A Google Cloud account (free tier is sufficient)
- A Twilio account (free trial works for testing)
- An Anthropic API key

## Setup

### Step 1: Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (e.g., `calendar-sync-app`)
3. Enable the **Google Calendar API**:
   - Go to **APIs & Services > Library**
   - Search for "Google Calendar API" and click **Enable**
4. Enable **Cloud Firestore**:
   - Go to **Firestore** in the console
   - Click **Create Database**
   - Choose **Native mode** and pick a region (e.g., `us-central1`)

### Step 2: OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Configure Consent Screen**:
   - Choose **External**
   - App name: "Calendar Sync"
   - Add your email as support contact and developer contact
   - Add scope: `https://www.googleapis.com/auth/calendar`
   - Add both your and your partner's emails as **Test Users**
   - Save
3. Go back to **Credentials > Create Credentials > OAuth Client ID**
   - Application type: **Desktop app**
   - Download the JSON file and save it as `credentials.json` in this directory

### Step 3: Twilio

1. Sign up at [twilio.com](https://www.twilio.com) (free trial gives $15 credit)
2. Get a phone number from the Twilio console
3. Note your **Account SID**, **Auth Token**, and **phone number**

### Step 4: Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key

### Step 5: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in all values.

### Step 6: Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 7: Authorize Both Users

Run the auth setup once for each user. This opens a browser window to sign in with Google:

```bash
# Make sure you have gcloud CLI installed and configured:
# gcloud auth application-default login

python setup_auth.py --user alex
# Sign in with Alex's Google account in the browser

python setup_auth.py --user sara
# Sign in with Sara's Google account in the browser
```

### Step 8: Deploy

```bash
# Make sure gcloud CLI is installed and authenticated:
# gcloud auth login
# gcloud config set project YOUR_PROJECT_ID

./deploy.sh
```

The deploy script will:
- Deploy both Cloud Functions
- Set up the hourly Cloud Scheduler job
- Print the Twilio webhook URL to configure

### Step 9: Configure Twilio Webhook

After deployment, the script prints a Reply URL. Configure it in Twilio:

1. Go to [Twilio Phone Numbers](https://console.twilio.com/us1/develop/phone-numbers)
2. Click your phone number
3. Under **Messaging > A message comes in**, set:
   - Webhook URL: `<the Reply URL from deploy output>`
   - HTTP Method: `POST`
4. Save

## Testing Locally

You can test the check function locally:

```bash
source .venv/bin/activate
functions-framework --target check_new_events --debug
```

Then trigger it:

```bash
curl http://localhost:8080
```

## Files

| File | Purpose |
|---|---|
| `main.py` | Cloud Function entry points (check events + handle SMS replies) |
| `calendar_service.py` | Google Calendar API operations |
| `ai_filter.py` | Claude-powered event filtering |
| `sms_service.py` | Twilio SMS send/receive |
| `config.py` | Configuration from environment variables |
| `setup_auth.py` | One-time OAuth authorization script |
| `deploy.sh` | Google Cloud deployment script |

## Cost

| Service | Monthly Cost |
|---|---|
| Google Cloud Functions | Free (within free tier) |
| Cloud Scheduler | Free (1 job free) |
| Firestore | Free (within free tier) |
| Twilio SMS | ~$1-3 (number + messages) |
| Anthropic API | ~$0.50-1 |
| **Total** | **~$2-4/month** |
