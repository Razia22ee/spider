import { useEffect, useMemo, useState } from "react";
import { Download, Play, RotateCcw, SkipForward } from "lucide-react";
import { formatGb, simulate, type Fault, type Frame, type RowStatus } from "@/lib/sim/engine";
import { Setup } from "@/components/nightshift/setup";

type Tab = "tonight" | "pool" | "ledger" | "setup";

const TABS: { id: Tab; label: string }[] = [
  { id: "tonight", label: "Tonight" },
  { id: "pool", label: "Pool" },
  { id: "ledger", label: "Ledger" },
  { id: "setup", label: "Setup" },
];

const STATUS_LABEL: Record<RowStatus, string> = {
  stored: "Stored",
  ignored: "Ignored",
  queued: "Queued",
  uploading: "Uploading",
  retry: "Retrying",
  switching: "Switching",
  pending: "Pending",
  waiting: "Tomorrow",
};

function statusClass(status: RowStatus): string {
  if (status === "stored") return "bg-sage text-sage-ink";
  if (status === "pending" || status === "switching") return "bg-clay text-clay-ink";
  if (status === "retry" || status === "uploading") return "bg-copper text-copper-ink";
  if (status === "ignored") return "bg-surface-2 text-faint";
  return "bg-surface-2 text-muted";
}

export function Console() {
  const [tab, setTab] = useState<Tab>("tonight");
  const [fault, setFault] = useState<Fault>("storage");
  const [travelSignedIn, setTravelSignedIn] = useState(false);
  const [primaryFreeGb, setPrimaryFreeGb] = useState(5);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [reduced, setReduced] = useState(false);

  const frames = useMemo(
    () => simulate({ archiveFault: fault, travelSignedIn, primaryFreeGb }),
    [fault, travelSignedIn, primaryFreeGb],
  );
  const frame = frames[Math.min(index, frames.length - 1)] as Frame;

  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [fault, travelSignedIn, primaryFreeGb]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(media.matches);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    if (!playing || reduced) return;
    if (index >= frames.length - 1) return;
    const timer = window.setTimeout(() => setIndex((value) => Math.min(value + 1, frames.length - 1)), 700);
    return () => window.clearTimeout(timer);
  }, [playing, reduced, index, frames.length]);

  useEffect(() => {
    if (playing && index >= frames.length - 1) setPlaying(false);
  }, [playing, index, frames.length]);

  const scale = Math.max(50, ...frame.accounts.map((account) => account.freeGb), 1);

  return (
    <div className="min-h-screen bg-bg text-fg">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="font-mono text-xs tracking-wide text-copper">02:30 MYT · 18:30 UTC</p>
            <h1 className="mt-1 text-3xl font-medium tracking-tight text-balance">Nightshift</h1>
            <p className="mt-2 max-w-xl text-pretty text-sm leading-relaxed text-muted">
              Your Telegram channel, five videos a night, one copy each, into whichever Drive or MEGA account actually has the room.
            </p>
          </div>
          <a
            href="/nightshift-engine.zip"
            download
            className="inline-flex h-11 items-center justify-center gap-2 self-start rounded-md border border-line bg-surface px-4 text-sm"
          >
            <Download className="size-4 text-copper" />
            Download project
          </a>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-4 pb-3" aria-label="Sections">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={
                "h-11 shrink-0 rounded-md px-4 text-sm " +
                (tab === item.id ? "bg-copper text-copper-ink" : "text-muted")
              }
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        {tab === "setup" ? <Setup /> : null}
        {tab === "tonight" ? (
          <Tonight
            frame={frame}
            index={index}
            total={frames.length}
            playing={playing}
            fault={fault}
            travelSignedIn={travelSignedIn}
            primaryFreeGb={primaryFreeGb}
            scale={scale}
            onFault={setFault}
            onTravel={setTravelSignedIn}
            onPrimary={setPrimaryFreeGb}
            onPlay={() => {
              if (index >= frames.length - 1) setIndex(0);
              setPlaying(true);
            }}
            onStep={() => {
              setPlaying(false);
              setIndex((value) => Math.min(value + 1, frames.length - 1));
            }}
            onReset={() => {
              setPlaying(false);
              setIndex(0);
            }}
          />
        ) : null}
        {tab === "pool" ? <Pool frame={frame} scale={scale} /> : null}
        {tab === "ledger" ? <Ledger frame={frame} /> : null}
      </main>
    </div>
  );
}

