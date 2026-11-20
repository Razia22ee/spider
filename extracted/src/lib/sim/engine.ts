/** A faithful model of backup/records.py and backup/pool.py for the operator console.
 *  The Python tests are the source of truth. This does not call Telegram or any cloud.
 */

export type Fault = "none" | "storage" | "rate";
export type Provider = "gdrive" | "mega";

export type SimInput = {
  archiveFault: Fault;
  travelSignedIn: boolean;
  primaryFreeGb: number;
};

export type AccountView = {
  id: string;
  name: string;
  provider: Provider;
  freeGb: number;
  authOk: boolean;
  available: boolean;
  note: string;
};

export type RowStatus =
  | "stored"
  | "ignored"
  | "queued"
  | "uploading"
  | "retry"
  | "switching"
  | "pending"
  | "waiting";

export type RowView = {
  messageId: number;
  filename: string;
  gb: number;
  kind: "video" | "photo" | "file";
  status: RowStatus;
  account: string | null;
  note: string;
};

export type Frame = {
  kicker: string;
  title: string;
  detail: string;
  log: string;
  focusId: number | null;
  accountFocus: string | null;
  accounts: AccountView[];
  rows: RowView[];
};

type Video = {
  messageId: number;
  filename: string;
  gb: number;
  kind: "video" | "photo" | "file";
  initial: "stored" | "pending" | "new";
};

type Acc = {
  id: string;
  name: string;
  provider: Provider;
  freeGb: number;
  authOk: boolean;
  available: boolean;
  fault: Fault;
  rateLeft: number;
  note: string;
};

const VIDEOS: Video[] = [
  { messageId: 1001, filename: "lecture-01.mp4", gb: 1.2, kind: "video", initial: "stored" },
  { messageId: 1008, filename: "board.jpg", gb: 0.004, kind: "photo", initial: "new" },
  { messageId: 1014, filename: "lecture-02.mp4", gb: 0.8, kind: "video", initial: "pending" },
  { messageId: 1102, filename: "notes.pdf", gb: 0.02, kind: "file", initial: "new" },
  { messageId: 1105, filename: "lecture-03.mp4", gb: 2.4, kind: "video", initial: "new" },
  { messageId: 1200, filename: "lecture-04.mp4", gb: 0.6, kind: "video", initial: "new" },
  { messageId: 1208, filename: "lecture-05.mp4", gb: 3.1, kind: "video", initial: "new" },
  { messageId: 1301, filename: "lecture-06.mp4", gb: 0.9, kind: "video", initial: "new" },
  { messageId: 1404, filename: "lecture-07.mp4", gb: 1.1, kind: "video", initial: "new" },
  { messageId: 1500, filename: "lecture-08.mp4", gb: 0.7, kind: "video", initial: "new" },
];

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

function sizeLabel(gb: number): string {
  if (gb < 0.05) return `${Math.round(gb * 1000)} MB`;
  return `${gb.toFixed(gb >= 10 ? 0 : 1)} GB`;
}

function cloneAccounts(input: SimInput): Acc[] {
  const primary = Math.max(0, input.primaryFreeGb);
  return [
    {
      id: "archive",
      name: "gdrive-archive",
      provider: "gdrive",
      freeGb: 20,
      authOk: true,
      available: true,
      fault: input.archiveFault,
      rateLeft: input.archiveFault === "rate" ? 1 : 0,
      note: "probed",
    },
    {
      id: "primary",
      name: "mega-primary",
      provider: "mega",
      freeGb: primary,
      authOk: true,
      available: true,
      fault: "none",
      rateLeft: 0,
      note: "probed",
    },
    {
      id: "home",
      name: "gdrive-home",
      provider: "gdrive",
      freeGb: 2,
      authOk: true,
      available: true,
      fault: "none",
      rateLeft: 0,
      note: "probed",
    },
    {
      id: "old",
      name: "mega-old",
      provider: "mega",
      freeGb: 0.3,
      authOk: true,
      available: true,
      fault: "none",
      rateLeft: 0,
      note: "probed",
    },
    {
      id: "travel",
      name: "mega-travel",
      provider: "mega",
      freeGb: 50,
      authOk: input.travelSignedIn,
      available: input.travelSignedIn,
      fault: "none",
      rateLeft: 0,
      note: input.travelSignedIn ? "probed" : "session expired",
    },
  ];
}

