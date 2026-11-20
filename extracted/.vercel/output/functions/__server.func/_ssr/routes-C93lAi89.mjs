import { i as __toESM } from "../_runtime.mjs";
import { K as require_react, b as require_jsx_runtime } from "../_libs/@tanstack/react-router+[...].mjs";
import { a as Download, i as Play, n as SkipForward, o as ChevronDown, r as RotateCcw, s as Check } from "../_libs/lucide-react.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/routes-C93lAi89.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
var VIDEOS = [
	{
		messageId: 1001,
		filename: "lecture-01.mp4",
		gb: 1.2,
		kind: "video",
		initial: "stored"
	},
	{
		messageId: 1008,
		filename: "board.jpg",
		gb: .004,
		kind: "photo",
		initial: "new"
	},
	{
		messageId: 1014,
		filename: "lecture-02.mp4",
		gb: .8,
		kind: "video",
		initial: "pending"
	},
	{
		messageId: 1102,
		filename: "notes.pdf",
		gb: .02,
		kind: "file",
		initial: "new"
	},
	{
		messageId: 1105,
		filename: "lecture-03.mp4",
		gb: 2.4,
		kind: "video",
		initial: "new"
	},
	{
		messageId: 1200,
		filename: "lecture-04.mp4",
		gb: .6,
		kind: "video",
		initial: "new"
	},
	{
		messageId: 1208,
		filename: "lecture-05.mp4",
		gb: 3.1,
		kind: "video",
		initial: "new"
	},
	{
		messageId: 1301,
		filename: "lecture-06.mp4",
		gb: .9,
		kind: "video",
		initial: "new"
	},
	{
		messageId: 1404,
		filename: "lecture-07.mp4",
		gb: 1.1,
		kind: "video",
		initial: "new"
	},
	{
		messageId: 1500,
		filename: "lecture-08.mp4",
		gb: .7,
		kind: "video",
		initial: "new"
	}
];
function round1(value) {
	return Math.round(value * 10) / 10;
}
function sizeLabel(gb) {
	if (gb < .05) return `${Math.round(gb * 1e3)} MB`;
	return `${gb.toFixed(gb >= 10 ? 0 : 1)} GB`;
}
function cloneAccounts(input) {
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
			note: "probed"
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
			note: "probed"
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
			note: "probed"
		},
		{
			id: "old",
			name: "mega-old",
			provider: "mega",
			freeGb: .3,
			authOk: true,
			available: true,
			fault: "none",
			rateLeft: 0,
			note: "probed"
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
			note: input.travelSignedIn ? "probed" : "session expired"
		}
	];
}
function viewAccounts(accounts) {
	return accounts.map((account) => ({
		id: account.id,
		name: account.name,
		provider: account.provider,
		freeGb: round1(account.freeGb),
		authOk: account.authOk,
		available: account.available,
		note: account.note
	}));
}
function baseRows() {
	return VIDEOS.map((video) => {
		if (video.kind !== "video") return {
			messageId: video.messageId,
			filename: video.filename,
			gb: video.gb,
			kind: video.kind,
			status: "ignored",
			account: null,
			note: video.kind === "photo" ? "photo, skipped" : "not a video, skipped"
		};
		if (video.initial === "stored") return {
			messageId: video.messageId,
			filename: video.filename,
			gb: video.gb,
			kind: "video",
			status: "stored",
			account: "gdrive-home",
			note: "already stored, will not download again"
		};
		return {
			messageId: video.messageId,
			filename: video.filename,
			gb: video.gb,
			kind: "video",
			status: "queued",
			account: null,
			note: video.initial === "pending" ? "failed last night, still first in line" : "new"
		};
	});
}
function rank(accounts, gb) {
	return accounts.filter((account) => account.available && account.authOk && account.freeGb >= gb).sort((a, b) => b.freeGb - a.freeGb || a.name.localeCompare(b.name));
}
function providerLabel(provider) {
	return provider === "gdrive" ? "Google Drive" : "MEGA";
}
function simulate(input) {
	const accounts = cloneAccounts(input);
	const rows = baseRows();
	const frames = [];
	const push = (frame) => {
		frames.push({
			...frame,
			accounts: viewAccounts(accounts),
			rows: rows.map((row) => ({ ...row }))
		});
	};
	push({
		kicker: "Before 02:30",
		title: "The channel has a backlog. Nothing has been touched tonight.",
		detail: "Stored videos stay put. Photos and files are noise. Pending videos outrank brand-new ones because they are older.",
		log: "ledger opened · 1 already stored · 7 videos not yet stored · 2 messages ignored",
		focusId: null,
		accountFocus: null
	});
	push({
		kicker: "Connect",
		title: "Signed in with the saved Telegram session.",
		detail: "The runner does not ask for a login code. If this session were rejected, the night would stop and the ledger would not invent successes.",
		log: "telegram_connected channel=@studio",
		focusId: null,
		accountFocus: null
	});
	const eligible = rows.filter((row) => row.kind === "video" && row.status !== "stored");
	eligible.sort((a, b) => a.messageId - b.messageId);
	const chosen = eligible.slice(0, 5);
	const waiting = eligible.slice(5);
	for (const row of waiting) {
		row.status = "waiting";
		row.note = "over the nightly cap of 5";
	}
	for (const row of chosen) row.status = "queued";
	push({
		kicker: "Select",
		title: `Five oldest unstored videos. ${waiting.length} stay for another night.`,
		detail: "The cap is hard. Asking the workflow for more than 5 does not raise it. Message 1001 is already stored, so it is not one of the five.",
		log: `videos_selected count=5 ids=${chosen.map((row) => row.messageId).join(",")}`,
		focusId: chosen[0]?.messageId ?? null,
		accountFocus: null
	});
	const skippedAuth = accounts.filter((account) => !account.authOk).map((account) => account.name);
	push({
		kicker: "Probe",
		title: "Every account is one pool. Free space decides, not the provider name.",
		detail: skippedAuth.length ? `${skippedAuth.join(", ")} failed auth and is out for tonight. The others are ranked by free bytes. Unknown space would not be treated as infinite.` : "Every configured account answered. They are ranked by free bytes. A rate limit later will not be recorded as a full disk.",
		log: `account_probed ${accounts.map((account) => `${account.name}:${account.authOk ? `${account.freeGb}GB` : "auth"}`).join(" ")}`,
		focusId: null,
		accountFocus: skippedAuth.length ? "travel" : "archive"
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
				accountFocus: null
			});
			continue;
		}
		let placed = false;
		const tried = [];
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
				accountFocus: account.id
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
					accountFocus: account.id
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
					accountFocus: account.id
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
				accountFocus: account.id
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
				accountFocus: null
			});
		}
	}
	push({
		kicker: "Done",
		title: pending === 0 ? `${stored} stored. The runner deletes the temp files and pushes the ledger.` : `${stored} stored, ${pending} still pending. Nothing failed was marked stored.`,
		detail: "Tomorrow's run reads this ledger from the repository. Stored rows are skipped. Pending rows are still the oldest work.",
		log: `run_finished succeeded=${stored} pending=${pending} exit=${pending && stored === 0 ? 1 : 0}`,
		focusId: null,
		accountFocus: null
	});
	return frames;
}
function formatGb(gb) {
	if (gb <= 1e-4) return "0 GB";
	if (gb < .05) return `${Math.max(1, Math.round(gb * 1e3))} MB`;
	const digits = gb >= 10 ? 0 : 1;
	return `${gb.toFixed(digits)} GB`;
}
VIDEOS.length;
var SECRETS = `TELEGRAM_API_ID
TELEGRAM_API_HASH
TELEGRAM_STRING_SESSION
TELEGRAM_CHANNEL
GDRIVE_ACCOUNTS_JSON
MEGA_ACCOUNTS_JSON`;
var DRIVE_JSON = `[
  {
    "name": "gdrive-1",
    "client_id": "YOUR_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_CLIENT_SECRET",
    "refresh_token": "YOUR_REFRESH_TOKEN",
    "folder_id": "",
    "max_file_bytes": null
  }
]`;
var MEGA_JSON = `[
  {
    "name": "mega-1",
    "email": "backup@example.com",
    "password": "YOUR_MEGA_PASSWORD",
    "folder": "Nightshift",
    "max_file_bytes": null
  }
]`;
var STEPS = [
	{
		title: "Private repository, files at the root",
		body: "Create a private GitHub repository and put this project at the top of it, so .github/workflows/backup.yml is not inside a subfolder. Leave data/backup_db.json in the repo. That file is the database. Do not require pull-request reviews on the default branch, or the Actions bot cannot commit the ledger. There is no server to rent."
	},
	{
		title: "Telegram API id and hash",
		body: "At my.telegram.org, create an application. The API id is a number. The API hash is a string. The channel is @yourchannel or the numeric id starting with -100. The Telegram account you sign in with must be able to read that channel."
	},
	{
		title: "StringSession, one time, on any computer",
		body: "Install the requirements and run python scripts/generate_telegram_session.py. Telegram sends a code. If the account has a cloud password, enter it. Copy the printed session into the TELEGRAM_STRING_SESSION secret, then close the terminal. After that, the daily job never needs that computer. Do not commit the session.",
		code: "pip install -r requirements.txt\npython scripts/generate_telegram_session.py",
		codeLabel: "Once, on a computer you control"
	},
	{
		title: "One Google refresh token per Drive account",
		body: "In Google Cloud, enable the Drive API. OAuth consent screen: External, Testing, and add your own Gmail as a test user. Create a Desktop OAuth client, download the JSON, and do not commit it. Run the token script once per Google account. Testing-mode refresh tokens die after 7 days. When one dies, that account is skipped and the video tries the next account. Mint a new token. Publishing the app so tokens last longer can require Google verification, because the Drive scope is sensitive. The scope is the full Drive scope on purpose: the job has to read storage quota, and it will not pretend missing quota is infinite space.",
		code: "python scripts/generate_gdrive_token.py --client-secrets client_secret.json",
		codeLabel: "Once per Google account"
	},
	{
		title: "MEGA accounts, as many as you have",
		body: "Add one object per account. There is no hard-coded limit of three. Prefer a dedicated MEGA account. The client cannot answer an interactive 2FA prompt, so that account should not use two-factor login. Free space is total minus used. A transfer-quota error means that account cannot take the file tonight; it is not recorded as success. Optional max_file_bytes records a limit you already know."
	},
	{
		title: "Six secrets, nothing in the repo",
		body: "Repository settings, Secrets and variables, Actions. GDRIVE_ACCOUNTS_JSON and MEGA_ACCOUNTS_JSON are JSON arrays. Use [] for a provider you are not using yet. Names must be unique across both lists. Account names may contain letters, numbers, dots, underscores and hyphens.",
		code: SECRETS,
		codeLabel: "Secret names"
	},
	{
		title: "Arm the clock",
		body: "The workflow is already set for 02:30 Asia/Kuala_Lumpur, which is 18:30 UTC. Malaysia has no daylight saving, so the cron does not move. GitHub can start a scheduled job late. Push the workflow to the default branch or the schedule does not exist. Actions, Nightshift, Run workflow starts a night immediately. dry_run indexes and plans without uploading. daily_limit can be lowered, never raised past 5. force_unlock is only after a killed job left the ledger locked.",
		code: "30 18 * * *",
		codeLabel: "UTC cron, already in the workflow"
	},
	{
		title: "First real night",
		body: "Run once with dry_run on. The log artifact should show videos_selected and dry_run_plan. The ledger gains discovered rows and no success rows. Run again with dry_run off. One account should hold the file. The ledger names that account and the file id. A second run must not download it again."
	},
	{
		title: "What the ledger means",
		body: "success will not be selected again. pending will, oldest first. needs_attention means the file is bigger than the runner (default 10 GB) or the Telegram message is gone. That is not a successful backup. The job commits the ledger after each video. If the runner dies after an upload but before the commit, the next night looks for the same {message_id}_{filename} and records the existing file instead of uploading a second copy."
	},
	{
		title: "When it will ask for you",
		body: "Exit 2: a secret or the Telegram session is wrong. Exit 3: Telegram could not be reached, or asked for a long flood-wait. Exit 1: nothing selected was stored. Exit 4: the cloud may have the file, but the ledger push failed. Exit 0 with some pending rows is a finished night; those rows are first tomorrow. A red auth line on one account does not stop the others."
	}
];
function CopyBlock({ label, text }) {
	const [copied, setCopied] = (0, import_react.useState)(false);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mt-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mb-2 flex items-center justify-between gap-3",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "font-mono text-xs text-faint",
				children: label
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				type: "button",
				className: "inline-flex h-11 items-center gap-2 rounded-md bg-surface-2 px-3 text-sm text-fg",
				onClick: () => {
					navigator.clipboard.writeText(text).then(() => {
						setCopied(true);
						window.setTimeout(() => setCopied(false), 1600);
					});
				},
				children: [copied ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Check, { className: "size-4 text-sage" }) : null, copied ? "Copied" : "Copy"]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("pre", {
			className: "overflow-x-auto rounded-md bg-bg p-4 font-mono text-xs leading-relaxed text-fg",
			children: text
		})]
	});
}
function Setup() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-4 rounded-md border border-line bg-surface p-5 sm:flex-row sm:items-center sm:justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-xl text-balance",
					children: "The project archive"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-2 max-w-xl text-pretty text-sm leading-relaxed text-muted",
					children: "This page does not connect to your Telegram or your cloud accounts. Download the archive, create a private repository, and put the files at the root."
				})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
					href: "/nightshift-engine.zip",
					download: true,
					className: "inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-md bg-copper px-4 text-sm font-medium text-copper-ink",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Download, { className: "size-4" }), "Download project"]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ol", {
				className: "overflow-hidden rounded-md border border-line bg-surface",
				children: STEPS.map((step, index) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", {
					className: "border-b border-line last:border-b-0",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("details", {
						className: "group",
						open: index === 0,
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("summary", {
							className: "flex min-h-11 items-center gap-3 px-4 py-3",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-mono text-xs text-copper",
									children: String(index + 1).padStart(2, "0")
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "flex-1 text-sm font-medium text-balance",
									children: step.title
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChevronDown, { className: "ns-chev size-4 shrink-0 text-faint" })
							]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "px-4 pb-4 pl-11",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "text-pretty text-sm leading-relaxed text-muted",
								children: step.body
							}), step.code ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyBlock, {
								label: step.codeLabel || "Copy",
								text: step.code
							}) : null]
						})]
					})
				}, step.title))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-4 lg:grid-cols-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-md border border-line bg-surface p-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-sm font-medium",
							children: "Google Drive secret"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 text-sm leading-relaxed text-muted",
							children: "The secret value is the array, not a wrapper object. Add another object for each extra account."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyBlock, {
							label: "GDRIVE_ACCOUNTS_JSON",
							text: DRIVE_JSON
						})
					]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-md border border-line bg-surface p-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-sm font-medium",
							children: "MEGA secret"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 text-sm leading-relaxed text-muted",
							children: "Folder Nightshift is created if it is missing. Password stays in the secret, never in the ledger."
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CopyBlock, {
							label: "MEGA_ACCOUNTS_JSON",
							text: MEGA_JSON
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-md border border-line bg-surface p-5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
					className: "text-sm font-medium",
					children: "Limits that are real"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("ul", {
					className: "mt-3 grid gap-2 text-sm leading-relaxed text-muted",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "Five videos a night. Older pending videos go before new ones." }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "Free GitHub runners have about 14 GB of disk. Files over 10 GB are flagged, not uploaded, and not called successful." }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "Private repos on the free plan include 2,000 Actions minutes a month. Huge files spend that quickly." }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "A rate limit is retried with backoff. It does not mean the disk is full." }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "A full account, or a MEGA transfer quota, sends the file to the next account that has room." }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: "If every account refuses, the video stays pending for the next night." })
					]
				})]
			})
		]
	});
}
var TABS = [
	{
		id: "tonight",
		label: "Tonight"
	},
	{
		id: "pool",
		label: "Pool"
	},
	{
		id: "ledger",
		label: "Ledger"
	},
	{
		id: "setup",
		label: "Setup"
	}
];
var STATUS_LABEL = {
	stored: "Stored",
	ignored: "Ignored",
	queued: "Queued",
	uploading: "Uploading",
	retry: "Retrying",
	switching: "Switching",
	pending: "Pending",
	waiting: "Tomorrow"
};
function statusClass(status) {
	if (status === "stored") return "bg-sage text-sage-ink";
	if (status === "pending" || status === "switching") return "bg-clay text-clay-ink";
	if (status === "retry" || status === "uploading") return "bg-copper text-copper-ink";
	if (status === "ignored") return "bg-surface-2 text-faint";
	return "bg-surface-2 text-muted";
}
function Console() {
	const [tab, setTab] = (0, import_react.useState)("tonight");
	const [fault, setFault] = (0, import_react.useState)("storage");
	const [travelSignedIn, setTravelSignedIn] = (0, import_react.useState)(false);
	const [primaryFreeGb, setPrimaryFreeGb] = (0, import_react.useState)(5);
	const [index, setIndex] = (0, import_react.useState)(0);
	const [playing, setPlaying] = (0, import_react.useState)(false);
	const [reduced, setReduced] = (0, import_react.useState)(false);
	const frames = (0, import_react.useMemo)(() => simulate({
		archiveFault: fault,
		travelSignedIn,
		primaryFreeGb
	}), [
		fault,
		travelSignedIn,
		primaryFreeGb
	]);
	const frame = frames[Math.min(index, frames.length - 1)];
	(0, import_react.useEffect)(() => {
		setIndex(0);
		setPlaying(false);
	}, [
		fault,
		travelSignedIn,
		primaryFreeGb
	]);
	(0, import_react.useEffect)(() => {
		const media = window.matchMedia("(prefers-reduced-motion: reduce)");
		const apply = () => setReduced(media.matches);
		apply();
		media.addEventListener("change", apply);
		return () => media.removeEventListener("change", apply);
	}, []);
	(0, import_react.useEffect)(() => {
		if (!playing || reduced) return;
		if (index >= frames.length - 1) return;
		const timer = window.setTimeout(() => setIndex((value) => Math.min(value + 1, frames.length - 1)), 700);
		return () => window.clearTimeout(timer);
	}, [
		playing,
		reduced,
		index,
		frames.length
	]);
	(0, import_react.useEffect)(() => {
		if (playing && index >= frames.length - 1) setPlaying(false);
	}, [
		playing,
		index,
		frames.length
	]);
	const scale = Math.max(50, ...frame.accounts.map((account) => account.freeGb), 1);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "min-h-screen bg-bg text-fg",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
			className: "border-b border-line",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mx-auto flex max-w-5xl flex-col gap-4 px-4 py-5 sm:flex-row sm:items-end sm:justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "font-mono text-xs tracking-wide text-copper",
						children: "02:30 MYT · 18:30 UTC"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "mt-1 text-3xl font-medium tracking-tight text-balance",
						children: "Nightshift"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-2 max-w-xl text-pretty text-sm leading-relaxed text-muted",
						children: "Your Telegram channel, five videos a night, one copy each, into whichever Drive or MEGA account actually has the room."
					})
				] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("a", {
					href: "/nightshift-engine.zip",
					download: true,
					className: "inline-flex h-11 items-center justify-center gap-2 self-start rounded-md border border-line bg-surface px-4 text-sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Download, { className: "size-4 text-copper" }), "Download project"]
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
				className: "mx-auto flex max-w-5xl gap-1 overflow-x-auto px-4 pb-3",
				"aria-label": "Sections",
				children: TABS.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					type: "button",
					onClick: () => setTab(item.id),
					className: "h-11 shrink-0 rounded-md px-4 text-sm " + (tab === item.id ? "bg-copper text-copper-ink" : "text-muted"),
					children: item.label
				}, item.id))
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("main", {
			className: "mx-auto max-w-5xl px-4 py-6",
			children: [
				tab === "setup" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Setup, {}) : null,
				tab === "tonight" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tonight, {
					frame,
					index,
					total: frames.length,
					playing,
					fault,
					travelSignedIn,
					primaryFreeGb,
					scale,
					onFault: setFault,
					onTravel: setTravelSignedIn,
					onPrimary: setPrimaryFreeGb,
					onPlay: () => {
						if (index >= frames.length - 1) setIndex(0);
						setPlaying(true);
					},
					onStep: () => {
						setPlaying(false);
						setIndex((value) => Math.min(value + 1, frames.length - 1));
					},
					onReset: () => {
						setPlaying(false);
						setIndex(0);
					}
				}) : null,
				tab === "pool" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Pool, {
					frame,
					scale
				}) : null,
				tab === "ledger" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ledger, { frame }) : null
			]
		})]
	});
}
function Tonight({ frame, index, total, playing, fault, travelSignedIn, primaryFreeGb, scale, onFault, onTravel, onPrimary, onPlay, onStep, onReset }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
			className: "rounded-md border border-line bg-surface p-5",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "font-mono text-xs text-copper",
					children: frame.kicker
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "mt-2 text-2xl font-medium text-balance",
					children: frame.title
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-3 max-w-3xl text-pretty text-sm leading-relaxed text-muted",
					children: frame.detail
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-4 overflow-x-auto rounded-md bg-bg px-3 py-2 font-mono text-xs text-muted",
					children: frame.log
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-4 flex flex-wrap items-center gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							type: "button",
							onClick: onPlay,
							className: "inline-flex h-11 items-center gap-2 rounded-md bg-copper px-4 text-sm font-medium text-copper-ink",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Play, { className: "size-4" }), playing ? "Playing" : index === 0 ? "Run 02:30" : "Play"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							type: "button",
							onClick: onStep,
							disabled: index >= total - 1,
							className: "inline-flex h-11 items-center gap-2 rounded-md border border-line px-4 text-sm disabled:opacity-40",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SkipForward, { className: "size-4" }), "Step"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							type: "button",
							onClick: onReset,
							className: "inline-flex h-11 items-center gap-2 rounded-md border border-line px-4 text-sm",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RotateCcw, { className: "size-4" }), "Reset"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
							className: "font-mono text-xs text-faint tabular-nums",
							children: [
								index + 1,
								" / ",
								total
							]
						})
					]
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "rounded-md border border-line bg-surface",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
					className: "flex items-center justify-between border-b border-line px-4 py-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium",
						children: "Channel"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "font-mono text-xs text-faint",
						children: "sample, not live"
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", { children: frame.rows.map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
					className: "grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b border-line px-4 py-3 last:border-b-0 " + (frame.focusId === row.messageId ? "bg-surface-2" : ""),
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-mono text-xs text-faint tabular-nums",
							children: row.messageId
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "min-w-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "block truncate text-sm",
								children: row.filename
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "block truncate text-xs text-muted",
								children: [
									formatGb(row.gb),
									row.account ? ` · ${row.account}` : "",
									" · ",
									row.note
								]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "rounded-md px-2 py-1 text-xs " + statusClass(row.status),
							children: STATUS_LABEL[row.status]
						})
					]
				}, row.messageId)) })]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-4",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
					className: "rounded-md border border-line bg-surface p-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
						className: "text-sm font-medium",
						children: "Pool tonight"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
						className: "mt-3 grid gap-3",
						children: frame.accounts.map((account) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", { children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-baseline justify-between gap-3 text-sm",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: account.id === frame.accountFocus ? "text-copper" : "",
									children: account.name
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-mono text-xs text-muted tabular-nums",
									children: account.authOk ? formatGb(account.freeGb) : "auth"
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "mt-1 h-2 overflow-hidden rounded-md bg-bg",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
									className: "h-full " + (account.authOk && account.available ? "bg-copper" : "bg-line"),
									style: { width: !account.authOk || account.freeGb <= 0 ? "0%" : `${Math.min(100, account.freeGb / scale * 100)}%` }
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "mt-1 text-xs text-faint",
								children: [
									account.provider === "gdrive" ? "Google Drive" : "MEGA",
									" · ",
									account.note
								]
							})
						] }, account.id))
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
					className: "rounded-md border border-line bg-surface p-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
							className: "text-sm font-medium",
							children: "Change the night"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("label", {
							className: "mt-3 block text-xs text-muted",
							htmlFor: "fault",
							children: "gdrive-archive on the first upload"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
							id: "fault",
							value: fault,
							onChange: (event) => onFault(event.target.value),
							className: "mt-1 h-11 w-full rounded-md border border-line bg-bg px-3 text-sm",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "storage",
									children: "Reports storage full"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "rate",
									children: "Rate limit, then accepts"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
									value: "none",
									children: "Healthy"
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "mt-3 block text-xs text-muted",
							htmlFor: "primary",
							children: [
								"mega-primary free space, ",
								primaryFreeGb,
								" GB"
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							id: "primary",
							type: "range",
							min: 0,
							max: 40,
							step: 1,
							value: primaryFreeGb,
							onChange: (event) => onPrimary(Number(event.target.value)),
							className: "mt-2 w-full accent-copper"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("label", {
							className: "mt-3 flex min-h-11 items-center justify-between gap-3 text-sm",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: "mega-travel signed in (50 GB)" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
								type: "checkbox",
								checked: travelSignedIn,
								onChange: (event) => onTravel(event.target.checked),
								className: "size-5 accent-copper"
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs leading-relaxed text-faint",
							children: "Leave travel signed out and primary under 20 GB to watch a full Drive account hand the file to MEGA."
						})
					]
				})]
			})]
		})]
	});
}
function Pool({ frame, scale }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "rounded-md border border-line bg-surface p-5",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-2xl font-medium text-balance",
					children: "One pool, one copy"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-3 max-w-3xl text-pretty text-sm leading-relaxed text-muted",
					children: "Drive and MEGA are not two backups. A video lands on exactly one account: the one with the most free space that can accept the file. If that upload comes back storage-full, the next account is tried. If it comes back rate-limited, the same account is retried with backoff. Auth failures are skipped. Space the API did not report is not treated as unlimited."
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "grid gap-3 sm:grid-cols-2",
				children: frame.accounts.map((account) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
					className: "rounded-md border border-line bg-surface p-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-baseline justify-between gap-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
								className: "text-sm font-medium",
								children: account.name
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-mono text-xs text-muted",
								children: account.provider === "gdrive" ? "Drive" : "MEGA"
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 font-mono text-lg tabular-nums",
							children: account.authOk ? formatGb(account.freeGb) : "Signed out"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "mt-3 h-2 overflow-hidden rounded-md bg-bg",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
								className: "h-full " + (account.available && account.authOk ? "bg-copper" : "bg-line"),
								style: { width: `${account.authOk ? Math.max(2, account.freeGb / scale * 100) : 0}%` }
							})
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 text-xs text-muted",
							children: account.note
						})
					]
				}, account.id))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("section", {
				className: "rounded-md border border-line bg-surface p-5 text-sm leading-relaxed text-muted",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: "Run the night on the Tonight tab, then come back. The bars move only after a real acceptance. A storage refusal zeros that account for the rest of the sample night. A rate limit does not." })
			})
		]
	});
}
var FIELDS = [
	{
		name: "channel_id + message_id",
		meaning: "Identity. A successful pair is never uploaded again."
	},
	{
		name: "filename / remote_filename",
		meaning: "The Telegram name, and the cloud object name with the message id in front."
	},
	{
		name: "file_size",
		meaning: "Bytes. Used for ranking and for the runner disk check."
	},
	{
		name: "status",
		meaning: "discovered, pending, success, or needs_attention."
	},
	{
		name: "provider + account",
		meaning: "Where the one copy went. Empty unless status is success."
	},
	{
		name: "destination_file_id",
		meaning: "Drive file id or MEGA node handle."
	},
	{
		name: "error_class",
		meaning: "storage, transient, auth, permanent, unknown, or runner_disk. Rate limits stay transient."
	}
];
function Ledger({ frame }) {
	const counts = frame.rows.reduce((acc, row) => {
		acc[row.status] = (acc[row.status] || 0) + 1;
		return acc;
	}, {});
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-4",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
				className: "rounded-md border border-line bg-surface p-5",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
						className: "text-2xl font-medium text-balance",
						children: "The file in the repository is the database"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-3 max-w-3xl text-pretty text-sm leading-relaxed text-muted",
						children: "data/backup_db.json is committed after each video. The runner’s disk is wiped when the job ends. Success is written only with a destination file id."
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dl", {
						className: "mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4",
						children: [
							"stored",
							"pending",
							"waiting",
							"ignored"
						].map((status) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "rounded-md bg-bg px-3 py-3",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("dt", {
								className: "text-xs text-faint",
								children: STATUS_LABEL[status]
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("dd", {
								className: "mt-1 font-mono text-xl tabular-nums",
								children: counts[status] || 0
							})]
						}, status))
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "overflow-x-auto rounded-md border border-line bg-surface",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("table", {
					className: "w-full min-w-xl text-left text-sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("thead", {
						className: "border-b border-line text-xs text-faint",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", { children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "px-4 py-3 font-medium",
								children: "Message"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "px-4 py-3 font-medium",
								children: "File"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "px-4 py-3 font-medium",
								children: "Status"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "px-4 py-3 font-medium",
								children: "Account"
							})
						] })
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tbody", { children: frame.rows.map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
						className: "border-b border-line last:border-b-0",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "px-4 py-3 font-mono text-xs tabular-nums",
								children: row.messageId
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("td", {
								className: "px-4 py-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "block",
									children: row.filename
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "text-xs text-muted",
									children: row.note
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "px-4 py-3",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "rounded-md px-2 py-1 text-xs " + statusClass(row.status),
									children: STATUS_LABEL[row.status]
								})
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "px-4 py-3 text-muted",
								children: row.account || "—"
							})
						]
					}, row.messageId)) })]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "grid gap-2",
				children: FIELDS.map((field) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", {
					className: "grid gap-1 rounded-md border border-line bg-surface px-4 py-3 sm:grid-cols-[14rem_minmax(0,1fr)]",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "font-mono text-xs text-copper",
						children: field.name
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
						className: "text-sm text-muted",
						children: field.meaning
					})]
				}, field.name))
			})
		]
	});
}
function Home() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Console, {});
}
//#endregion
export { Home as component };
