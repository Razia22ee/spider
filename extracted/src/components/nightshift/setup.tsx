import { useState } from "react";
import { Check, ChevronDown, Download } from "lucide-react";

const SECRETS = `TELEGRAM_API_ID
TELEGRAM_API_HASH
TELEGRAM_STRING_SESSION
TELEGRAM_CHANNEL
GDRIVE_ACCOUNTS_JSON
MEGA_ACCOUNTS_JSON`;

const DRIVE_JSON = `[
  {
    "name": "gdrive-1",
    "client_id": "YOUR_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_CLIENT_SECRET",
    "refresh_token": "YOUR_REFRESH_TOKEN",
    "folder_id": "",
    "max_file_bytes": null
  }
]`;

const MEGA_JSON = `[
  {
    "name": "mega-1",
    "email": "backup@example.com",
    "password": "YOUR_MEGA_PASSWORD",
    "folder": "Nightshift",
    "max_file_bytes": null
  }
]`;

const CRON = "30 18 * * *";

const STEPS: { title: string; body: string; code?: string; codeLabel?: string }[] = [
  {
    title: "Private repository, files at the root",
    body: "Create a private GitHub repository and put this project at the top of it, so .github/workflows/backup.yml is not inside a subfolder. Leave data/backup_db.json in the repo. That file is the database. Do not require pull-request reviews on the default branch, or the Actions bot cannot commit the ledger. There is no server to rent.",
  },
  {
    title: "Telegram API id and hash",
    body: "At my.telegram.org, create an application. The API id is a number. The API hash is a string. The channel is @yourchannel or the numeric id starting with -100. The Telegram account you sign in with must be able to read that channel.",
  },
  {
    title: "StringSession, one time, on any computer",
    body: "Install the requirements and run python scripts/generate_telegram_session.py. Telegram sends a code. If the account has a cloud password, enter it. Copy the printed session into the TELEGRAM_STRING_SESSION secret, then close the terminal. After that, the daily job never needs that computer. Do not commit the session.",
    code: "pip install -r requirements.txt\npython scripts/generate_telegram_session.py",
    codeLabel: "Once, on a computer you control",
  },
  {
    title: "One Google refresh token per Drive account",
    body: "In Google Cloud, enable the Drive API. OAuth consent screen: External, Testing, and add your own Gmail as a test user. Create a Desktop OAuth client, download the JSON, and do not commit it. Run the token script once per Google account. Testing-mode refresh tokens die after 7 days. When one dies, that account is skipped and the video tries the next account. Mint a new token. Publishing the app so tokens last longer can require Google verification, because the Drive scope is sensitive. The scope is the full Drive scope on purpose: the job has to read storage quota, and it will not pretend missing quota is infinite space.",
    code: "python scripts/generate_gdrive_token.py --client-secrets client_secret.json",
    codeLabel: "Once per Google account",
  },
  {
    title: "MEGA accounts, as many as you have",
    body: "Add one object per account. There is no hard-coded limit of three. Prefer a dedicated MEGA account. The client cannot answer an interactive 2FA prompt, so that account should not use two-factor login. Free space is total minus used. A transfer-quota error means that account cannot take the file tonight; it is not recorded as success. Optional max_file_bytes records a limit you already know.",
  },
  {
    title: "Six secrets, nothing in the repo",
    body: "Repository settings, Secrets and variables, Actions. GDRIVE_ACCOUNTS_JSON and MEGA_ACCOUNTS_JSON are JSON arrays. Use [] for a provider you are not using yet. Names must be unique across both lists. Account names may contain letters, numbers, dots, underscores and hyphens.",
    code: SECRETS,
    codeLabel: "Secret names",
  },
  {
    title: "Arm the clock",
    body: "The workflow is already set for 02:30 Asia/Kuala_Lumpur, which is 18:30 UTC. Malaysia has no daylight saving, so the cron does not move. GitHub can start a scheduled job late. Push the workflow to the default branch or the schedule does not exist. Actions, Nightshift, Run workflow starts a night immediately. dry_run indexes and plans without uploading. daily_limit can be lowered, never raised past 5. force_unlock is only after a killed job left the ledger locked.",
    code: CRON,
    codeLabel: "UTC cron, already in the workflow",
  },
  {
    title: "First real night",
    body: "Run once with dry_run on. The log artifact should show videos_selected and dry_run_plan. The ledger gains discovered rows and no success rows. Run again with dry_run off. One account should hold the file. The ledger names that account and the file id. A second run must not download it again.",
  },
  {
    title: "What the ledger means",
    body: "success will not be selected again. pending will, oldest first. needs_attention means the file is bigger than the runner (default 10 GB) or the Telegram message is gone. That is not a successful backup. The job commits the ledger after each video. If the runner dies after an upload but before the commit, the next night looks for the same {message_id}_{filename} and records the existing file instead of uploading a second copy.",
  },
  {
    title: "When it will ask for you",
    body: "Exit 2: a secret or the Telegram session is wrong. Exit 3: Telegram could not be reached, or asked for a long flood-wait. Exit 1: nothing selected was stored. Exit 4: the cloud may have the file, but the ledger push failed. Exit 0 with some pending rows is a finished night; those rows are first tomorrow. A red auth line on one account does not stop the others.",
  },
];