function viewAccounts(accounts: Acc[]): AccountView[] {
  return accounts.map((account) => ({
    id: account.id,
    name: account.name,
    provider: account.provider,
    freeGb: round1(account.freeGb),
    authOk: account.authOk,
    available: account.available,
    note: account.note,
  }));
}

function baseRows(): RowView[] {
  return VIDEOS.map((video) => {
    if (video.kind !== "video") {
      return {
        messageId: video.messageId,
        filename: video.filename,
        gb: video.gb,
        kind: video.kind,
        status: "ignored",
        account: null,
        note: video.kind === "photo" ? "photo, skipped" : "not a video, skipped",
      };
    }
    if (video.initial === "stored") {
      return {
        messageId: video.messageId,
        filename: video.filename,
        gb: video.gb,
        kind: "video",
        status: "stored",
        account: "gdrive-home",
        note: "already stored, will not download again",
      };
    }
    return {
      messageId: video.messageId,
      filename: video.filename,
      gb: video.gb,
      kind: "video",
      status: "queued",
      account: null,
      note: video.initial === "pending" ? "failed last night, still first in line" : "new",
    };
  });
}

function rank(accounts: Acc[], gb: number): Acc[] {
  return accounts
    .filter((account) => account.available && account.authOk && account.freeGb >= gb)
    .sort((a, b) => b.freeGb - a.freeGb || a.name.localeCompare(b.name));
}

function providerLabel(provider: Provider): string {
  return provider === "gdrive" ? "Google Drive" : "MEGA";
}

