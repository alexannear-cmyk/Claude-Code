# Calendar Sync App — MVP Implementation Plan

## Overview
A Python app that monitors both Alex's and Sara's Google Calendars, uses AI to identify events the other person should know about, prompts the creator via SMS, and (on approval) creates a shared notification event on the creator's calendar with the other person invited.

---

## Phase 0: Google Cloud & Account Setup (Manual — One Time)

### 0.1 Create a Google Cloud Project
1. Go to https://console.cloud.google.com
2. Click "Select a project" → "New Project"
3. Name it something like `calendar-sync-app`
4. Note the **Project ID**

### 0.2 Enable Required APIs
In the Google Cloud Console, go to **APIs & Services → Library** and enable:
- **Google Calendar API**

### 0.3 Create OAuth 2.0 Credentials
1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth Client ID**
3. If prompted, configure the **OAuth Consent Screen** first:
   - Choose "External" user type
   - Fill in app name ("Calendar Sync"), your email for support/developer contact
   - Add scope: `https://www.googleapis.com/auth/calendar` (full calendar access)
   - Add both your and Sara's emails as **Test Users** (required while app is in "Testing" mode)
4. Back in Credentials, create an **OAuth Client ID**:
   - Application type: **Desktop app** (for the initial auth flow)
   - Download the `credentials.json` file

### 0.4 Set Up Twilio
1. Sign up at https://www.twilio.com (free trial gives you $15 credit)
2. Get a Twilio phone number (this is the number that will send/receive SMS)
3. Note your **Account SID**, **Auth Token**, and **Twilio phone number**
4. In the Twilio console, you'll later configure a webhook URL for incoming SMS replies

### 0.5 Get an Anthropic API Key
1. Go to https://console.anthropic.com
2. Create an API key
3. Note the key (starts with `sk-ant-`)

---

## Phase 1: Project Structure & Core Setup

### 1.1 Project Structure
```
calendar-sync/
├── main.py                  # Cloud Function entry point
├── auth.py                  # Google OAuth helper (one-time token generation)
├── calendar_service.py      # Google Calendar read/write operations
├── ai_filter.py             # Claude API event filtering
├── sms_service.py           # Twilio SMS send/receive
├── config.py                # Configuration & environment variables
├── requirements.txt         # Python dependencies
├── deploy.sh                # Deployment script for Google Cloud
├── setup_auth.py            # One-time script to authorize both users
└── README.md                # Setup & deployment guide
```

### 1.2 Dependencies (`requirements.txt`)
```
google-auth==2.*
google-auth-oauthlib==1.*
google-api-python-client==2.*
anthropic==0.*
twilio==9.*
google-cloud-firestore==2.*
functions-framework==3.*
```

---

## Phase 2: Google Calendar Integration

### 2.1 One-Time Auth Flow (`setup_auth.py`)
- Run locally on your machine
- Opens a browser for OAuth consent — do this once for Alex, once for Sara
- Stores refresh tokens securely (in Google Cloud Secret Manager or Firestore)
- Each user gets their own token; the app uses these to access calendars on their behalf

### 2.2 Calendar Service (`calendar_service.py`)
Functions to build:
- `get_calendar_list(user)` — list all calendars for a user
- `get_recent_events(user, since_timestamp)` — fetch events created/modified since last check
- `create_notification_event(creator, event_summary, start_time, end_time, invitee_email)` — create a new event like "Alex at movie (Alamo Drafthouse)" and invite the other person

### 2.3 Calendar Selection
- On first run per user, fetch all calendars and store the list
- Default: monitor ALL calendars (we rely on AI filtering to skip irrelevant ones)
- Future enhancement: let users pick which calendars to monitor

---

## Phase 3: AI Event Filtering

### 3.1 Filter Logic (`ai_filter.py`)
- Takes an event (title, description, calendar name, time, duration)
- Sends to Claude API with a prompt like:

```
You are helping a couple stay informed about each other's schedules.
Given this calendar event, determine if the other person likely needs to know about it.

Event: {title}
Calendar: {calendar_name}
Time: {start} - {end}
Description: {description}

SHARE if: social plans, appointments, travel, commitments that affect availability,
activities outside the home, events involving other people.

SKIP if: work meetings, focus blocks, personal reminders, recurring habits,
trivial calendar holds, birthdays/holidays already on shared calendars.

Respond with JSON: {"should_prompt": true/false, "reason": "brief explanation",
"suggested_summary": "Alex at [activity] ([location if relevant])"}
```

