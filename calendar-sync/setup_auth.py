"""One-time OAuth setup script.

Run this locally to authorize each user's Google Calendar access.
Usage:
    python setup_auth.py --user alex
    python setup_auth.py --user sara

This opens a browser for OAuth consent and stores the token locally.
"""

import argparse

from calendar_service import authorize_user
from config import USERS


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
