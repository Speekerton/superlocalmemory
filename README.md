<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/branding/slm-wordmark-dark.svg">
  <img src="assets/branding/slm-wordmark-light.svg" alt="SuperLocalMemory" width="380">
</picture>

<p align="center"><img src="assets/mascot/slm-mascot-hero.png" width="180" alt="SuperLocalMemory mascot, a fluffy caped helper with the SLM logo, arms open"></p>

### The governed memory system for AI agents. On your computer, honest when it doesn't know.

Claude Code, Codex, Cursor, ChatGPT, Grok Bot and other MCP clients share one memory that lives on your machine. It learns from use, controls who may read and erase what, and says "That isn't in SuperLocalMemory." instead of guessing. It remembers **pictures and documents** you can find by describing them, looks after its own older memories with **Memory health**, and lets **your bots talk to each other** through the same governed memory.

It works with any harness that speaks MCP or can run a command (`slm remember`, `slm recall`). The six packaged plugins (Claude Code, Codex, GitHub Copilot, Antigravity, Hermes and the Cursor-format plugin for Grok Bot) are examples of that, not a list of what is supported.

[![PyPI](https://img.shields.io/pypi/v/superlocalmemory)](https://pypi.org/project/superlocalmemory/)
[![npm](https://img.shields.io/npm/v/superlocalmemory)](https://www.npmjs.com/package/superlocalmemory)
[![PyPI downloads](https://img.shields.io/pepy/dt/superlocalmemory?label=PyPI%20downloads)](https://pepy.tech/project/superlocalmemory)
[![npm downloads](https://img.shields.io/npm/dt/superlocalmemory?label=npm%20downloads)](https://www.npmjs.com/package/superlocalmemory)
[![GitHub stars](https://img.shields.io/github/stars/qualixar/superlocalmemory?style=flat&logo=github)](https://github.com/qualixar/superlocalmemory/stargazers)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)
[![Research: 4 arXiv papers](https://img.shields.io/badge/arXiv-4_papers-b31b1b)](#research)

**[Install](https://www.superlocalmemory.com/install)** · **[Product walkthrough](https://www.superlocalmemory.com/demo)** · **[Demo video](https://www.youtube.com/watch?v=pyAu_vaIYZQ)** · **[CLI proof](docs/QUICK_PROOF.md)** · **[Docs](#documentation)** · **[Release notes](CHANGELOG.md)**

<img src="docs/screenshots/dashboard/answer-check-dont-have-that.png" alt="Answer check in the dashboard: for &quot;How much did the Kestrel pilot cost?&quot; no memory answers it, so SLM says &quot;I don't have that&quot; instead of guessing" width="820">

</div>

**Most agent memory is a vector store with a save button. SuperLocalMemory is a governed memory system:** every save passes an admission check and gets a receipt, every read respects roles, profiles and scopes, every erasure is provable, every recall can be checked for whether it actually answers the question, and all of it runs on your own computer with no model call required.

## New: pictures and documents, and bots that talk to each other

| Remember what you see | Let your bots talk to each other |
|---|---|
| Save a screenshot, a photo or a PDF, then find it weeks later by describing it: "the slide with the quarterly numbers", "the error dialog from the deploy". A picture model on your computer matches your words to the picture, OCR reads the text inside it, and each PDF page is indexed by its picture and its text. No generative model looks at your files and nothing leaves your machine.<br><br>Built in and **off by default**: one click in the dashboard, one question in the npm installer or upgrader, or `slm media enable`. Your existing memories and embeddings are never changed. Needs a computer with 16 GB of memory; the first set-up downloads about 1.5 GB. Connect a folder or an Obsidian vault with `slm sources`. | ChatGPT, Claude on the web, Grok Bot, Muse and Composio, connected through [Web access](#web-apps-and-bots-web-access), now join SLM-Mesh beside the agents on your computer (Claude Code, Codex, Hermes, Antigravity). They see each other with `mesh_peers`, send a named bot a message, read their inbox and read shared state.<br><br>Honest about real time: a message lands in the inbox at once, but a web app reads it when its next turn starts; SLM never pretends to wake a chat window. Each app needs two yeses: a box you tick when you connect it, and a switch on the **Web access** row in Connected apps (or `slm remote keys allow <key> mesh`). The **Bot messages** tab shows every bot by name. |

[How pictures and documents work](#pictures-and-documents) · [Requirements and limits](docs/pictures-and-documents.md) · [How bot messaging works](#bot-to-bot-messaging)

**Recall tells you when memory cannot answer.** Every recall comes back in one of three tiers. *Supported*: at least one memory is strong enough evidence for the question. *Closest memories*: nothing supports it, but the question is a real one and a few memories are close, so you see up to three, labelled, under "I don't have this exactly — here are the closest memories." *Not in memory*: nonsense, or nothing close, and recall returns nothing under "That isn't in SuperLocalMemory." While SLM is still warming up after a start it says so and shows what it has found, and never claims the memory is empty ([how recall decides](docs/recall.md#when-memory-cannot-answer)).

**An on-device answer check, installed for you where it can run.** On Apple Silicon, setup installs **Laya** (about 1.1 GB) by default, with no terminal question in unattended runs; it judges on your Mac whether the memories found answer the question and nothing leaves the machine. Opt out with `slm setup --no-laya` or `SLM_SKIP_LAYA=1`. **Jev**, the online check, stays off until you choose it and tick its consent ([answer check](#answer-check-laya-and-jev)).

**Your bots and web apps can use the same memory.** Local agents connect over MCP, including the Grok Bot plugin on a shared bot computer. ChatGPT, Claude on the web, Muse, Composio and other web MCP clients can reach it through optional [Web access](#web-apps-and-bots-web-access): you sign in with GitHub for each app, choose whether it may only read or also save, and remove any app at once.

Mode A saves and recalls memories without a language model, and nothing leaves the device unless you turn on the online answer check (Jev). Anything that sends data out is a choice you make, and the docs say exactly what goes.


```bash
npm install -g superlocalmemory   # primary route (Node 18+, Python 3.12+); or: pipx install superlocalmemory
slm setup                         # pick Mode A to keep everything on this machine
slm connect cursor                # or codex, windsurf, zed, claude-desktop, jetbrains, opencode ... (Claude Code uses the plugin)
```

npm installs SLM into a package-owned virtual environment. The other primary route is pip in a Python virtual environment you activate: `python3 -m venv .venv`, activate it, then `python -m pip install superlocalmemory`. Repository clone: `./scripts/install.sh install` (macOS, Linux) or `.\scripts\install.ps1 -Action Install` (Windows); see [CONTRIBUTING.md](CONTRIBUTING.md).

Runs on Windows, Linux and macOS ([platforms](#platform-support)). No Docker, no required graph database, no API key.

## What it does

| If you are | You get | Where |
|---|---|---|
| Anyone | One memory on your computer that every connected agent shares: Claude Code, Codex, Cursor, Copilot, Antigravity, Hermes, ChatGPT and more | [Works with your agents](#works-with-your-agents) |
| Anyone | Recall in three honest tiers: supported, closest memories, or "That isn't in SuperLocalMemory." Never a confident guess | [Recall](docs/recall.md) |
| Anyone | An on-device answer check (Laya), installed by default on Apple Silicon; an optional online one (Jev) | [Answer check](docs/answer-check.md) |
| Anyone | Pictures, screenshots and PDFs you find by describing them; folders and Obsidian vaults mirrored read-only | [Pictures and documents](docs/pictures-and-documents.md) |
| Anyone | **Memory health**: older memories described and tidied in the background, only ever by adding, with a Fix button and Undo for anything bigger | [Memory health](docs/memory-health.md) |
| Anyone | A dashboard with search, a knowledge graph, an answer-check view, connected apps, bot messages and governance | [Dashboard](docs/DASHBOARD-COVERAGE.md) |
| Anyone | Backup that is encrypted before upload, restore points before each store update, and a restore that rolls back if it fails | [Cloud backup](docs/cloud-backup.md), [Restore points](docs/restore-points.md) |
| Teams | Roles per workspace, company mode with sign-in, personal / shared / global scopes, a hash-chained audit trail, GDPR export and verified erasure that also removes derived copies | [Teams](docs/rbac-teams.md), [Compliance](docs/compliance.md) |
| Developers | An MCP server (stdio or HTTP) with tool profiles from 9 to 110 tools, a CLI, a REST API and a Python SDK | [MCP tools](docs/mcp-tools.md), [CLI](docs/cli-reference.md), [API](docs/api-reference.md) |
| Developers | Layered recall: `depth` 0 (ids and one-line previews), 1 (full facts), 2 (with source, neighbours and the correction that replaced it), a hard `max_tokens` cap, and an `expand` tool to drill into one result | [Recall](docs/recall.md#layered-recall) |
| Developers | Adapters for LangGraph, LangChain, LlamaIndex, CrewAI, AutoGen, Semantic Kernel, Microsoft Agent Framework, Google ADK and the OpenAI Agents SDK | [Framework adapters](docs/framework-adapters.md) |
| Developers | SLM-Mesh messages, locks and shared state between agent sessions and the web apps you allow; bounded loops that finish only when an independent gate passes | [Multi-machine](docs/multi-machine.md), [Bounded loops](docs/bounded-loops-bridge.md) |
| Developers | Exact cache and reversible compression of tool output, a proxy or MCP tools, no change to your context window | [Optimize](docs/optimize-overview.md) |
| Developers | Bi-temporal queries (`--valid-at`, `--known-as-of`), nine memory kinds, saved views and summaries that cite their memory ids | [Recall](docs/recall.md), [Memory kinds](docs/memory-kinds.md) |
| Operators | Modes A, B and C (no language model, a model on this machine, or your own endpoint), SQLite canonical with optional CozoDB and LanceDB projections, remote access over TLS, `slm doctor` | [Configuration](docs/configuration.md), [Scale engine](docs/scale-engine.md), [Troubleshooting](docs/troubleshooting.md) |

## 30-second example

```console
$ slm remember "We deploy the API blue-green; rollback is a DNS flip." --kind decision
Queryable ✓ 1 facts (operation=ebca8e80...).
$ slm remember "Always run the migration dry-run before a release." --kind rule
$ slm remember "Staging DB is Postgres 16 on port 5433."

$ slm recall "how do we roll back the API"
  1. [0.67] We deploy the API blue-green; rollback is a DNS flip.
  2. [0.53] Always run the migration dry-run before a release.
  3. [0.52] Staging DB is Postgres 16 on port 5433.

$ slm recall "what did we decide about rollback" --kind decision
  1. [0.54] We deploy the API blue-green; rollback is a DNS flip.

$ slm remember "Staging DB moved to Postgres 17 on port 5434." --replaces 0f57a17af3dd46e5
Replaced ✓ 1 fact(s) of 0f57a17af3dd46e5.
To undo, run:
  slm review-correction ... rollback 1
$ slm recall "which port does staging postgres use"
  1. [0.68] Staging DB moved to Postgres 17 on port 5434.
```

Real output from a fresh Mode A install, trimmed. Scores rank; they are not probabilities. While the embedding model loads, recall says `Incomplete search`.

### Watch the product film

[![Watch the SuperLocalMemory demo: Claude Code and Codex sharing one memory](https://img.youtube.com/vi/pyAu_vaIYZQ/maxresdefault.jpg)](https://www.youtube.com/watch?v=pyAu_vaIYZQ)

Four minutes on a real local install, every dashboard pane: recall, the knowledge graph, the answer check, one memory shared by Claude Code, Codex, Cursor and ChatGPT, SLM Mesh, governance, caching and compression.

### The dashboard

The picture at the top and these are captured from a real install in Mode A, with Laya running on the Mac and a store of fictional project memories. Nothing is mocked: each verdict, score and timing is what SLM returned.

| Memories that answer the question | Recall Lab: why each memory was chosen |
|---|---|
| ![Answer Check: Laya judges that the memories answer "When is Project Kestrel going live?" with confidence 0.85, in 1.4 s of the 3 s limit](docs/screenshots/dashboard/answer-check-answered.png) | ![Recall Lab: per-channel scores for "what did we decide about the database"](docs/screenshots/dashboard/recall-lab.png) |

| Every memory with its kind and project | Saved views |
|---|---|
| ![Memories table filtered by kind: decisions, rules, corrections, facts, with the project each belongs to](docs/screenshots/dashboard/memories-kinds-projects.png) | ![Saved views: a saved question that runs the same search your agent uses and shows the memory each result came from](docs/screenshots/dashboard/saved-views.png) |

<!-- SCREENSHOTS TO CAPTURE ON THE RELEASE BUILD, then add as a table row here:
| Documents & Images: a picture found by describing it | Bot messages: every connected bot by name |
docs/screenshots/dashboard/documents-images.png · docs/screenshots/dashboard/bot-messages.png -->

![Connected apps: Web access is on, linked with GitHub for the default profile, renews automatically, with a free daily allowance and a button to add an app or turn access off](docs/screenshots/dashboard/connected-apps.png)

## Why SuperLocalMemory

A vector store answers "what is similar". AI agent memory must also answer: is this still true, who may see it, can it be erased with proof, and does the agent actually have the answer?

**1. Governed memory, not a vector store.** Roles per workspace, personal / shared / global scopes with default-deny cross-profile recall, GDPR erasure with HMAC-verifiable receipts, retention rules and a hash-chained audit log. The [governed-memory paper](https://arxiv.org/abs/2608.08253) measures what the governed write path costs. Code: `src/superlocalmemory/access/`, `compliance/`.

**2. A zero-LLM core built on published math.** Six retrieval channels and fusion run without a language model; the published architecture scored 60.4% on LoCoMo with no LLM anywhere ([benchmarks](#benchmarks)). Fisher-information scoring, sheaf contradiction detection and Langevin lifecycle dynamics added 12.7 points ([architecture paper](https://arxiv.org/abs/2603.14588)).

**3. It says "That isn't in SuperLocalMemory."** Recall scores each memory on several signals together and answers only when one is strong enough; otherwise it shows the closest memories, labelled, or nothing. The [answer check](docs/answer-check.md) adds a second opinion from a model on your Mac (Laya) or online (Jev).

**4. Memory that learns, and cannot quietly get worse (opt-in).** With `SLM_RANKING` set, a Thompson-sampling bandit tunes channel weights and a LightGBM ranker learns from reported outcomes. A retrained ranker is served to half of live recalls and promoted only when an always-valid sequential test (mSPRT, α = 0.05) shows a higher reward from reported outcomes; after promotion it is rolled back automatically if mean settled reward drops 2% or more over a 200-recall watch window. That watch measures outcome reward, not NDCG. Off by default, so a fresh install ranks the same way every time. Code: `learning/shadow_test.py`, `learning/model_rollback.py`.

**5. Memory with a sense of time.** Every fact records when it happened and when SLM learned it. Ask what was true last month (`--valid-at`) or what SLM knew before a date (`--known-as-of`). Unused memories fade and lose vector precision ([lifecycle paper](https://arxiv.org/abs/2604.04514)).

**6. Many agents, one coordinated memory.** Every write records its agent, with Bayesian trust scores against poisoning ([trust paper](https://arxiv.org/abs/2603.02240)). SLM-Mesh gives parallel sessions messages, locks and shared state, and web apps and bots you connect can join it with your permission.

**7. "Done" means a gate passed.** Bounded loops repeat a task until an independent check (tests, a schema, a linter) passes, never on the agent's word, and store every lap as auditable memory.

**8. Context you don't pay for twice.** Exact cache and reversible compression work through MCP tools or a skill, with no proxy, so your full context window stays intact.

**9. Memory that sees.** Screenshots, photos and PDF pages become memories you recall by describing them, with no generative model in the path. A picture counts as evidence only above the model's own similarity floor, so a question about something you never saved does not surface the nearest wrong picture.

SLM is part of Qualixar's AI Reliability Engineering work: agent memory that is observable, bounded and honest about what it doesn't know.

## Works with your agents

| Surface | What you get | Docs |
|---|---|---|
| Editor plugins | Claude Code, Codex, VS Code / Copilot, Antigravity, Hermes. Each ships 16 skills, 4 sub-agents and session hooks; the npm package carries every plugin folder | [Plugins](docs/plugins.md), [IDE setup](docs/ide-setup.md), [Hermes](docs/hermes.md) |
| Any other agent | The universal agent rules: one file that teaches any agent when to recall, what to save and how to keep memory clean. Paste it into `AGENTS.md`, `CLAUDE.md`, `.cursorrules` or the agent's system prompt | [Universal agent rules](plugin-src/rules/AGENTS.md) |
| `slm connect <ide>` | Writes the MCP config for Cursor, Windsurf, Zed, JetBrains, Gemini CLI, Claude Desktop, VS Code / Copilot, Antigravity, OpenCode, Continue and Codex CLI; `slm connect claude-code` points you to the plugin and Hermes installs as a native plugin | [IDE setup](docs/ide-setup.md) |
| MCP | stdio (`slm mcp`) or HTTP at `http://127.0.0.1:8765/mcp/`; profiles from 9 to 110 tools | [MCP tools](docs/mcp-tools.md) |
| Framework adapters | LangGraph, LangChain, LlamaIndex, CrewAI, AutoGen, Semantic Kernel, Microsoft Agent Framework, Google ADK, OpenAI Agents | [Framework adapters](docs/framework-adapters.md) |
| Python SDK and HTTP API | `MemoryEngine` in your code; the local REST API | [API reference](docs/api-reference.md) |
| Auto-capture hooks | `slm hooks install` for Claude Code, `--agent codex` for Codex | [Auto-memory](docs/auto-memory.md) |
| Web apps (ChatGPT, Claude on the web, Muse, Composio) | Optional Web access, turned on from the dashboard: OAuth sign-in, read or save per app, and a Connected apps page to remove any app at once. With your permission an app can also message your other bots (`slm:mesh`) and use pictures (`slm:media`). Copy-paste instructions tell the app when to recall and what to save | [Web access](#web-apps-and-bots-web-access), [Host guides](docs/remote-access/hosts.md), [Web agent instructions](docs/web-agents/README.md) |
| Cursor-format plugin (Grok Bot, Cursor) | A marketplace-distributed plugin — different from `slm connect cursor` above — that runs on a shared, memory-tight computer with no hooks or dashboard | See below |

### Set up your platform

SuperLocalMemory has no list of approved hosts. Any harness that speaks MCP can use `slm mcp` (stdio) or `http://127.0.0.1:8765/mcp/`, and any harness that can run a command can call `slm remember` and `slm recall`. Install it once, then connect the host:

| Platform | Set up | What you get | Honest limits |
|---|---|---|---|
| Claude Code | `claude plugin marketplace add qualixar/superlocalmemory`, then `claude plugin install superlocalmemory@qualixar` | MCP server, 16 skills, 4 sub-agents, `/slm-loop`, session and recall hooks | The plugin runs the `slm` you installed; on Windows it stops with a plain message when `slm` is not on PATH |
| Codex | `slm connect codex`, then `slm codex install` (or `codex plugin add superlocalmemory-codex@qualixar`) | MCP server, 16 skills, 4 sub-agents, `/slm-loop`, lifecycle hooks | Review and trust the new hooks with `/hooks`; the agent rules in `codex-plugin/AGENTS.md` are yours to append |
| GitHub Copilot (VS Code, Visual Studio, JetBrains, Eclipse, CLI) | `slm connect vscode-copilot --here` in the project, then copy the add-ons from `copilot-plugin/.github/` | MCP server, agent rules, 16 prompt files, 4 agents, hooks | MCP is generally available everywhere; prompts, agents and hooks are additive and hooks are a preview in VS Code |
| Antigravity (`agy`) | `agy plugin install "$(npm root -g)/superlocalmemory/antigravity-plugin"` | MCP server, 16 skills, 4 agents, `/slm-loop`, hooks | `agy plugin install` takes a local folder; with a pip install run `scripts/install-antigravity-plugin.sh` |
| Hermes | `hermes plugins install 'https://github.com/qualixar/superlocalmemory.git#hermes-plugin'` | 16 skills, advisor child agents, `/slm <command>` and a `/slm-<command>` alias for each | Installed disabled; grant only the `superlocalmemory` MCP server; destructive commands need a `CONFIRM` token; a remote SLM supports a fixed command set |
| Cursor-format hosts (Grok Bot, Cursor) | Add the `qualixar` marketplace in the Plugins screen, then `superlocalmemory` | MCP server on the 19-tool `core` profile, a bot-sized skill set | No hooks, no dashboard, no interactive setup; designed for a shared, memory-tight computer |
| Cursor, Windsurf, Zed, JetBrains, Gemini CLI, Claude Desktop, OpenCode, Continue | `slm connect <name>` (`--dry-run` first) | MCP server in that tool's own config format | MCP only: no skills or hooks |
| ChatGPT, Claude on the web, Muse, Composio, other remote MCP clients | Web access from the dashboard, then the [host guide](docs/remote-access/hosts.md) | Recall and, if you allow it, save, mesh and pictures | Your computer must be online; each app is limited by what you tick |
| Anything else | Paste the [universal agent rules](plugin-src/rules/AGENTS.md) into its instructions and give it the CLI or MCP | Memory discipline for any agent | You wire the hooks yourself, if it has any |

`slm connect` lists every host it can write for with `slm connect --list`. Hosts that update on their own schedule are checked by `slm upgrade-hosts`, which previews and changes nothing until you add `--apply`.

### What the packaged plugins contain

All six plugins are generated from one source, `plugin-src/`, so they carry the same skills and agents adapted to each host. The skills teach an agent when and how to use SLM; the agents are bounded helpers it can hand a job to; the hooks run at session events without the agent doing anything.

| Skill | What it teaches |
|---|---|
| `slm-recall` | Searching memory: filters, kinds, time windows, the three recall tiers, `depth`, `max_tokens`, `expand` |
| `slm-remember` | What is worth saving, memory kinds, `replaces`, corrections |
| `slm-session` | Session start and close, pinned items and standing rules |
| `slm-status` | Health, `slm doctor`, `slm db integrity` and `repair`, optimize counters |
| `slm-governance` | Roles, company mode, retention, audit, GDPR export and erasure, what remote apps never see |
| `slm-scope`, `slm-profile` | Personal, shared and global memory; switching memory profiles and tool sets |
| `slm-graph` | The knowledge graph and code graph tools |
| `slm-mesh` | Messages, `mesh_wait`, locks and shared state between sessions and allowed web apps |
| `slm-loop` | Bounded loops with SLM as the ledger |
| `slm-cache`, `slm-compress` | KV cache and reversible compression |
| `slm-web-access` | Setting up and diagnosing Web access, Connected apps and upload links |
| `slm-media` | Pictures, PDFs and folders: `remember_media`, `remember_document`, `media_upload_link`, `slm media`, `slm sources` |
| `slm-bot-memory`, `slm-getting-started-bot` | Several bots on one computer; first-session orientation on a headless bot host |

| Sub-agent | Job |
|---|---|
| `slm-memory-advisor` | When to remember or recall, how to phrase a query, how to keep memory clean |
| `slm-optimize-advisor` | Compress and cache to stretch the context window; advisory and fail-open |
| `slm-governance-advisor` | Scope, roles, retention and erasure decisions; never bypasses a control |
| `slm-loop-runner` | Runs a task as a bounded loop until an independent gate passes |

The Claude Code plugin's hooks, in the order they matter: at session start one hook prints the `session_init` guidance, another injects project context, and the launcher makes sure the environment exists. `checkpoint` records files you edit. `post_tool_outcome` and `stop_outcome` notice which recalled memories were actually used and settle each outcome. `user_prompt_rehash` treats the same question asked again within a minute as a sign the last answer missed, and `topic_shift` reminds the agent to recall when you change subject. `before_web` runs a recall before a web search or fetch. `stop` saves a session summary. Codex, Copilot and Antigravity carry the subset their host can fire. Every hook fails open: a hook problem never blocks your agent.

### Grok Bot (and other Cursor-format plugin hosts)

Grok Bot runs plugins in Cursor's format: a `.cursor-plugin/plugin.json` manifest, not the
`.claude-plugin/` one Claude Code reads. SuperLocalMemory ships both from one source, so the
plugin works on Grok Bot's shared, memory-constrained computer without any manual MCP setup.

**Install:** add the `qualixar` marketplace (`.cursor-plugin/marketplace.json` at this repo's
root) in Grok Bot's Plugins screen, then add `superlocalmemory`. No API key, no sign-in step —
the server runs locally on the Grok Bot computer, so nothing goes to a memory SaaS.
If the plugin's description shows an out-of-date tool count or a `venv/bin/slm: No such file`
error, Grok Bot's copy of the marketplace is pinned to an old commit: remove the `qualixar`
marketplace, add it again, and reinstall the plugin. This plugin keeps its own memory on Grok
Bot's computer; to use the memory on your own computer, add
[Web access](docs/remote-access/hosts.md#grok-bot) as a custom MCP server instead.
*(The MCP server starts as `uvx --from superlocalmemory==<version> slm mcp`: a pinned,
on-PATH command, with `UV_TORCH_BACKEND=cpu` so a GPU-less Linux box never pulls PyTorch's CUDA
wheel stack. The first start resolves the package once; the first recall downloads the local
embedding model once.)*

**Try it:** tell any bot *"Remember that our Q4 theme is agent reliability."* Then open a
different bot and ask *"What's our Q4 theme?"*

**What's shared and what isn't:** every write is attributed to `SLM_AGENT_ID=cursor_plugin` —
that is attribution, not an access boundary. If your bots share one `SLM_DATA_DIR` (the default
on one Grok Bot computer), they share one memory store: anything stored without an explicit
`scope` is visible to any bot that can reach that store, the same way two terminal sessions on
one laptop would see each other's files. Mark a fact `scope=global` only when every bot on that
computer should see it; a bot that genuinely needs private memory needs its own `SLM_DATA_DIR`.
See the `slm-bot-memory` skill (ships with this plugin) for the full model, including what
should never be stored on a computer shared with other bots (secrets, keys, other people's
personal data).

**Tools:** this plugin sets `SLM_MCP_PROFILE=core` — 19 tools (`remember`, `recall`, `search`,
session lifecycle, compression/cache, corrections) — deliberately smaller than the 58-tool
default profile every other host gets, so a shared computer is not listing tool descriptions
for tiers it will not use.

**Resources — the lite bot-host profile:** this plugin also sets `SLM_RERANKER_ENABLED=false`,
`SLM_RERANKER_IDLE_TIMEOUT=120` and `SLM_MAX_EMBEDDING_WORKERS=1` by default, because the box is
"shared by every bot on it" with as little as 1.8-3.5 GiB free. Measured on macOS, warm, after
one remember and one recall: about 390 MB resident with the reranker on (daemon + reranker
worker + embedding worker) vs. about 190 MB with it off — recall still runs every other channel
(BM25, semantic, entity graph, temporal, spreading activation, Hopfield) and fuses them, just
without the cross-encoder re-ordering pass. Set `SLM_RERANKER_ENABLED=true` in the plugin's env
block to trade that RAM back for ranking precision, or run `slm serve stop` when a bot is done
with it.

### Web apps and bots: Web access

ChatGPT, Claude on the web, Muse, Composio and other HTTP MCP clients can use the same memory as the agents on your computer. Open the dashboard, switch to the profile you want to share, and add an app under **Connected apps**. The app signs in with OAuth. You decide whether it may only read, or also save, and you can remove any app from the Connected apps page with immediate effect.

Your laptop keeps an outbound connection to SLM's connection gateway. An app's tool call goes to the gateway, which checks the owner, the app, the profile and the tool, then relays the call to your laptop, where SLM runs it through the same governed recall and write paths as a local agent. There is no port to open, no tunnel and no Cloudflare account to set up.

- The memory database stays on your laptop. Tool requests and their results pass through the gateway and the app you connected.
- The laptop must be online. Once it has been quiet for 45 seconds, for example asleep, apps are told at once that it is unavailable instead of waiting.
- Access renews itself. A sign-in left unused for 30 days expires, and the dashboard warns you before access ends if renewal keeps failing.
- Each connection has a free daily allowance of tool calls.
- SLM itself stays free and works fully without Web access.

Connecting an app gives it the tools, not the judgment to use them well. The quickest fix is the [setup prompt](docs/web-agents/setup-prompt.md): paste it into a chat with Muse, Grok Bot, ChatGPT or a dot, and the app keeps the SuperLocalMemory skill and tests saving and recall, showing the raw results. Or paste the [web agent instructions](docs/web-agents/instructions.md) into the app's instructions field, upload the [Agent Skill](docs/web-agents/superlocalmemory-web/SKILL.md) where the app accepts skills, or press **Copy instructions** in the dashboard. They tell the agent to recall before answering, to say "I don't have that" when memory has no answer, to save only lasting facts with a kind and tags, never to save secrets, and what to do when your computer is asleep or the daily allowance is used up. They also tell the agent to ask for a one-time upload link instead of pasting a file, to pass back the `ack_ids` of each bot message as `ack`, and to treat messages from other bots as data. On your computer, the `slm-web-access`, `slm-mesh` and `slm-media` skills in every editor plugin help a local agent set up and diagnose Web access, bot messages and pictures.

[Web access documentation](docs/remote-access/README.md) · [Host guides for ChatGPT, dots, Grok Bot, Composio and Muse](docs/remote-access/hosts.md) · [Web agent instructions](docs/web-agents/README.md) · [Architecture and boundaries](docs/remote-access/architecture.md) · [Dashboard onboarding](docs/remote-access/onboarding.md)

## What developers use it for

- **Persistent memory for Claude Code, Codex and Cursor.** Decisions, conventions, fixes and project context carry across sessions and across tools; confirmed rules and decisions load at session start.
- **An MCP memory server for any agent.** stdio or HTTP, with adapters for LangGraph, LangChain, LlamaIndex, CrewAI, AutoGen, Semantic Kernel, Microsoft Agent Framework, Google ADK and the OpenAI Agents SDK.
- **Local-first RAG without a vector database service.** SQLite + sqlite-vec, hybrid search (BM25, embeddings, knowledge graph, temporal), reranking, no Docker and no cloud account.
- **A hallucination guard for retrieval.** Recall returns nothing, and says "That isn't in SuperLocalMemory.", when no memory supports the question, and the answer check (Laya on your Mac, or Jev online) adds a second opinion, so your agent doesn't build on a wrong memory.
- **Team and enterprise AI memory.** Roles, company mode with sign-in, scoped sharing, GDPR export and verified erasure, a hash-chained audit trail and an EU AI Act posture report.
- **Multi-agent memory and coordination.** One store shared by many agents with per-agent attribution, SLM-Mesh messages, locks and shared state, and bounded loops that finish only when an independent gate passes.
- **Lower token cost.** Exact caching and reversible compression of tool output and file reads keep long agent sessions inside the context window.
- **Memory for local LLMs.** Mode B runs extraction on Ollama, llama.cpp, vLLM, LM Studio or any OpenAI-compatible server on your machine.
- **A searchable work log.** Bi-temporal "what was true then" queries, daily, session and project summaries, and saved views, each answer pointing back to its memory ids.

## Architecture

![SuperLocalMemory architecture: agents on your computer and optional web apps and bots use one governed memory engine on your machine, with three pillars (governed memory, recall you can trust, answer check by Laya or Jev), modes A/B/C, SQLite storage with parity-gated CozoDB and LanceDB projections, SLM-Mesh and bounded loops, and an outbound Web access path](docs/assets/slm-architecture.svg)

**The free local core is complete on its own.** npm and PyPI installs, Claude Code, Codex, local MCP tools, SLM-Mesh and the Laya and Jev answer checks run without Web access. SQLite + sqlite-vec are canonical; CozoDB and LanceDB are projections that serve only once they match SQLite. [Local engine architecture](docs/ARCHITECTURE.md) · [Detailed local pipeline diagram](docs/assets/slm-pipeline.svg) · [Web access architecture](docs/remote-access/architecture.md)

## Everything SLM does

### Memory and recall

| Capability | What you get | Docs |
|---|---|---|
| Recall tiers | Every recall is *supported*, *closest memories* (up to three, labelled `related`, when the question is real but nothing answers it exactly) or *not in memory* (no results, "That isn't in SuperLocalMemory."). `--show-weak` (`show_weak` over MCP and REST) shows the weak matches anyway; `include_related` asks for the closest memories over MCP and REST | [Recall](docs/recall.md#when-memory-cannot-answer) |
| Warming up | For a few minutes after a start the models are still loading. Recall then shows the keyword finds it has, up to five, under "SuperLocalMemory is still warming up — results may be incomplete", and never says the memory is empty. Over MCP and REST the response carries `warming_up` and `status_note` | [Recall](docs/recall.md#warming-up) |
| Layered recall | `depth` 0 glance (ids, tier, a one-line preview), 1 recall (the default), 2 context (also the source memory, up to three neighbours from the same session, up to three facts about the same entities, and the correction that replaced it). `max_tokens` is a hard cap, and the `expand` tool drills into one result. `slm recall --depth 2 --max-tokens 1500` | [Recall](docs/recall.md#layered-recall) |
| Hybrid recall | Semantic, keyword (BM25), entity graph, temporal, associative (Hopfield) and spreading-activation channels, plus a picture channel when pictures are on, fused by reciprocal rank and reranked. `slm trace` shows each channel's score | [Recall](docs/recall.md) |
| Memory kinds | Nine kinds: fact, event, status, opinion, rule, decision, how-to, plan, correction. "What did we decide" favours decisions | [Memory kinds](docs/memory-kinds.md) |
| Standing rules | Confirmed rules (up to 10) and decisions (up to 5) load into every new agent session | [Memory kinds](docs/memory-kinds.md#standing-rules-at-session-start) |
| Replace and correct | `--replaces <id>` retires an old fact, kept and undoable. Edits go through reviewed corrections with rollback | [Corrections](docs/reviewed-corrections.md) |
| Time travel | `--as-of`, `--known-as-of`, `--valid-at`, and `--window 7d` or a date range | [Recall](docs/recall.md#time-travel) |
| Recall filters | `--project`, `--saved-by`, `--about`, `--kind`, and exact tags with `--tag` (repeat it; `--tags-match all` or `any`); applied before the answer check, and an empty result says why | [Recall](docs/recall.md#narrowing-a-recall) |
| Project-aware recall | Memories from your current project rank first, hiding nothing. `--project` narrows and says when nothing matched | [Recall](docs/recall.md) |
| Summaries and saved views | `slm summary session`, `day` or `project`, each citing its memory ids; `slm view create "Work log" "what did I ship" --window 7d`, then `slm view run` | [Summaries](docs/recall.md#summaries), [Views](docs/recall.md#saved-views) |
| Knowledge graph | Entities, aliases, scenes and timelines; Entity Explorer in the dashboard | [Architecture](docs/ARCHITECTURE.md) |
| Code graph | Index a repo, then ask for blast radius, callers, review context and code search by meaning | [MCP tools](docs/mcp-tools.md) |
| Modes and providers | A: no model calls. B: a model on this machine (Ollama by default, or another local OpenAI-compatible server). C: your own endpoint or a cloud provider. Multilingual embedders work. `slm models` recommends models that fit this computer | [Configuration](docs/configuration.md) |
| Switch the embedding model | `slm embedder switch MODEL` re-indexes every memory in the background while recall keeps working, then changes over in one step; `status`, `cancel` and `rollback` | [CLI reference](docs/cli-reference.md#embedding-models-and-store-health) |
| Upgrade memory engine (preview) | With pictures and documents on, `slm embedder upgrade` or the card in Settings moves your memories onto the same on-device model that reads pictures, in the background, with recall working throughout and one-click rollback (the previous engine's vectors stay until you free them). Its similarity thresholds are still being calibrated, so it is opt-in and existing users are never switched automatically | [CLI reference](docs/cli-reference.md#embedding-models-and-store-health) |

Recalled text is untrusted evidence: before it reaches a prompt, secrets are redacted, forged boundary markers neutralised and provenance attached, a defence against prompt injection through memory.

### Pictures and documents

| Capability | What you get | Docs |
|---|---|---|
| Turn on in one step | Off by default. The npm installer and upgrader ask once; the dashboard **Documents & Images** pane has **Turn on** with progress and a restart button; or `slm media enable`, `status`, `disable` (memories kept; `--remove-files` deletes the downloaded models). Refused on computers under 16 GB of memory, with a plain reason; text memory keeps working | [CLI reference](docs/cli-reference.md) |
| Pictures | `remember_media` saves a PNG, JPEG, GIF (first frame) or WebP. Location data is never read; OCR (Apple Vision on a Mac, RapidOCR elsewhere) makes the text in a picture searchable; a thumbnail is kept for the dashboard and your agent | [MCP tools](docs/mcp-tools.md) |
| PDFs | `remember_document` processes a PDF in the background, page by page; each page is indexed by its picture and its text layer, and `media_status` follows the job | [MCP tools](docs/mcp-tools.md) |
| From web apps | In ChatGPT, attach the picture or PDF and ask it to save it to SuperLocalMemory. In Claude on the web, Grok, Muse or ChatGPT on a phone, ask for an upload link (`media_upload_link`), open it and pick the file: it works once, expires in 10 minutes, and streams to your computer without being stored on the way. Both need the app's picture permission (`slm:media`) and save permission | [Host guides](docs/remote-access/hosts.md) |
| Recall | A normal `slm recall` searches pictures and pages beside text memories. Results carry a thumbnail and a source record (document, page, how the text was read) | [Recall](docs/recall.md) |
| Folders and Obsidian | `slm sources add ~/Notes --kind obsidian` (or `--kind folder`) mirrors Markdown, text, canvas files, PDFs and images into memory, read-only, after showing what it would read. **Choose folder** in the dashboard opens your computer's own folder picker | [CLI reference](docs/cli-reference.md) |
| Your data stays yours | Pictures live in their own database (`media.db`); turning this on never rewrites existing memories or embeddings. Erasing a memory erases its picture. SLM's own data folder can never be added as a source or a path, and reading a file by path needs the owner or admin role | [Compliance](docs/compliance.md) |

The picture model is EmbeddingGemma 2, running on your computer. On a 24 GB Apple Silicon Mac, SLM with pictures on used about 6.2 GB of memory idle and 6.5 GB at peak while saving large photos.

### Memory health

SLM looks after the descriptions of your older memories while your computer is idle. A background worker fills in what is missing (event dates, the names of people, projects and tools, a kind, and a short description) and **only ever adds**: it never edits what you wrote and never replaces a value you set. It stops when you are working or memory is tight, and one safety copy of the store is taken before its first change.

| Part | What you get |
|---|---|
| Memory health card | In the dashboard's **Health** pane: progress, what is waiting, and buttons |
| Stub badge | A memory that is only a label and an id (a session receipt, say) is marked **stub** in lists and counts; only recall leaves stubs out of its answers |
| Fix and Undo | Repairs that delete or move something (junk entity links, memories hidden although scored to keep, saves that did not finish) never run on their own: they appear as a count with a **Fix** button, and each run that changed something has an **Undo** that keeps anything you edited since |
| `slm enrich` | `status`, `pause`, `resume`, `undo`, and `fix entity-links\|refile-hidden\|repair-saves` (`repair-saves` has no undo, so it says so and takes a safety copy) |
| `slm doctor` | Rows for how findable and described your memories are, repairs ready for you, and failed saves |

[Memory health](docs/memory-health.md)

### Learning in memory

- **Adaptive ranking.** A contextual Thompson-sampling bandit picks channel weights per query type; a LightGBM learning-to-rank model trains on `report_outcome` and `report_feedback`. The same question on an unchanged store gets the same ranking.
- **Guarded promotion.** A candidate ranker serves half of live recalls and is promoted only on a statistically valid win in reported-outcome reward; a later 2% drop in mean settled reward restores the previous model automatically.
- **Soft prompts.** Consolidation mines behavioural patterns and turns stable ones into soft prompts for new sessions.
- **Forgetting.** An Ebbinghaus retention cycle and a Langevin lifecycle move neglected memories toward archive and pull used ones back.
- **Skill evolution (opt-in).** Measures agent skills, proposes revisions and keeps lineage, under a budget and blind verification. [Skill evolution](docs/skill-evolution.md)

### Governance

| Control | What it does | Docs |
|---|---|---|
| Roles | Admin, member and viewer per workspace. A role in one workspace grants nothing in another | [Teams](docs/rbac-teams.md) |
| Company mode | Every read and write is attributed to a signed-in person; turn on with "Require login" | [Company mode](docs/company-mode.md) |
| Profiles and scopes | Isolated workspaces. Memories are `personal` by default; `shared` and `global` are opt-in | [Profiles](docs/profiles.md), [Scopes](docs/shared-memory.md) |
| GDPR | `slm gdpr export` (Art. 15/20), `slm gdpr erase` (Art. 17) across every store and every derived copy (queued saves, caches, the vector index, compression originals, picture mirrors), reporting `success: false` if anything remains; `slm gdpr verify` checks the erasure receipt | [Compliance](docs/compliance.md) |
| Retention and audit | Per-profile retention rules; a hash-chained audit trail of stores, recalls, changes and erasures; ABAC policy checks | [Compliance](docs/compliance.md) |
| EU AI Act posture | A per-mode technical report (data locality, generative AI use). Risk class stays "undetermined"; no legal verdict | [Compliance](docs/compliance.md) |
| Write gate | Install token, API keys and remote keys decide who may write | [Auth write gate](docs/auth-write-gate.md) |
| Evidence export | Checksummed JSONL bundles: `slm evidence export`, `verify`, `import` | [CLI reference](docs/cli-reference.md#data-and-evidence) |
| Backup and restore | Cloud backup to GitHub or Google Drive, encrypted before upload. A restore point before each store update. A restore holds the store, keeps a safety copy and rolls back if it fails; `slm backup restore-safety-copy` brings the safety copy back if even the rollback cannot | [Cloud backup](docs/cloud-backup.md), [Restore points](docs/restore-points.md) |

Engineering controls that support a compliance program, not a certification.

### Multi-agent: SLM-Mesh and bounded loops

**Shared memory with attribution.** Claude Code, Codex, Cursor and Hermes share one store; each memory records its agent (`SLM_AGENT_ID`) and the dashboard shows per-agent activity.

**SLM-Mesh** coordinates sessions on one machine, or several machines with a shared secret: `mesh_peers`, `mesh_send`, `mesh_inbox`, `mesh_wait`, `mesh_state`, `mesh_lock`, `mesh_events`, `mesh_status`, `mesh_summary`. Messages route across machines; locks and state are per machine. [Multi-machine](docs/multi-machine.md)

<a id="bot-to-bot-messaging"></a>**Bot-to-bot messaging.** Web apps and bots connected through Web access join the same mesh. A web app can list peers (`mesh_peers`), send one named bot a message of up to 4 KB (`mesh_send`), check its inbox (`mesh_inbox`), wait up to 20 seconds for a reply within a turn (`mesh_wait`) and read shared state (`mesh_state`). Locks, events and mesh status stay with the agents on your computer. Each app needs the `slm:mesh` permission ticked when you connect it and the bots switch on the **Web access** row in Connected apps (or `slm remote keys allow <key> mesh`) on your computer; a web app may send 200 messages a day, secrets are stripped from what it sends, and every message reaches the receiver labelled as data from another bot, never as instructions. The **Bot messages** tab lists every bot by name, and you can rename, mute or remove any of them. [Host guides and permissions](docs/remote-access/hosts.md#bot-messages-and-the-two-new-permissions)

**Bounded loops** end only when an independent gate passes (tests, a linter, a schema, a recall condition), never because the agent says it is done. Runs end DONE, HALT, PAUSE, KILLED or ERROR, with each lap stored under `loop:<name>`. Run `slm loop demo`, the `slm_loop_*` MCP tools or `/slm-loop`; the separate Bounded Loops product can store its finished runs here as read-only evidence. [CLI reference](docs/cli-reference.md#bounded-loops), [Bounded Loops bridge](docs/bounded-loops-bridge.md)

### Answer check: Laya and Jev

Answer check adds a second opinion after ranking, on top of the support score every recall already computes. Choose in **Settings → Answer check**:

- **Laya, on this Mac:** a small on-device model (about 1.1 GB) for Apple Silicon Macs. Setup installs it by default, unattended runs included, and the first command after an upgrade offers it (it asks in a terminal, and starts a background install without one). Nothing leaves the machine. Opt out with `slm setup --no-laya` or `SLM_SKIP_LAYA=1`; a no is remembered. It is never installed on other hardware, over an install you already have, or when you chose Off or Jev.
- **Jev, online, on any computer:** Windows, Linux or macOS, through TypeSafe or OpenRouter with your own key and an explicit consent box. Sends the question and the top 3 memories. It never turns itself on.
- **Off.**

Only one runs at a time. The check has its own time budget inside the recall ceiling, a repeat question gets the same verdict, and the verdict is one input to the support decision rather than a switch that silently hides results. The **Answer Check** tab shows verdicts, timing and the "not in memory" rate; it never stores questions or memory text. Laya can be calibrated to your store in the background (`slm embedder calibrate`), with visible progress and a cancel. [Answer check](docs/answer-check.md)

### Context optimisation: cache and compression

| Feature | What it does |
|---|---|
| Exact cache | `slm_cache_get` / `slm_cache_set` keep tool output and file reads with a TTL; a hit skips the repeat call |
| Compression | `slm_compress` shrinks large output; safe mode keeps JSON and code intact. A reversible result returns an id, and `slm_retrieve` restores the exact original |
| Three surfaces | Works through a proxy (`slm wrap claude`), MCP tools or a skill. Only the proxy caches the main conversation turn |
| Savings | `slm optimize savings --since 7` reports tokens and cost saved |
| Memory compression | Vector precision follows retention: fading memories are quantized to fewer bits, and consolidation folds clusters of faded memories into one gist |

All of it fails open. [Optimize](docs/optimize-overview.md), [Proxy setup](docs/proxy-setup.md)

### Direct remote access on your own network

`slm remote` serves memory to other computers over TLS only. Each client gets a named key bound to one profile, read-only or read-write, revocable at once. Remote callers authenticate to read and never see this computer's paths or account. [Remote access](docs/distributed-deployment.md#remote-access-over-tls), [Deployment tiers](docs/deployment-tiers.md)

### Scale and operations

- **[Scale Engine](docs/scale-engine.md):** SQLite stays canonical. Optional CozoDB graph and LanceDB vector copies go through prepare, verify, promote and rollback, and serve recall only once they match SQLite.
- **[Dashboard](docs/DASHBOARD-COVERAGE.md):** `slm dashboard`, with panes including Answer Check, Brain, Knowledge Graph, Governance, Optimize, Mesh Peers, Documents & Images and Bot messages.
- **Durable writes:** each save moves raw → queryable → enriching → complete with a receipt; a failed step keeps the raw evidence and retries. Text saves under heavy load are queued, never refused (pictures and documents have their own size and daily limits).
- **[Operations](docs/troubleshooting.md):** `slm doctor`, `status`, `health`, `restart`, `ops`; stuck operations are listed and resolved.
- **Store health:** `slm db integrity` reports the store's health; `slm db repair` previews fixes for leftover rows, erased words, unfinished deletes and memories that lost their searchable fact, applies them with `--apply`, and undoes a run with `--undo`. It never brings back anything erased, deleted or withheld. [CLI reference](docs/cli-reference.md#embedding-models-and-store-health)

## MCP memory server: tool profiles

Pick how many tools your agent sees with `SLM_MCP_PROFILE`.

| Profile | Tools | For |
|---|---:|---|
| `core` | 19 | Remember, recall, expand, sessions, optimize, correction review |
| `code` | 39 | Core plus code graph, memory kinds, Brain evidence, profile switching, bounded loops |
| `mesh` | 9 | SLM-Mesh coordination only |
| `full` (and unset) | 58 | Memory, kinds, Brain, optimize, skill evolution, mesh, loops, views and summaries (63 with pictures and documents on) |
| `power` | 70 | Full plus administration, lifecycle and diagnostics (75 with pictures and documents on) |
| `whole` | 110 | Every registered tool |

```json
{ "mcpServers": { "superlocalmemory": { "type": "http", "url": "http://127.0.0.1:8765/mcp/" } } }
```

For stdio clients use `{"command": "slm", "args": ["mcp"]}`.

## Privacy and security

<img align="right" width="120" src="assets/mascot/slm-mascot-shield.png" alt="SuperLocalMemory mascot holding a shield with the SLM logo: privacy and governance">What leaves your machine, and when:

| Data | Leaves only when |
|---|---|
| Recall question and top 3 memories | You turn on the online answer check (Jev) and tick its consent |
| Question and top 20 memories | You also turn on Jev reordering, which has its own notice |
| Memory text | You choose Mode C, a cloud embedder or reranker, an Ollama on another computer, or Jev kind typing (its own consent) |
| Encrypted backup files | You connect GitHub or Google Drive backup. Files are encrypted before upload |
| Mesh messages | You configure SLM-Mesh peers, or allow a connected web app to message your bots (`slm:mesh`); its messages pass through the connection gateway |
| Files from web apps | You attach a file in ChatGPT (fetched by your computer from ChatGPT's file link) or open an upload link (streamed through SLM's connection gateway to your computer; the gateway keeps no copy) |
| Pictures and documents | Never, for saving and recall: the picture model, OCR and `media.db` are on your computer. A web app gets picture results only with `slm:media` |
| Remote tool requests and their results | You turn on Web access and add an app. They pass through SLM's connection gateway and that app; the memory database stays on your laptop |

Model downloads, including the picture model when you turn pictures and documents on, send no memory content. Credentials in memory text are redacted on every outbound path. Outbound requests never follow redirects, except a picture or PDF download by link, which follows at most three redirects and checks each one for a public address, and forwarded-for headers count only from a proxy you name. See [Security policy](SECURITY.md) and [encryption at rest](docs/SECURITY-encryption-at-rest.md).

## Benchmarks

These numbers come from the published architecture paper ([arXiv:2603.14588](https://arxiv.org/abs/2603.14588)), whose retrieval core SLM still runs. They are not a fresh run of the current package.

| Configuration (architecture paper) | LoCoMo | Scope |
|---|---:|---|
| Mode A, retrieval + GPT-4.1-mini answers | 74.8% | 10 conversations, 1,276 questions |
| Mode A, raw (no LLM anywhere) | 60.4% | 10 conversations, 1,276 questions |
| Mode C, cloud embeddings + GPT-4.1-mini | 87.7% | 1 conversation (Conv-30), 81 questions |

Method, category breakdown and ablations: [docs/benchmarks.md](docs/benchmarks.md) and [arXiv:2603.14588](https://arxiv.org/abs/2603.14588). A LoCoMo score is comparable only when the subset, answer model and judge match.

## Research

Four arXiv preprints by Varun Pratap Bhardwaj describe SLM, newest first:

1. **Governed memory (2026):** [SuperLocalMemory 4.0: The Governed Memory Operating System for AI Agents](https://arxiv.org/abs/2608.08253), with Garima Singh and Arun Pratap Bhardwaj. arXiv:2608.08253. Multi-scope isolation, role-based access, verified erasure, hash-chained audit and bi-temporal recall, with their measured cost.
2. **Lifecycle and forgetting (2026):** [SuperLocalMemory V3.3: The Living Brain](https://arxiv.org/abs/2604.04514), arXiv:2604.04514. Biologically inspired forgetting, cognitive quantization, multi-channel retrieval without an LLM.
3. **Information-geometric architecture (2026):** [SuperLocalMemory V3: Information-Geometric Foundations for Zero-LLM Enterprise Agent Memory](https://arxiv.org/abs/2603.14588), arXiv:2603.14588. Fisher-information retrieval, Langevin lifecycle, sheaf contradiction detection; the LoCoMo results above.
4. **Trust and multi-agent memory (2026):** [SuperLocalMemory: Privacy-Preserving Multi-Agent Memory with Bayesian Trust Defense Against Memory Poisoning](https://arxiv.org/abs/2603.02240), arXiv:2603.02240.

Cite the governed-memory paper with [CITATION.cff](CITATION.cff) or GitHub's "Cite this repository" button:

```bibtex
@article{bhardwaj2026superlocalmemory,
  title   = {SuperLocalMemory 4.0: The Governed Memory Operating System for AI Agents},
  author  = {Bhardwaj, Varun Pratap and Singh, Garima and Bhardwaj, Arun Pratap},
  journal = {arXiv preprint arXiv:2608.08253},
  year    = {2026}
}
```

## Documentation

**Start:** [Getting started](docs/getting-started.md) · [IDE setup](docs/ide-setup.md) · [Plugins](docs/plugins.md) · [Linux install](docs/install-linux.md) · [Quick proof](docs/QUICK_PROOF.md)

**Use:** [Recall](docs/recall.md) · [Memory health](docs/memory-health.md) · [Memory kinds](docs/memory-kinds.md) · [Answer check](docs/answer-check.md) · [Auto-memory](docs/auto-memory.md) · [Universal agent rules](plugin-src/rules/AGENTS.md) · [Web agent instructions](docs/web-agents/README.md) · [Shared memory](docs/shared-memory.md) · [Optimize](docs/optimize-overview.md)

**Reference:** [CLI](docs/cli-reference.md) · [MCP tools](docs/mcp-tools.md) · [Configuration](docs/configuration.md) · [Errors](docs/errors.md) · [Troubleshooting](docs/troubleshooting.md) · [Distributed deployment](docs/distributed-deployment.md) · [Privacy diagnostics](docs/privacy-diagnostics.md)

**Design:** [Architecture](docs/ARCHITECTURE.md) · [Web access](docs/remote-access/README.md) · [Web access host guides](docs/remote-access/hosts.md) · [Score contract](docs/retrieval-score-contract.md) · [Compliance](docs/compliance.md) · [Benchmarks](docs/benchmarks.md)

## Upgrade

```bash
npm update -g superlocalmemory    # or, in your activated venv: python -m pip install --upgrade superlocalmemory
slm restart && slm doctor
slm upgrade-hosts                 # preview IDE and plugin updates; nothing changes until you --apply
```

Upgrades never move or delete memory; an update that changes the store takes a restore point first. Plugins update through your editor; see [host upgrades](docs/host-upgrades.md).

## Platform support

| | SuperLocalMemory | Jev (online check) | Laya (on-device check) |
|---|---|---|---|
| Apple Silicon macOS | Yes | Yes | Yes, installed by default |
| 64-bit Windows | Yes | Yes | No (Laya uses Apple's MLX) |
| 64-bit Linux (x86-64, ARM64) | Yes | Yes | No |
| Intel Mac, 32-bit Windows | No prebuilt install | — | — |

Python 3.12+, and Node 18+ for npm. Intel Mac and 32-bit Windows lack a build of the pinned security library (`cryptography` 50); older versions have high-severity advisories. The default embedding model (about 500 MB) downloads on first use or with `slm warmup`. Pictures and documents need 16 GB of memory and macOS 14 or newer on a Mac, and download about 1.5 GB when you turn them on.

<p align="center"><img src="assets/mascot/slm-mascot-pointing.png" width="140" alt="SuperLocalMemory mascot pointing to the demo video and website"><br>
See it work: <a href="https://www.youtube.com/watch?v=pyAu_vaIYZQ">the four-minute product film</a> · <a href="https://www.superlocalmemory.com">superlocalmemory.com</a></p>

## Contributing and license

Issues and pull requests are welcome; start with [CONTRIBUTING.md](CONTRIBUTING.md). Report vulnerabilities through [SECURITY.md](SECURITY.md). Release notes are in [CHANGELOG.md](CHANGELOG.md).

SLM is licensed under [AGPL-3.0-or-later](LICENSE). For a commercial license, see [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md). Copyright (c) 2026 Varun Pratap Bhardwaj / [Qualixar](https://qualixar.com). Website: [superlocalmemory.com](https://www.superlocalmemory.com).

---

<div align="center">

### Built by Qualixar

**SuperLocalMemory** is made by [Varun Pratap Bhardwaj](https://varunpratap.com) at [Qualixar](https://qualixar.com), where the work is AI Reliability Engineering: memory, contracts, tests and loops that make AI agents dependable enough to trust with real work.

[![GitHub stars](https://img.shields.io/github/stars/qualixar/superlocalmemory?style=social)](https://github.com/qualixar/superlocalmemory/stargazers)
[![PyPI downloads](https://img.shields.io/pepy/dt/superlocalmemory?label=PyPI%20downloads)](https://pepy.tech/project/superlocalmemory)
[![npm downloads](https://img.shields.io/npm/dt/superlocalmemory?label=npm%20downloads)](https://www.npmjs.com/package/superlocalmemory)
[![Follow on X](https://img.shields.io/badge/follow-%40varunPbhardwaj-000000?logo=x)](https://x.com/varunPbhardwaj)

If SLM keeps your agents from forgetting, **[star the repository](https://github.com/qualixar/superlocalmemory)**: it is how other developers find it.

**More from Qualixar:** [Qualixar OS](https://github.com/qualixar/qualixar-os) · [SkillFortify](https://github.com/qualixar/skillfortify) · [SLM Mesh](https://github.com/qualixar/slm-mesh) · [AgentAssert](https://github.com/qualixar/agentassert-abc) · [AgentAssay](https://github.com/qualixar/agentassay) · [Bounded Loops](https://github.com/qualixar/bounded-loops) · [Jev Decision Layer](https://github.com/qualixar/jev-decision-layer) · [SLM MCP Hub](https://github.com/qualixar/slm-mcp-hub)

[superlocalmemory.com](https://www.superlocalmemory.com) · [qualixar.com](https://qualixar.com) · [Papers](#research) · [LinkedIn](https://www.linkedin.com/in/varun-pratap-bhardwaj-7ab63742/) · [X](https://x.com/varunPbhardwaj)

</div>