function CopyBlock({ label, text }: { label: string; text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="mt-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="font-mono text-xs text-faint">{label}</p>
        <button
          type="button"
          className="inline-flex h-11 items-center gap-2 rounded-md bg-surface-2 px-3 text-sm text-fg"
          onClick={() => {
            void navigator.clipboard.writeText(text).then(() => {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1600);
            });
          }}
        >
          {copied ? <Check className="size-4 text-sage" /> : null}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto rounded-md bg-bg p-4 font-mono text-xs leading-relaxed text-fg">{text}</pre>
    </div>
  );
}

export function Setup() {
  return (
    <div className="grid gap-6">
      <div className="flex flex-col gap-4 rounded-md border border-line bg-surface p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl text-balance">The project archive</h2>
          <p className="mt-2 max-w-xl text-pretty text-sm leading-relaxed text-muted">
            This page does not connect to your Telegram or your cloud accounts. Download the archive, create a private repository, and put the files at the root.
          </p>
        </div>
        <a
          href="/nightshift-engine.zip"
          download
          className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-md bg-copper px-4 text-sm font-medium text-copper-ink"
        >
          <Download className="size-4" />
          Download project
        </a>
      </div>

      <ol className="overflow-hidden rounded-md border border-line bg-surface">
        {STEPS.map((step, index) => (
          <li key={step.title} className="border-b border-line last:border-b-0">
            <details className="group" open={index === 0}>
              <summary className="flex min-h-11 items-center gap-3 px-4 py-3">
                <span className="font-mono text-xs text-copper">{String(index + 1).padStart(2, "0")}</span>
                <span className="flex-1 text-sm font-medium text-balance">{step.title}</span>
                <ChevronDown className="ns-chev size-4 shrink-0 text-faint" />
              </summary>
              <div className="px-4 pb-4 pl-11">
                <p className="text-pretty text-sm leading-relaxed text-muted">{step.body}</p>
                {step.code ? <CopyBlock label={step.codeLabel || "Copy"} text={step.code} /> : null}
              </div>
            </details>
          </li>
        ))}
      </ol>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-line bg-surface p-4">
          <h3 className="text-sm font-medium">Google Drive secret</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted">The secret value is the array, not a wrapper object. Add another object for each extra account.</p>
          <CopyBlock label="GDRIVE_ACCOUNTS_JSON" text={DRIVE_JSON} />
        </div>
        <div className="rounded-md border border-line bg-surface p-4">
          <h3 className="text-sm font-medium">MEGA secret</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted">Folder Nightshift is created if it is missing. Password stays in the secret, never in the ledger.</p>
          <CopyBlock label="MEGA_ACCOUNTS_JSON" text={MEGA_JSON} />
        </div>
      </div>

      <div className="rounded-md border border-line bg-surface p-5">
        <h3 className="text-sm font-medium">Limits that are real</h3>
        <ul className="mt-3 grid gap-2 text-sm leading-relaxed text-muted">
          <li>Five videos a night. Older pending videos go before new ones.</li>
          <li>Free GitHub runners have about 14 GB of disk. Files over 10 GB are flagged, not uploaded, and not called successful.</li>
          <li>Private repos on the free plan include 2,000 Actions minutes a month. Huge files spend that quickly.</li>
          <li>A rate limit is retried with backoff. It does not mean the disk is full.</li>
          <li>A full account, or a MEGA transfer quota, sends the file to the next account that has room.</li>
          <li>If every account refuses, the video stays pending for the next night.</li>
        </ul>
      </div>
    </div>
  );
}
