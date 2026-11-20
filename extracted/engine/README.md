# Nightshift

Nightshift copies new videos from your own Telegram channel into **one** cloud pool made of every Google Drive account and every MEGA account you list. Each video is stored **once**, on the account that currently has the most free space and can actually take the file. It runs on GitHub Actions. There is no server to keep on.

Every day at **02:30 Malaysia time** (18:30 UTC):

1. GitHub Actions starts the workflow.
2. Telethon opens your channel with a saved StringSession.
3. New messages are indexed. Photos, GIFs and ordinary files are ignored.
4. The ledger selects up to **5** videos that are not already stored, oldest first.
5. Each video is downloaded to the runner's temporary disk, then deleted after the attempt.
6. The pool probes every account. Dead logins are skipped. Unknown free space is not treated as unlimited.
7. The video goes to the account with the most room. If that account is full, the next one is tried. A rate limit is retried on the same account and is **not** treated as a full disk.
8. The ledger in `data/backup_db.json` is committed back to this private repository after each video.
9. The log is saved as a workflow artifact. The runner shuts down.

A video that fails stays `pending` and is tried again the next night. It is never marked successful unless a provider returned a file id, or the same file name was already sitting on that account from a run that died after the upload.

## What this will not do

- It will not upload the same video to every account.
- It will not keep a computer, VPS or worker running between nights.
- It will not bypass provider quotas. Full accounts are skipped. API rate limits are backed off.
- It will not store a file larger than the GitHub-hosted runner can hold (default ceiling **10 GB**, leaving room on the free runner's disk). Those rows are marked `needs_attention`, not success.
- It will not log you into Telegram every night. That happens once, on a computer, when you create the StringSession.

GitHub's free private plan includes 2,000 Actions minutes a month. A short night is fine. A night of multi-gigabyte uploads can spend a lot of that budget. Scheduled jobs can also start late when GitHub is busy.

## 1. Repository

Create a **private** GitHub repository. Copy the contents of this folder into the root, so this path exists:

```text
.github/workflows/backup.yml
```

Do not put the project in a subfolder or Actions will not see the workflow.

Leave `data/backup_db.json` in the repo. That file is the database. The workflow commits it. Do not protect the default branch in a way that blocks `github-actions[bot]` from pushing, or the ledger will not survive the runner being destroyed.

## 2. Telegram API

1. Open [my.telegram.org](https://my.telegram.org) and create an application.
2. Note the numeric **API ID** and the **API hash**.
3. Decide how the job should find the channel: `@yourchannel` or the numeric id (`-100...`).

The account that owns the session must be able to read that channel.

## 3. StringSession, once

On any computer, from this folder:

```bash
pip install -r requirements.txt
python scripts/generate_telegram_session.py
```

Telegram will text you a code. If the account has a cloud password, the script asks for it. The printed line is the StringSession.

You can delete the checkout afterwards. The daily job does not need this computer.

## 4. Google Drive accounts

Repeat this for every Google account that should be in the pool. There is no built-in limit of three.

1. In Google Cloud, create a project and enable the **Google Drive API**.
2. On the OAuth consent screen, choose **External**, add your own Gmail address as a test user, and stay in **Testing** until you decide otherwise.
3. Create an OAuth client of type **Desktop**.
4. Download the client JSON. Do not commit it.
5. Mint a refresh token:

```bash
python scripts/generate_gdrive_token.py --client-secrets ~/Downloads/client_secret.json
```

A browser opens. Sign in with **that** Google account and allow access. The script prints one JSON object. If Google returns no refresh token, revoke the app at [Google Account permissions](https://myaccount.google.com/permissions) and run it again.

`folder_id` is optional. Leave it empty to use My Drive's root, or paste the id from a folder URL (`https://drive.google.com/drive/folders/THIS_PART`).

**Testing-mode refresh tokens expire after 7 days.** When one expires, that account is skipped (the log says auth failed) and the video is tried on another account or left pending. Mint a new token for that account. Publishing the OAuth app to Production so tokens last longer can require Google's verification, because the Drive scope is sensitive. For a private one-person backup, re-minting the token is the straightforward path.

The scope is `https://www.googleapis.com/auth/drive`. It is broader than upload-only because the job has to read `storageQuota`. A missing quota is not treated as infinite space. Drive omits `limit` only for Workspace accounts that are actually unlimited, and that is the only case recorded as unlimited.

## 5. MEGA accounts

Add one object per account. Use a dedicated MEGA account if you can. `mega.py` talks to MEGA's unofficial API and cannot complete an interactive 2FA prompt, so the backup account should not have two-factor login turned on.

Free space is `total - used` from MEGA's storage counters. `get_quota()` in mega.py is not used: that call returns the plan size, not the space left. A transfer-quota failure (`EOVERQUOTA`) means that account cannot take the file tonight; the job tries the next account and does not mark the video successful.

Optional `max_file_bytes` lets you record a limit you already know (for example a plan that rejects very large files) without hard-coding it for every account.

## 6. Secrets

Repository → Settings → Secrets and variables → Actions. Create these. There is no `.env` file.

| Secret | What it is |
| --- | --- |
| `TELEGRAM_API_ID` | Integer from my.telegram.org |
| `TELEGRAM_API_HASH` | Hash from my.telegram.org |
| `TELEGRAM_STRING_SESSION` | Output of `generate_telegram_session.py` |
| `TELEGRAM_CHANNEL` | `@name` or `-100...` |
| `GDRIVE_ACCOUNTS_JSON` | A JSON **array**. `[]` if you have no Drive accounts |
| `MEGA_ACCOUNTS_JSON` | A JSON **array**. `[]` if you have no MEGA accounts |

Shapes (also in `accounts.example.json`):

```json
[
  {
    "name": "gdrive-1",
    "client_id": "...",
    "client_secret": "...",
    "refresh_token": "...",
    "folder_id": "",
    "max_file_bytes": null
  }
]
```

```json
[
  {
    "name": "mega-1",
    "email": "backup@example.com",
    "password": "...",
    "folder": "Nightshift",
    "max_file_bytes": null
  }
]
```

Names must be unique across both lists and match `[A-Za-z0-9._-]`, up to 40 characters. Add as many objects as you have accounts.

## 7. Schedule and a manual night

The workflow file already schedules **02:30 Asia/Kuala_Lumpur**. Malaysia does not observe daylight saving, so `30 18 * * *` stays correct year-round.

Actions → Nightshift → Run workflow.

- **dry_run** indexes the channel and writes the plan. It does not download or upload, and it does not mark anything successful.
- **daily_limit** can be lowered. Values above 5 become 5.
- **force_unlock** is only for a lock left by a job that was killed. Normal nights do not need it.

Push this repository to the default branch or the scheduled workflow will not exist yet. The first push of the workflow file is what arms the cron.

## 8. Ledger

`data/backup_db.json` is committed by the job after each video, using the workflow's `GITHUB_TOKEN`. A runner that dies mid-upload leaves the video `pending` (or finds the already-uploaded object by its `{message_id}_{filename}` name on the next night and records it without uploading a second copy).

Rows:

| Field | Meaning |
| --- | --- |
| `channel_id`, `message_id` | Identity. The same pair is never stored twice |
| `filename`, `remote_filename`, `file_size` | What was seen, and the object name in the cloud |
| `status` | `discovered`, `pending`, `success`, or `needs_attention` |
| `provider`, `account`, `destination_file_id`, `upload_date` | Set only on success |
| `attempts`, `last_error`, `error_class`, `history` | What went wrong. `error_class` is `storage`, `transient`, `auth`, `permanent`, or `unknown` |

`success` and `needs_attention` are not selected again. `pending` is. `needs_attention` means a human has to look: the file is bigger than the runner, or the Telegram message is gone. That is not a successful backup.

Overlapping runs are blocked two ways: the workflow `concurrency` group, and a lock inside the ledger (6 hours, or until the run finishes). A second local process also takes an OS lock on `data/backup_db.json.lock`.

## 9. Checks before you trust it

```bash
pip install pytest
pytest
```

The tests do not call Telegram, Drive or MEGA. They cover:

- photos and other non-videos are ignored
- the daily cap is 5 even if a higher number is configured
- older message ids go first
- a successful row is not downloaded again
- a storage-full response switches accounts
- a rate limit is retried on the same account and does not zero its free space
- a failed upload stays `pending` and can succeed on the next run
- a file already present at the destination is recorded, not uploaded again
- a second process holding the ledger lock does not start another run

Then, with secrets in place, run the workflow once with **dry_run** on. Read the log artifact. You should see `videos_selected` and `dry_run_plan`, and the ledger should gain `discovered` rows but no `success` rows. Run it again with dry_run off. Confirm one cloud account received the file and the ledger names that account.

## 10. When it needs you

| Log | What to do |
| --- | --- |
| `configuration error` / exit 2 | A secret is missing or the JSON is not an array |
| Telegram auth / exit 2 | Session expired or the API hash is wrong. Generate a new StringSession |
| Telegram connection / exit 3 | Network or a long flood-wait. The next night tries again |
| `error_class: auth` on one account | Re-mint that Drive token, or fix that MEGA password. Other accounts are still used |
| `error_class: storage` | That account could not take the file. If every account says so, free some space |
| `error_class: transient` | Rate limit or network. The video stays pending |
| `runner_disk` | File is over `MAX_RUNNER_FILE_BYTES` (default 10 GiB). It will not fit a free GitHub runner |
| exit 4 | The upload may have worked but the ledger push failed. The next run looks for the remote file name before uploading again |
| exit 1 | Nothing selected was stored. Read `video_not_stored` in the artifact |

Exit 0 with a mix of success and pending is a finished night. The pending rows are first in line tomorrow.

Optional environment variables (the workflow already sets the ones that matter):

| Variable | Default |
| --- | --- |
| `DAILY_LIMIT` | 5, and never above 5 |
| `HISTORY_SCAN_LIMIT` | 2000 messages per night, ceiling 10000 |
| `MAX_RUNNER_FILE_BYTES` | 10737418240 |
| `STORAGE_MARGIN_BYTES` | 1048576 extra bytes required on top of the file size |
| `RETRY_ATTEMPTS` | 4, with backoff at 2s, 4s, 8s, capped at 60s |
| `LOCK_TTL_HOURS` | 6 |

## Security

- Secrets live in GitHub Secrets. The ledger stores account **names** and file ids, not tokens or passwords.
- Logs redact field names that look like tokens, secrets, passwords or sessions.
- The backup workflow does not run on `pull_request`, so a fork cannot read secrets.
- Keep the repository private.
- Drive access is a full Drive scope on purpose (quota + upload). MEGA passwords sit in one secret. Prefer dedicated backup accounts.
- Review the workflow diff if you ever change it. It has `contents: write` only so it can commit the ledger.

## Layout

```text
.github/workflows/backup.yml    daily job and manual run
.github/workflows/tests.yml     unit tests on push
backup/                         the program (python -m backup)
scripts/generate_telegram_session.py
scripts/generate_gdrive_token.py
data/backup_db.json             the ledger
tests/                          no network
```
