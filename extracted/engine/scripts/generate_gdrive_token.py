#!/usr/bin/env python3
"""One-time Google Drive login for a single account.

Run once per Google account. The refresh token goes into GDRIVE_ACCOUNTS_JSON.
Revoke the app at https://myaccount.google.com/permissions and run again if
Google does not return a refresh token.

Scope is https://www.googleapis.com/auth/drive so the job can read storage
quota and upload into a folder you choose. Keep the repository private.
"""

from __future__ import annotations

import argparse

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Mint a Drive refresh token for one account.")
    parser.add_argument("--client-secrets", required=True, help="Desktop OAuth client JSON from Google Cloud")
    args = parser.parse_args()
    flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not creds.refresh_token:
        raise SystemExit(
            "Google did not return a refresh token. Remove Nightshift's access at "
            "https://myaccount.google.com/permissions and run this again."
        )
    print("\nAdd this object to the GDRIVE_ACCOUNTS_JSON array:\n")
    print("{")
    print('  "name": "gdrive-1",')
    print(f'  "client_id": "{creds.client_id}",')
    print(f'  "client_secret": "{creds.client_secret}",')
    print(f'  "refresh_token": "{creds.refresh_token}",')
    print('  "folder_id": "",')
    print('  "max_file_bytes": null')
    print("}")
    print("\nfolder_id is optional. Empty means the root of My Drive.")
    print("Delete the downloaded client secret file when you are done. Do not commit it.")


if __name__ == "__main__":
    main()
