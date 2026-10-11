# 4.1.25 changelog draft: the remediation stage (PRs 231 onward)

Draft for the delivery lead, who writes the final CHANGELOG.md. The existing
`## [4.1.25]` section in CHANGELOG.md already covers the features (pictures and
documents, sources, bots, engine upgrade) and two remediation items: export
(PR 232) and erasure/backups (PR 240). This draft adds everything else from the
fix stage. Each line names its ledger ids (FIX-LEDGER.md) and PR. Lines marked
**[pending]** describe work that is on a branch or still being built; drop or
reword them if they do not merge.

Release head when drafted: origin/release/4.1.25 = a2c8520a.

## Fixed: recall says "nothing found" instead of guessing

- Recall again abstains when nothing in memory supports the question: the evidence floor compares the cosine it documents, on the channel's own scale. (E-C1 floor; PR 231)
- A question can no longer reach an unrelated person or project through a chain of near-miss names. Entity matching is exact, then normalised, then one typo in one word; it never merges different numbers or versions and never fuzzy-matches against aliases that were themselves fuzzy. Question words are looked up exactly unless they are everyday English, so "zxqv plorth wimble" finds no entity. (L-02, E-H1, N-02, ENG-03; PR 234)
- Entity names are real names: timestamps, hashes, paths, status words like PASS or LIVE, and sentence fragments are no longer saved as people or projects. (L-07, E-H2, N-13; PR 234, PR 238)
- New `slm db repair-entities` previews, applies (with a backup and an undo record) and undoes the clean-up of links left by the old entity rules. (L-02, N-13; PR 234, PR 238)
- **[pending]** The answer check is calibrated per store, a sentence of random IDs no longer counts as an answer, the built-in Nomic model gets its retrieval prefixes through a staged re-embed, recall waits for the query embedding only within its budget, a slow but healthy Laya worker is not killed, and "warming" and a skipped check are reported as such. (L-03, N-03, N-12, E-M2, E-M8/ENG-12, ENG-04, ENG-20, OPS-30, OPS-32, UX-16, L-13, L-18, E-M5, BRN-22; WP-6, no PR yet)

## Fixed: recall stays fast while you write

- A save no longer forces the whole graph to rebuild on the next recall. The cached graph follows writes incrementally; deletes and erasures leave it before the walk; full rebuilds run in the background at most once per 30 s. On a 26k-fact benchmark with writes every 2 s, p95 went from 4.3 s to 0.94 s and memory from up to 1.7 GB to about 260 MB. (N-11, L-04, E-H4, E-M6; PR 236)
- Enrichment uses the entity index instead of scanning the profile, and the duplicate check uses a content index: median enrichment on a 26k-fact store went from 7.44 s to 0.76 s excluding model time. (L-08, ENG-29, E-M7 main path; PR 237)
- **[pending]** Further recall-channel indexes and caches for large stores (migrations M056 to M058), and the keyword fallback no longer keeps an unread copy of every saved text. (N-11 residual, E-L2; WP-4b, no PR yet)

## Fixed: what is saved is what you said

- Every extracted statement is checked against its source before it is stored: no added names, numbers or dates, no flipped negation, no names leaking from the prompt's example. Mode B extraction went from 55 of 124 to 0 of 54 unsupported statements on a 40-note set; the original note is always kept. (L-01/ENG-14; PR 237)
- Quoted speech is never rewritten and each speaker's turn is handled separately, so "Priya said 'I am leaving'" stays Priya's. (N-09/ENG-02; PR 237)
- Relative dates ("last Tuesday") resolve against the memory's own date, not the day the daemon processed it. (ENG-15; PR 237)
- Saving the same text twice no longer adds a row or bumps its use count, and a duplicate keeps the new save's scope, project and event date. (E-M1/ENG-11; PR 237)
- Long texts are chunked instead of holding the worker; a long paste says it was truncated and where the full text is; the best installed local model is recommended, never switched silently. (E-M4, E-L1, L-19; PR 237)
- **[pending]** A statement that fails the source check is kept for review with its reason instead of being dropped, never used in answers; if the check itself fails, unchecked derivatives are withheld and recall reports reduced fidelity. (N-14; PR 242 in batch PR 246)

## Fixed: the learning loop actually learns

- One outcome writer for MCP, REST, the tracker and the new `slm outcome` command; one query id from recall through to the reward; each outcome settles exactly one recall, across restarts and concurrent settlers (migration M055, learning.db, additive). (BRN-05, BRN-11, BRN-13; PR 235)
- The candidate ranker is actually served during its test and is promoted or rejected by a sequential test with a measured 1.3 to 1.7 % false-promotion rate; training sees real labels. (BRN-01, BRN-12, BRN-19; PR 235)
- Consolidation's dry run writes nothing, reports real bytes, never revives an invalidated fact, parses UTC offsets, does not count itself as use, and does not resurrect rejected advice; the behaviour miner stays within one session and project; "lossless" normalisation keeps code byte for byte. (BRN-02, BRN-03, BRN-04, BRN-06, BRN-10, BRN-25, BRN-31, BRN-32; PR 235)
- Health shows "Not demonstrated" until an outcome has settled (`GET /api/learning/readiness`). (BRN-21; PR 235)
- **[pending]** Bounded loops report DONE only with an independently executed, immutable check receipt; soft prompts survive feedback and review; skill health comes from the skill's own runs; the retention policy is applied; forgetting respects pinned and recently rewarded facts, source trust and real use; skill evolution uses installed local models and survives reload, activation and rollback; MCP compression keeps one tenant-owned recovery copy and counts its savings; Mode A consolidation works without entity signals; MCP sessions register as mesh peers at start. (BRN-07, BRN-08/G-H1, BRN-09, BRN-14 to BRN-17, BRN-23, BRN-24, BRN-26, BRN-28 to BRN-30, E-H3, L-10; PR 247)

