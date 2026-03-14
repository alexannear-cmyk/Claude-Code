#!/usr/bin/env bash
#
# Deploy Calendar Sync to Google Cloud.
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated
#   2. A .env file in this directory (see .env.example)
#   3. Both users authorized via setup_auth.py
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh

set -euo pipefail

# Load environment variables from .env file
if [ -f .env ]; then
    # Export all variables from .env (skip comments and blank lines)
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
else
    echo "Error: .env file not found. Copy .env.example to .env and fill in your values."
    exit 1
fi

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID in .env}"
REGION="${GCP_REGION:-us-central1}"

echo "Deploying to project: $PROJECT_ID, region: $REGION"

# Build the env vars string for Cloud Functions
ENV_VARS="ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"
ENV_VARS+=",TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}"
ENV_VARS+=",TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}"
ENV_VARS+=",TWILIO_PHONE_NUMBER=${TWILIO_PHONE_NUMBER}"
ENV_VARS+=",GCP_PROJECT_ID=${PROJECT_ID}"
ENV_VARS+=",ALEX_EMAIL=${ALEX_EMAIL}"
ENV_VARS+=",ALEX_PHONE=${ALEX_PHONE}"
ENV_VARS+=",SARA_EMAIL=${SARA_EMAIL}"
ENV_VARS+=",SARA_PHONE=${SARA_PHONE}"

echo ""
echo "=== Deploying check_new_events function ==="
gcloud functions deploy calendar-sync-check \
    --project "$PROJECT_ID" \
    --runtime python312 \
    --trigger-http \
    --entry-point check_new_events \
    --region "$REGION" \
    --memory 256MB \
    --timeout 120s \
    --set-env-vars "$ENV_VARS" \
    --no-allow-unauthenticated

CHECK_URL=$(gcloud functions describe calendar-sync-check \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --format='value(httpsTrigger.url)')

echo ""
echo "=== Deploying handle_sms_reply function ==="
gcloud functions deploy calendar-sync-reply \
    --project "$PROJECT_ID" \
    --runtime python312 \
    --trigger-http \
    --entry-point handle_sms_reply \
    --region "$REGION" \
    --memory 256MB \
    --timeout 30s \
    --set-env-vars "$ENV_VARS" \
    --allow-unauthenticated  # Twilio needs to reach this

REPLY_URL=$(gcloud functions describe calendar-sync-reply \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --format='value(httpsTrigger.url)')

echo ""
echo "=== Setting up Cloud Scheduler (hourly) ==="
# Delete existing job if it exists (ignore error if it doesn't)
gcloud scheduler jobs delete calendar-sync-job \
    --project "$PROJECT_ID" \
    --location "$REGION" \
    --quiet 2>/dev/null || true

gcloud scheduler jobs create http calendar-sync-job \
    --project "$PROJECT_ID" \
    --location "$REGION" \
    --schedule "0 * * * *" \
    --uri "$CHECK_URL" \
    --http-method POST \
    --oidc-service-account-email "${PROJECT_ID}@appspot.gserviceaccount.com"

echo ""
echo "=== Deployment complete! ==="
echo ""
echo "Check function URL:  $CHECK_URL"
echo "Reply function URL:  $REPLY_URL"
echo ""
echo "NEXT STEP: Configure the Reply URL as your Twilio webhook:"
echo "  1. Go to https://console.twilio.com/us1/develop/phone-numbers"
echo "  2. Click your phone number"
echo "  3. Under 'Messaging', set 'A message comes in' webhook to:"
echo "     $REPLY_URL"
echo "  4. Set HTTP method to POST"
echo "  5. Save"