- Returns whether to prompt + a suggested notification event title

### 3.2 Cost Estimate
- Using Claude Haiku for filtering: ~$0.001 per event evaluation
- At ~10-20 new events/day combined: less than $1/month

---

## Phase 4: SMS Notification System

### 4.1 Outbound SMS (`sms_service.py`)
When AI says "should_prompt = true":
- Send SMS to the event creator:
  ```
  New event: "Movie at Alamo Drafthouse"
  Wed Mar 18, 6:00 PM

  Notify Sara? Reply Y or N
  ```
- Store pending prompt in Firestore with event details and a unique ID

### 4.2 Inbound SMS Handler (separate Cloud Function)
- Twilio sends a webhook POST when the user replies
- Parse reply (Y/N/Yes/No)
- If Y: call `create_notification_event()` to create the shared event
- If N: mark as dismissed in Firestore
- Reply back confirming: "Done! Created 'Alex at movie (Alamo Drafthouse)' on Sara's calendar." or "Got it, skipped."

---

## Phase 5: Event Processing Pipeline (`main.py`)

### 5.1 Main Flow (triggered by Cloud Scheduler)
```
1. For each user (Alex, Sara):
   a. Fetch events created/modified since last check
   b. Filter out already-processed event IDs (check Firestore)
   c. For each new event:
      i.   Run through AI filter
      ii.  If should_prompt → send SMS
      iii. Store event ID as "processed" in Firestore
   d. Update "last checked" timestamp
```

### 5.2 Firestore Collections
```
processed_events/{event_id}     — tracks which events we've already seen
pending_prompts/{prompt_id}     — SMS prompts waiting for Y/N reply
user_tokens/{user_id}           — OAuth refresh tokens (encrypted)
```

---

## Phase 6: Deployment

### 6.1 Deploy Check Function
```bash
gcloud functions deploy calendar-sync-check \
  --runtime python312 \
  --trigger-http \
  --entry-point check_new_events \
  --region us-central1 \
  --set-env-vars ANTHROPIC_API_KEY=...,TWILIO_SID=...,TWILIO_TOKEN=...,TWILIO_NUMBER=...
```

### 6.2 Deploy SMS Reply Handler
```bash
gcloud functions deploy calendar-sync-reply \
  --runtime python312 \
  --trigger-http \
  --entry-point handle_sms_reply \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ...
```
(This URL gets configured as Twilio's incoming message webhook)

### 6.3 Set Up Cloud Scheduler
```bash
gcloud scheduler jobs create http calendar-sync-job \
  --schedule "0 * * * *" \
  --uri https://REGION-PROJECT.cloudfunctions.net/calendar-sync-check \
  --http-method POST
```
(Checks for new events every hour, on the hour)

---

## Phase 7: Testing & Iteration

### 7.1 Local Testing
- Run the check function locally with `functions-framework`
- Use a test calendar with sample events
- Verify AI filtering makes sensible decisions
- Test SMS send/receive with your phone

### 7.2 Smoke Test Checklist
- [ ] OAuth flow works for both users
- [ ] App reads events from all selected calendars
- [ ] AI correctly identifies share-worthy events
- [ ] SMS is sent to the right person
- [ ] Reply Y creates the notification event with correct title/time
- [ ] Reply N dismisses without action
- [ ] Duplicate events are not re-prompted

---

## Estimated Monthly Cost (Running)
| Service | Cost |
|---|---|
| Google Cloud Functions | Free (well within free tier) |
| Cloud Scheduler | Free (1 job free) |
| Firestore | Free (well within free tier) |
| Twilio SMS | ~$1-3/mo (phone number + messages) |
| Anthropic API (Haiku) | ~$0.50-1/mo |
| **Total** | **~$2-4/month** |

---

## User Info (for implementation)
- **Alex's email**: (to be configured)
- **Sara's email**: annear.sara@gmail.com
- **Alex's phone**: (to be configured)
- **Sara's phone**: (to be configured)