export function simulate(input: SimInput): Frame[] {
  const accounts = cloneAccounts(input);
  const rows = baseRows();
  const frames: Frame[] = [];
  const push = (frame: Omit<Frame, "accounts" | "rows">) => {
    frames.push({
      ...frame,
      accounts: viewAccounts(accounts),
      rows: rows.map((row) => ({ ...row })),
    });
  };

  push({
    kicker: "Before 02:30",
    title: "The channel has a backlog. Nothing has been touched tonight.",
    detail: "Stored videos stay put. Photos and files are noise. Pending videos outrank brand-new ones because they are older.",
    log: "ledger opened · 1 already stored · 7 videos not yet stored · 2 messages ignored",
    focusId: null,
    accountFocus: null,
  });

  push({
    kicker: "Connect",
    title: "Signed in with the saved Telegram session.",
    detail: "The runner does not ask for a login code. If this session were rejected, the night would stop and the ledger would not invent successes.",
    log: "telegram_connected channel=@studio",
    focusId: null,
    accountFocus: null,
  });

  const eligible = rows.filter((row) => row.kind === "video" && row.status !== "stored");
  eligible.sort((a, b) => a.messageId - b.messageId);
  const chosen = eligible.slice(0, 5);
  const waiting = eligible.slice(5);
  for (const row of waiting) {
    row.status = "waiting";
    row.note = "over the nightly cap of 5";
  }
  for (const row of chosen) {
    row.status = "queued";
  }

  push({
    kicker: "Select",
    title: `Five oldest unstored videos. ${waiting.length} stay for another night.`,
    detail: "The cap is hard. Asking the workflow for more than 5 does not raise it. Message 1001 is already stored, so it is not one of the five.",
    log: `videos_selected count=5 ids=${chosen.map((row) => row.messageId).join(",")}`,
    focusId: chosen[0]?.messageId ?? null,
    accountFocus: null,
  });

  const skippedAuth = accounts.filter((account) => !account.authOk).map((account) => account.name);
  push({
    kicker: "Probe",
    title: "Every account is one pool. Free space decides, not the provider name.",
    detail: skippedAuth.length
      ? `${skippedAuth.join(", ")} failed auth and is out for tonight. The others are ranked by free bytes. Unknown space would not be treated as infinite.`
      : "Every configured account answered. They are ranked by free bytes. A rate limit later will not be recorded as a full disk.",
    log: `account_probed ${accounts
      .map((account) => `${account.name}:${account.authOk ? `${account.freeGb}GB` : "auth"}`)
      .join(" ")}`,
    focusId: null,
    accountFocus: skippedAuth.length ? "travel" : "archive",
  });

  let stored = 0;
  let pending = 0;

  for (const row of chosen) {
    const order = rank(accounts, row.gb);
    if (!order.length) {
      row.status = "pending";
      row.note = `no account has ${sizeLabel(row.gb)} free`;
      row.account = null;
      pending += 1;
      push({
        kicker: "Pending",
        title: `${row.filename} does not fit anywhere tonight.`,
        detail: "It stays pending. It is not marked stored. Tomorrow it is still ahead of anything newer.",
        log: `video_not_stored message=${row.messageId} error_class=storage`,
        focusId: row.messageId,
        accountFocus: null,
      });
      continue;
    }

    let placed = false;
    const tried: string[] = [];
    for (const account of order) {
      tried.push(account.name);
      row.status = "uploading";
      row.account = account.name;
      row.note = `trying ${account.name}, ${sizeLabel(account.freeGb)} free`;
      push({
        kicker: "Upload",
        title: `${row.filename} → ${account.name}.`,
        detail: `${providerLabel(account.provider)} has the most room that can hold ${sizeLabel(row.gb)}. One account only.`,
        log: `upload_attempt message=${row.messageId} account=${account.name}`,
        focusId: row.messageId,
        accountFocus: account.id,
      });

      if (account.fault === "rate" && account.rateLeft > 0) {
        account.rateLeft -= 1;
        row.status = "retry";
        row.note = "rate limit, same account, not a full disk";
        push({
          kicker: "Retry",
          title: `${account.name} hit a rate limit. Backing off, not switching.`,
          detail: "userRateLimitExceeded and MEGA EAGAIN are temporary. Free space stays as probed. The next try is the same account.",
          log: `retry message=${row.messageId} account=${account.name} error_class=transient delay=2s`,
          focusId: row.messageId,
          accountFocus: account.id,
        });
      }

      if (account.fault === "storage" && account.available) {
        account.available = false;
        account.freeGb = 0;
        account.note = "storage quota exceeded";
        row.status = "switching";
        row.note = `${account.name} is full. Next account.`;
        push({
          kicker: "Switch",
          title: `${account.name} refused the file. Quota, not a network blip.`,
          detail: "The account is dropped for the rest of the night. The video is still unstored, so the pool offers it to the next account with room.",
          log: `switch message=${row.messageId} from=${account.name} error_class=storage`,
          focusId: row.messageId,
          accountFocus: account.id,
        });
        continue;
      }

      account.freeGb = round1(account.freeGb - row.gb);
      account.note = "accepted a video";
      row.status = "stored";
      row.account = account.name;
      row.note = `one copy on ${account.name}`;
      stored += 1;
      placed = true;
      push({
        kicker: "Stored",
        title: `${row.filename} is on ${account.name} only.`,
        detail: `${providerLabel(account.provider)} returned a file id. The ledger will name this account. The same message will not be downloaded tomorrow.`,
        log: `video_stored message=${row.messageId} account=${account.name} provider=${account.provider}`,
        focusId: row.messageId,
        accountFocus: account.id,
      });
      break;
    }

    if (!placed) {
      row.status = "pending";
      row.account = null;
      row.note = `tried ${tried.join(" → ")}`;
      pending += 1;
      push({
        kicker: "Pending",
        title: `${row.filename} is still unstored.`,
        detail: "Every account that could have taken it refused, or none had the bytes. Status stays pending.",
        log: `video_not_stored message=${row.messageId} error_class=storage`,
        focusId: row.messageId,
        accountFocus: null,
      });
    }
  }

  push({
    kicker: "Done",
    title:
      pending === 0
        ? `${stored} stored. The runner deletes the temp files and pushes the ledger.`
        : `${stored} stored, ${pending} still pending. Nothing failed was marked stored.`,
    detail:
      "Tomorrow's run reads this ledger from the repository. Stored rows are skipped. Pending rows are still the oldest work.",
    log: `run_finished succeeded=${stored} pending=${pending} exit=${pending && stored === 0 ? 1 : 0}`,
    focusId: null,
    accountFocus: null,
  });

  return frames;
}

export function formatGb(gb: number): string {
  if (gb <= 0.0001) return "0 GB";
  if (gb < 0.05) return `${Math.max(1, Math.round(gb * 1000))} MB`;
  const digits = gb >= 10 ? 0 : 1;
  return `${gb.toFixed(digits)} GB`;
}

export const SAMPLE_COUNT = VIDEOS.length;