function Tonight({
  frame,
  index,
  total,
  playing,
  fault,
  travelSignedIn,
  primaryFreeGb,
  scale,
  onFault,
  onTravel,
  onPrimary,
  onPlay,
  onStep,
  onReset,
}: {
  frame: Frame;
  index: number;
  total: number;
  playing: boolean;
  fault: Fault;
  travelSignedIn: boolean;
  primaryFreeGb: number;
  scale: number;
  onFault: (fault: Fault) => void;
  onTravel: (value: boolean) => void;
  onPrimary: (value: number) => void;
  onPlay: () => void;
  onStep: () => void;
  onReset: () => void;
}) {
  return (
    <div className="grid gap-5">
      <section className="rounded-md border border-line bg-surface p-5">
        <p className="font-mono text-xs text-copper">{frame.kicker}</p>
        <h2 className="mt-2 text-2xl font-medium text-balance">{frame.title}</h2>
        <p className="mt-3 max-w-3xl text-pretty text-sm leading-relaxed text-muted">{frame.detail}</p>
        <p className="mt-4 overflow-x-auto rounded-md bg-bg px-3 py-2 font-mono text-xs text-muted">{frame.log}</p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onPlay}
            className="inline-flex h-11 items-center gap-2 rounded-md bg-copper px-4 text-sm font-medium text-copper-ink"
          >
            <Play className="size-4" />
            {playing ? "Playing" : index === 0 ? "Run 02:30" : "Play"}
          </button>
          <button
            type="button"
            onClick={onStep}
            disabled={index >= total - 1}
            className="inline-flex h-11 items-center gap-2 rounded-md border border-line px-4 text-sm disabled:opacity-40"
          >
            <SkipForward className="size-4" />
            Step
          </button>
          <button
            type="button"
            onClick={onReset}
            className="inline-flex h-11 items-center gap-2 rounded-md border border-line px-4 text-sm"
          >
            <RotateCcw className="size-4" />
            Reset
          </button>
          <p className="font-mono text-xs text-faint tabular-nums">
            {index + 1} / {total}
          </p>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <section className="rounded-md border border-line bg-surface">
          <header className="flex items-center justify-between border-b border-line px-4 py-3">
            <h3 className="text-sm font-medium">Channel</h3>
            <p className="font-mono text-xs text-faint">sample, not live</p>
          </header>
          <ul>
            {frame.rows.map((row) => (
              <li
                key={row.messageId}
                className={
                  "grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b border-line px-4 py-3 last:border-b-0 " +
                  (frame.focusId === row.messageId ? "bg-surface-2" : "")
                }
              >
                <span className="font-mono text-xs text-faint tabular-nums">{row.messageId}</span>
                <span className="min-w-0">
                  <span className="block truncate text-sm">{row.filename}</span>
                  <span className="block truncate text-xs text-muted">
                    {formatGb(row.gb)}
                    {row.account ? ` · ${row.account}` : ""} · {row.note}
                  </span>
                </span>
                <span className={"rounded-md px-2 py-1 text-xs " + statusClass(row.status)}>{STATUS_LABEL[row.status]}</span>
              </li>
            ))}
          </ul>
        </section>

        <div className="grid gap-4">
          <section className="rounded-md border border-line bg-surface p-4">
            <h3 className="text-sm font-medium">Pool tonight</h3>
            <ul className="mt-3 grid gap-3">
              {frame.accounts.map((account) => (
                <li key={account.id}>
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <span className={account.id === frame.accountFocus ? "text-copper" : ""}>{account.name}</span>
                    <span className="font-mono text-xs text-muted tabular-nums">
                      {account.authOk ? formatGb(account.freeGb) : "auth"}
                    </span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-md bg-bg">
                    <div
                      className={"h-full " + (account.authOk && account.available ? "bg-copper" : "bg-line")}
                      style={{
                      width:
                        !account.authOk || account.freeGb <= 0
                          ? "0%"
                          : `${Math.min(100, (account.freeGb / scale) * 100)}%`,
                    }}
                    />
                  </div>
                  <p className="mt-1 text-xs text-faint">
                    {account.provider === "gdrive" ? "Google Drive" : "MEGA"} · {account.note}
                  </p>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-md border border-line bg-surface p-4">
            <h3 className="text-sm font-medium">Change the night</h3>
            <label className="mt-3 block text-xs text-muted" htmlFor="fault">
              gdrive-archive on the first upload
            </label>
            <select
              id="fault"
              value={fault}
              onChange={(event) => onFault(event.target.value as Fault)}
              className="mt-1 h-11 w-full rounded-md border border-line bg-bg px-3 text-sm"
            >
              <option value="storage">Reports storage full</option>
              <option value="rate">Rate limit, then accepts</option>
              <option value="none">Healthy</option>
            </select>
            <label className="mt-3 block text-xs text-muted" htmlFor="primary">
              mega-primary free space, {primaryFreeGb} GB
            </label>
            <input
              id="primary"
              type="range"
              min={0}
              max={40}
              step={1}
              value={primaryFreeGb}
              onChange={(event) => onPrimary(Number(event.target.value))}
              className="mt-2 w-full accent-copper"
            />
            <label className="mt-3 flex min-h-11 items-center justify-between gap-3 text-sm">
              <span>mega-travel signed in (50 GB)</span>
              <input
                type="checkbox"
                checked={travelSignedIn}
                onChange={(event) => onTravel(event.target.checked)}
                className="size-5 accent-copper"
              />
            </label>
            <p className="text-xs leading-relaxed text-faint">
              Leave travel signed out and primary under 20 GB to watch a full Drive account hand the file to MEGA.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

function Pool({ frame, scale }: { frame: Frame; scale: number }) {
  return (
    <div className="grid gap-4">
      <section className="rounded-md border border-line bg-surface p-5">
        <h2 className="text-2xl font-medium text-balance">One pool, one copy</h2>
        <p className="mt-3 max-w-3xl text-pretty text-sm leading-relaxed text-muted">
          Drive and MEGA are not two backups. A video lands on exactly one account: the one with the most free space that can accept the file. If that upload comes back storage-full, the next account is tried. If it comes back rate-limited, the same account is retried with backoff. Auth failures are skipped. Space the API did not report is not treated as unlimited.
        </p>
      </section>
      <ul className="grid gap-3 sm:grid-cols-2">
        {frame.accounts.map((account) => (
          <li key={account.id} className="rounded-md border border-line bg-surface p-4">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-sm font-medium">{account.name}</h3>
              <span className="font-mono text-xs text-muted">{account.provider === "gdrive" ? "Drive" : "MEGA"}</span>
            </div>
            <p className="mt-2 font-mono text-lg tabular-nums">{account.authOk ? formatGb(account.freeGb) : "Signed out"}</p>
            <div className="mt-3 h-2 overflow-hidden rounded-md bg-bg">
              <div
                className={"h-full " + (account.available && account.authOk ? "bg-copper" : "bg-line")}
                style={{ width: `${account.authOk ? Math.max(2, (account.freeGb / scale) * 100) : 0}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-muted">{account.note}</p>
          </li>
        ))}
      </ul>
      <section className="rounded-md border border-line bg-surface p-5 text-sm leading-relaxed text-muted">
        <p>
          Run the night on the Tonight tab, then come back. The bars move only after a real acceptance. A storage refusal zeros that account for the rest of the sample night. A rate limit does not.
        </p>
      </section>
    </div>
  );
}

const FIELDS: { name: string; meaning: string }[] = [
  { name: "channel_id + message_id", meaning: "Identity. A successful pair is never uploaded again." },
  { name: "filename / remote_filename", meaning: "The Telegram name, and the cloud object name with the message id in front." },
  { name: "file_size", meaning: "Bytes. Used for ranking and for the runner disk check." },
  { name: "status", meaning: "discovered, pending, success, or needs_attention." },
  { name: "provider + account", meaning: "Where the one copy went. Empty unless status is success." },
  { name: "destination_file_id", meaning: "Drive file id or MEGA node handle." },
  { name: "error_class", meaning: "storage, transient, auth, permanent, unknown, or runner_disk. Rate limits stay transient." },
];

function Ledger({ frame }: { frame: Frame }) {
  const counts = frame.rows.reduce<Record<string, number>>((acc, row) => {
    acc[row.status] = (acc[row.status] || 0) + 1;
    return acc;
  }, {});
  return (
    <div className="grid gap-4">
      <section className="rounded-md border border-line bg-surface p-5">
        <h2 className="text-2xl font-medium text-balance">The file in the repository is the database</h2>
        <p className="mt-3 max-w-3xl text-pretty text-sm leading-relaxed text-muted">
          data/backup_db.json is committed after each video. The runner’s disk is wiped when the job ends. Success is written only with a destination file id.
        </p>
        <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(["stored", "pending", "waiting", "ignored"] as RowStatus[]).map((status) => (
            <div key={status} className="rounded-md bg-bg px-3 py-3">
              <dt className="text-xs text-faint">{STATUS_LABEL[status]}</dt>
              <dd className="mt-1 font-mono text-xl tabular-nums">{counts[status] || 0}</dd>
            </div>
          ))}
        </dl>
      </section>
      <div className="overflow-x-auto rounded-md border border-line bg-surface">
        <table className="w-full min-w-xl text-left text-sm">
          <thead className="border-b border-line text-xs text-faint">
            <tr>
              <th className="px-4 py-3 font-medium">Message</th>
              <th className="px-4 py-3 font-medium">File</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Account</th>
            </tr>
          </thead>
          <tbody>
            {frame.rows.map((row) => (
              <tr key={row.messageId} className="border-b border-line last:border-b-0">
                <td className="px-4 py-3 font-mono text-xs tabular-nums">{row.messageId}</td>
                <td className="px-4 py-3">
                  <span className="block">{row.filename}</span>
                  <span className="text-xs text-muted">{row.note}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={"rounded-md px-2 py-1 text-xs " + statusClass(row.status)}>{STATUS_LABEL[row.status]}</span>
                </td>
                <td className="px-4 py-3 text-muted">{row.account || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="grid gap-2">
        {FIELDS.map((field) => (
          <li key={field.name} className="grid gap-1 rounded-md border border-line bg-surface px-4 py-3 sm:grid-cols-[14rem_minmax(0,1fr)]">
            <span className="font-mono text-xs text-copper">{field.name}</span>
            <span className="text-sm text-muted">{field.meaning}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
