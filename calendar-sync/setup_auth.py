"""One-time OAuth setup script.

Run this locally to authorize each user's Google Calendar access.
Usage:
    python setup_auth.py --user alex
    python setup_auth.py --user sara

This opens a browser for OAuth consent and stores the refresh token
in Firestore for the Cloud Function to use.
"""

import argparse
import json

from google.cloud import firestore
from google_auth_oauthlib.flow import InstalledAppFlow

from config import GOOGLE_CREDENTIALS_FILE, GCP_PROJECT_ID, SCOPES, USERS


def authorize_user(user_id: str) -> None:
    if user_id not in USERS:
        print(f"Unknown user: {user_id}. Must be one of: {list(USERS.keys())}")
        return

    user = USERS[user_id]
    print(f"Authorizing {user_id} ({user['email']})...")
    print("A browser window will open. Sign in with the Google account above.")

    flow = InstalledAppFlow.from_client_secrets_file(
        GOOGLE_CREDENTIALS_FILE, SCOPES
    )
    credentials = flow.run_local_server(port=0)

    # Store the refresh token in Firestore
    db = firestore.Client(project=GCP_PROJECT_ID)
    doc_ref = db.collection("user_tokens").document(user_id)
    doc_ref.set({
        "refresh_token": credentials.refresh_token,
        "token": credentials.token,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "token_uri": credentials.token_uri,
        "email": user["email"],
    })

    print(f"Successfully authorized {user_id}! Token stored in Firestore.")


def main():
    parser = argparse.ArgumentParser(
        description="Authorize a user for Calendar Sync"
    )
    parser.add_argument(
        "--user",
        required=True,
        choices=list(USERS.keys()),
        help="Which user to authorize",
    )
    args = parser.parse_args()
    authorize_user(args.user)


if __name__ == "__main__":
    main()