## Fixed: company mode and access

- Every state-changing route asks for a role in company mode: a deny-by-default check runs before body validation, so refusals are 401 or 403, never 422 or 500; restarting the daemon needs MANAGE. (G-C1, G-H3/OPS-18, G-H4, G-L3; PR 233)
- **[pending]** One identity check on every door: a signed-out or revoked session is refused instead of becoming the machine owner; a login accepted over REST is the same identity over HTTP MCP; reads check READ on every workspace a request names; MCP tools and resources are gated (only `get_version` is public); a workspace keeps at least one admin, with `slm team admin` and `slm team reset-password` for recovery; the audit chain hashes every field and records access-control events; failed-operation tools are scoped to the caller's workspaces and report an unreadable database as unavailable; Jev consent changes write a receipt; agent attribution comes from the connection; `slm ops repair-saves` re-files saves the old dedup folded onto another memory. (OPS-01, OPS-08 to OPS-10, OPS-16, OPS-17, OPS-19, OPS-21 to OPS-27, G-M5, G-M6, L-06, L-15/G-M2, L-16/G-L2, UX-12, UX-13, UX-20, UX-21, G-L4; WP-9b, no PR yet)

## Fixed: export, doctor and messages

Already in CHANGELOG.md for PR 232 (export). Not yet listed there:

- Doctor shows failed saves with the retry command, and reads the Codex version that `upgrade-hosts` writes. (L-05/OPS-15, L-21; PR 232)
- The write-auth message names the `X-Install-Token` header for local callers. (L-20; PR 232)

## Fixed: frameworks and editor hosts

- Google ADK, CrewAI and Semantic Kernel run through an isolated engine bridge instead of failing to install next to SLM; CrewAI declares its real Python range. (UX-18, UX-19, UX-22; PR 239)
- Microsoft Agent Framework keeps message roles and content; AutoGen returns the text and the caller's metadata; all nine framework quickstarts run as written. (UX-25, UX-26, UX-27; PR 239)
- Continue, OpenCode, Antigravity, VS Code and Gemini CLI setup writes each host's current schema; discovery and installation agree; HTTP verification checks the real `/health` and lists tools. (BRN-18, BRN-20, BRN-27, UX-33, UX-34, UX-38, UX-41, UX-42; PR 239)
- The Optimize SDK quickstarts import what exists, and the standalone cache works when initialised. (UX-39, UX-40; PR 239)

## Fixed: erasure and backups

Already in CHANGELOG.md (PR 240). Ledger ids for traceability: OPS-04 to OPS-07, OPS-11 to OPS-14, OPS-20, OPS-28, OPS-29, OPS-33, OPS-34, UX-31, UX-35, ENG-30, ENG-31, G-M4, N-05.

## [pending] Connected apps, ports and services (PR 245)

- The dashboard shows which apps are connected right now (live MCP processes by host, with a count), flags apps still running older SLM code and offers a reconnect. (UI-1/L-09/G-M3, G-M1, N-07)
- Connect, doctor, repair and restart are buttons; Connect writes an absolute interpreter path. (UI-2, UX-11, UX-14)
- `slm dashboard`, Health, Settings and HTTP setup use the configured port; strict credential settings survive auto-start; a second install gets its own service name, and old services are migrated only when they provably belong to this install. (OPS-02, OPS-03, UX-01, UX-02, UX-03, N-04)
- `--sync` saves return after enrichment completes, the Python API shares the daemon's embedder, turning media on gives connected harnesses the media tools, failed session opens exit non-zero, and a queued upgrade says why it waits. (ENG-25/OPS-35, OPS-31, ENG-10, ENG-22, UX-45, L-22)

## [pending] Maths, pictures and managed runtimes (PR 243 in batch PR 246)

- Fisher-Rao distance uses standard deviation; Hopfield temperature scales with dimension and is saved; FRQAD penalises lower precision monotonically; the 2-bit TurboQuant codebook uses all four levels (old vectors still decode). (ENG-05, ENG-06, ENG-07, ENG-24)
- Point-in-time snapshots never return a future fact; causal edges need an asserted cause in one clause, in order, within seven days; a contradiction needs the same subject and attribute. (ENG-13, ENG-16, ENG-18)
- Two different wordless pictures stay two memories with their own thumbnails; wordless pictures get a stored caption or OCR summary; picture search is capped at 32 candidates. (ENG-09, L-11, L-12, ENG-19 channel side)
- A copied or moved data folder no longer runs the original folder's Laya runtime or model. (N-08/ENG-01)

## [pending] Dashboard (WP-10)

Recall Lab and answer-check states, settings accessibility and phone width, audit table fields, backup recovery, keyboard access to memories and entities, ingestion status, activity by date range, contrast, and the daily search that answers (UI-3, UI-4, LOCAL, UX-04 to UX-07, UX-09, UX-10, UX-15, UX-17, UX-23, UX-24, UX-28 to UX-30, UX-32, UX-36, UX-37, UX-43, UX-44, UX-46, G-H2, ENG-08, ENG-21, ENG-23, L-14, L-17). Write the lines from the merged diff, not from this list.

## Internal (tests and docs; probably one line in the final changelog)

- Test isolation fixes and the merge gate that runs every test importing a changed module. (N-01 PR 231, N-15 process)
- README quick-start order, the company-mode status flake, learned-ranking order dependence, stale editable-install guard, adjacency docstring, 8 s hang guard kept with a regression test, unused imports. (N-06, N-10, E-L3, E-L4, E-L5; PR 241)
- Three release-branch test failures fixed (diagnostics mock, remote binding classification, vector-parity receipts). (PR 244 in batch PR 246)
