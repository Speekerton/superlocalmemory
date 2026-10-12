<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/assets/branding/slm-wordmark-dark.svg">
  <img src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/assets/branding/slm-wordmark-light.svg" alt="SuperLocalMemory" width="380">
</picture>

<p align="center"><img src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/assets/mascot/slm-mascot-hero.png" width="180" alt="SuperLocalMemory mascot, a fluffy caped helper with the SLM logo, arms open"></p>

### Memory for AI agents that knows when it doesn't know.

**One private memory that lives on your machine, for every agent you use.** Claude Code, Codex, Cursor, Copilot, ChatGPT and any MCP client remember together, and when the answer isn't there, SuperLocalMemory says so instead of feeding your agent a confident guess. In Mode A, core remember and recall make no model-provider call. Anything that sends data out is a choice you make.

[![PyPI](https://img.shields.io/pypi/v/superlocalmemory)](https://pypi.org/project/superlocalmemory/)
[![npm](https://img.shields.io/npm/v/superlocalmemory)](https://www.npmjs.com/package/superlocalmemory)
[![PyPI downloads](https://img.shields.io/pepy/dt/superlocalmemory?label=PyPI%20downloads)](https://pepy.tech/project/superlocalmemory)
[![npm downloads](https://img.shields.io/npm/dt/superlocalmemory?label=npm%20downloads)](https://www.npmjs.com/package/superlocalmemory)
[![GitHub stars](https://img.shields.io/github/stars/qualixar/superlocalmemory?style=flat&logo=github)](https://github.com/qualixar/superlocalmemory/stargazers)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue)](https://github.com/qualixar/superlocalmemory/blob/main/LICENSE)
[![Research: 4 arXiv papers](https://img.shields.io/badge/arXiv-4_papers-b31b1b)](#research)

**[Install](#install-in-a-minute)** · **[What's new in 4.2](#whats-new-in-42)** · **[Demo video](https://www.youtube.com/watch?v=pyAu_vaIYZQ)** · **[Docs](#documentation)** · **[Website](https://www.superlocalmemory.com)**

<img src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/docs/assets/gifs/recall-tiers.gif" alt="Recall in the dashboard: a real question gets its answer; a gibberish question gets 'That isn't in SuperLocalMemory.'; a real question memory cannot answer exactly gets the closest memories, labelled" width="820">

</div>

## Install in a minute

```bash
npm install -g superlocalmemory   # or: pipx install superlocalmemory   (Python 3.12+, Node 18+ for npm)
slm setup                         # pick Mode A to keep everything on this machine
slm connect cursor                # or codex, windsurf, zed, claude-desktop, jetbrains ... (Claude Code uses the plugin)
```

npm installs SLM into a package-owned virtual environment; pipx does the same. Prefer pip? `python -m pip install superlocalmemory` inside a Python virtual environment you activate. Repository clone: `./scripts/install.sh install` (macOS, Linux) or `.\scripts\install.ps1 -Action Install` (Windows). Claude Code: `claude plugin install superlocalmemory@qualixar` ([Works with your agents](#works-with-your-agents)).

Windows, Linux and Apple Silicon macOS. [Getting started](https://github.com/qualixar/superlocalmemory/blob/main/docs/getting-started.md) · [Platform support](#platform-support)

## 30-second example

```console
$ slm remember "We deploy the API blue-green; rollback is a DNS flip." --kind decision
$ slm recall "how do we roll back the API"
  1. [0.67] We deploy the API blue-green; rollback is a DNS flip.
$ slm recall "zxqv plorth wimble"
  That isn't in SuperLocalMemory.
```

Scores rank memories; they are not probabilities.

## Why it's different

| | |
|---|---|
| **It admits what it doesn't know** | Every recall is *supported*, *closest memories* (clearly labelled) or *"That isn't in SuperLocalMemory."* Your agent never builds on a memory that doesn't answer the question. |
| **It runs on your computer** | No cloud account, no API key, no Docker. In Mode A nothing leaves your machine and no language model is called. |
| **It's governed, not just stored** | Every save gets a receipt, every read respects roles and workspaces, every erasure is provable, every action is in a hash-chained audit trail. |
| **It looks after itself** | Memory health describes your older memories in the background, only ever by adding, with Fix and Undo for anything bigger. |
| **It never floods your context** | Layered recall returns a glance, the facts, or the full context, under a hard token budget. Your agent asks for more only when it needs it. |
| **It's built on published research** | Four arXiv papers: information-geometric retrieval, biologically inspired forgetting, trust against memory poisoning, and governed memory. |

## What's new in 4.2

| | |
|---|---|
| **Recall that knows when it doesn't know** | Three tiers: an answer, the closest memories under "I don't have this exactly", or "That isn't in SuperLocalMemory." While SLM is still starting it says it is warming up and shows what it has, never "empty". [How recall decides](https://github.com/qualixar/superlocalmemory/blob/main/docs/recall.md#when-memory-cannot-answer) |
| **Layered recall** | `depth` 0 (one-line previews), 1 (the facts), 2 (with source, neighbours and corrections), a hard `max_tokens` cap, and `expand` to dig into one result. [Layered recall](https://github.com/qualixar/superlocalmemory/blob/main/docs/recall.md#layered-recall) |
| **On-device answer check by default** | Laya, a small model on Apple Silicon, judges whether the memories found actually answer the question. Installed by default, nothing leaves the Mac; opt out with `slm setup --no-laya`. [Answer check](https://github.com/qualixar/superlocalmemory/blob/main/docs/answer-check.md) |
| **Memory health** | Older memories get their dates, names, tags and kinds filled in while your computer is idle, without touching what you wrote. Repairs that move or delete anything wait for your Fix, and Undo puts them back. [Memory health](https://github.com/qualixar/superlocalmemory/blob/main/docs/memory-health.md) |
| **Erasure that reaches every copy** | GDPR erasure now removes derived copies too: summaries, personas, scene titles, caches and indexes. [Compliance](https://github.com/qualixar/superlocalmemory/blob/main/docs/compliance.md) |
| **Safer backup and restore** | A restore keeps a safety copy and rolls back on failure, with plain "wait" or "recover" messages. [Restore points](https://github.com/qualixar/superlocalmemory/blob/main/docs/restore-points.md) |
| **Workspace governance everywhere** | Maintenance, consolidation and skill approvals act only on the workspace you're in. [Teams](https://github.com/qualixar/superlocalmemory/blob/main/docs/rbac-teams.md) |

All changes: [CHANGELOG](https://github.com/qualixar/superlocalmemory/blob/main/CHANGELOG.md)

## Works with your agents

Any harness that speaks MCP (`slm mcp`, or `http://127.0.0.1:8765/mcp/`) or can run a command (`slm remember`, `slm recall`) can use SuperLocalMemory. The packaged plugins below are ready-made examples, not a limit.

| Host | Connect | You get |
|---|---|---|
| **Claude Code** | `claude plugin marketplace add qualixar/superlocalmemory` then `claude plugin install superlocalmemory@qualixar` | MCP, 16 skills, 4 agents, `/slm-loop`, session hooks |
| **Codex** | `slm connect codex` then `slm codex install` | MCP, skills, agents, hooks |
| **GitHub Copilot** | `slm connect vscode-copilot --here` | MCP, prompts, agents, hooks |
| **Antigravity, Hermes** | Native plugins | MCP, skills, agents, commands |
| **Cursor, Windsurf, Zed, JetBrains, Gemini CLI, Claude Desktop, OpenCode, Continue** | `slm connect <name>` | MCP |
| **Grok Bot and other Cursor-format hosts** | Add the `qualixar` plugin marketplace | A bot-sized plugin for shared computers ([guide](https://github.com/qualixar/superlocalmemory/blob/main/docs/plugins.md#grok-bot-and-other-cursor-format-hosts)) |
| **ChatGPT, Claude on the web, Muse, Composio** | Optional Web access from the dashboard: sign in per app, read-only or read-and-save | Your local memory, from the web ([guide](https://github.com/qualixar/superlocalmemory/blob/main/docs/remote-access/README.md)) |
| **LangGraph, LangChain, LlamaIndex, CrewAI, AutoGen, Semantic Kernel, Microsoft Agent Framework, Google ADK, OpenAI Agents** | Framework adapters | Memory in your code ([adapters](https://github.com/qualixar/superlocalmemory/blob/main/docs/framework-adapters.md)) |
| **Anything else** | Paste the [universal agent rules](https://github.com/qualixar/superlocalmemory/blob/main/plugin-src/rules/AGENTS.md) and give it the CLI or MCP | Memory discipline for any agent |

Details: [plugins](https://github.com/qualixar/superlocalmemory/blob/main/docs/plugins.md), [IDE setup](https://github.com/qualixar/superlocalmemory/blob/main/docs/ide-setup.md), [MCP tool profiles](#mcp-memory-server-tool-profiles).

## Everything SLM does

| Area | What you get | Docs |
|---|---|---|
| **Recall** | Semantic, keyword, entity-graph, temporal, associative and picture channels, fused and reranked; filters by project, kind, tag, agent and time; nine memory kinds; standing rules at session start | [Recall](https://github.com/qualixar/superlocalmemory/blob/main/docs/recall.md), [Memory kinds](https://github.com/qualixar/superlocalmemory/blob/main/docs/memory-kinds.md) |
| **Time** | Every fact knows when it happened and when SLM learned it: `--valid-at`, `--known-as-of`, `--window 7d`. Corrections replace a fact and stay undoable | [Recall](https://github.com/qualixar/superlocalmemory/blob/main/docs/recall.md#time-travel), [Corrections](https://github.com/qualixar/superlocalmemory/blob/main/docs/reviewed-corrections.md) |
| **Pictures and documents** | Find a screenshot, photo or PDF page by describing it. A picture model and OCR on your computer; nothing leaves it. Off by default, one click to turn on (16 GB memory) | [Pictures and documents](https://github.com/qualixar/superlocalmemory/blob/main/docs/pictures-and-documents.md) |
| **Folders and Obsidian** | Mirror a folder or vault into memory, read-only: `slm sources add ~/Notes --kind obsidian` | [CLI](https://github.com/qualixar/superlocalmemory/blob/main/docs/cli-reference.md) |
| **Knowledge graph** | People, projects and tools resolved from your memories, with timelines; a code graph for blast radius and callers | [Architecture](https://github.com/qualixar/superlocalmemory/blob/main/docs/ARCHITECTURE.md) |
| **Learning** | Opt-in adaptive ranking that is promoted only on a statistically valid win and rolled back if it gets worse; forgetting curves; soft prompts; opt-in skill evolution | [Skill evolution](https://github.com/qualixar/superlocalmemory/blob/main/docs/skill-evolution.md) |
| **Governance** | Roles per workspace, company mode with sign-in, personal / shared / global scopes, hash-chained audit, retention rules, GDPR export and verified erasure, an EU AI Act posture report | [Teams](https://github.com/qualixar/superlocalmemory/blob/main/docs/rbac-teams.md), [Compliance](https://github.com/qualixar/superlocalmemory/blob/main/docs/compliance.md) |
| **Many agents, one memory** | Every write is attributed to its agent, with trust scores against memory poisoning. SLM-Mesh gives sessions messages, locks and shared state; connected web apps and bots can message each other | [Multi-machine](https://github.com/qualixar/superlocalmemory/blob/main/docs/multi-machine.md), [Bot messages](https://github.com/qualixar/superlocalmemory/blob/main/docs/remote-access/hosts.md#bot-messages-and-the-two-new-permissions) |
| **Bounded loops** | "Done" means an independent gate passed (tests, a linter, a schema), never the agent's word; every lap is stored | [Bounded loops](https://github.com/qualixar/superlocalmemory/blob/main/docs/bounded-loops-bridge.md) |
| **Context savings** | Exact cache and reversible compression of tool output, through a proxy (`slm wrap claude`), MCP tools or a skill; `slm optimize savings` shows what you saved | [Optimize](https://github.com/qualixar/superlocalmemory/blob/main/docs/optimize-overview.md) |
| **Backup** | Cloud backup to GitHub or Google Drive, encrypted before upload; a restore point before every store update | [Cloud backup](https://github.com/qualixar/superlocalmemory/blob/main/docs/cloud-backup.md) |
| **Dashboard** | Search, knowledge graph, answer check, Memory health, connected apps, bot messages, governance: `slm dashboard` | [Dashboard](https://github.com/qualixar/superlocalmemory/blob/main/docs/DASHBOARD-COVERAGE.md) |
| **Modes** | A: no language model. B: a model on this machine (Ollama or any local server). C: your own endpoint or a cloud provider | [Configuration](https://github.com/qualixar/superlocalmemory/blob/main/docs/configuration.md) |
| **Scale and operations** | SQLite canonical, optional LanceDB and CozoDB copies that serve only when they match; `slm doctor`, store integrity and repair with undo; durable writes with receipts | [Scale engine](https://github.com/qualixar/superlocalmemory/blob/main/docs/scale-engine.md), [Troubleshooting](https://github.com/qualixar/superlocalmemory/blob/main/docs/troubleshooting.md) |

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

stdio: `{"command": "slm", "args": ["mcp"]}` · HTTP: `http://127.0.0.1:8765/mcp/` · [MCP tools](https://github.com/qualixar/superlocalmemory/blob/main/docs/mcp-tools.md)

## See it

| Memory health: Fix and Undo | Knowledge graph |
|---|---|
| <img src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/docs/assets/gifs/memory-health.gif" alt="Memory health card: hidden memories that are still in use are fixed with one click, and Undo restores exactly what changed"> | <img src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/docs/assets/gifs/knowledge-graph.gif" alt="Knowledge graph: nodes settle into clusters, a click on a person shows the memory behind it"> |
| **Entity Explorer** | **The answer check at work** |
| <img src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/docs/assets/gifs/entities.gif" alt="Entity Explorer: projects and tools with their facts and timeline"> | <img src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/docs/screenshots/dashboard/answer-check-answered.png" alt="Answer Check: the on-device model judges that the memories answer the question, with its confidence and timing"> |

Recorded on a test install with fictional memories. Prefer video? [The four-minute product film](https://www.youtube.com/watch?v=pyAu_vaIYZQ).

## Architecture

<img src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/docs/assets/slm-architecture.png" alt="SuperLocalMemory architecture: agents and apps reach one daemon on your computer through MCP, the CLI, the REST API and optional Web access; recall runs channels, fusion and reranking, the answer-support gate with three tiers, the on-device answer check and layered output; saves are admission-checked and redacted; SQLite is canonical with LanceDB and CozoDB copies and a separate store for pictures; Memory health and consolidation run in the background; roles, audit and erasure govern every call; SLM-Mesh connects agents" width="900">

The free local core is complete on its own; Web access is optional. [Architecture in detail](https://github.com/qualixar/superlocalmemory/blob/main/docs/ARCHITECTURE.md)

## Privacy

<img align="right" width="110" src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/assets/mascot/slm-mascot-shield.png" alt="SuperLocalMemory mascot holding a shield: privacy and governance">

Nothing leaves your computer unless you choose a feature that sends it, and each one says exactly what goes:

| What leaves | Only when |
|---|---|
| A question and the top memories | You turn on Jev, the online answer check, and tick its consent |
| Memory text | You choose Mode C, a cloud embedder, or a model on another computer |
| Encrypted backup files | You connect GitHub or Google Drive backup |
| Tool calls from web apps | You turn on Web access and add an app; the database stays on your computer |

Pictures, documents, Laya and Mode A never send anything. Secrets in memory text are redacted on every outbound path. [Security policy](https://github.com/qualixar/superlocalmemory/blob/main/SECURITY.md)

## Benchmarks

These numbers come from the published architecture paper ([arXiv:2603.14588](https://arxiv.org/abs/2603.14588)), whose retrieval core SLM still runs. They are not a fresh run of the current package.

| Configuration (architecture paper) | LoCoMo | Scope |
|---|---:|---|
| Mode A, retrieval + GPT-4.1-mini answers | 74.8% | 10 conversations, 1,276 questions |
| Mode A, raw (no LLM anywhere) | 60.4% | 10 conversations, 1,276 questions |
| Mode C, cloud embeddings + GPT-4.1-mini | 87.7% | 1 conversation (Conv-30), 81 questions |

A LoCoMo score is comparable only when the subset, answer model and judge match. [Method and ablations](https://github.com/qualixar/superlocalmemory/blob/main/docs/benchmarks.md)

## Research

Four arXiv preprints by Varun Pratap Bhardwaj describe SLM:

1. [SuperLocalMemory 4.0: The Governed Memory Operating System for AI Agents](https://arxiv.org/abs/2608.08253), arXiv:2608.08253
2. [SuperLocalMemory V3.3: The Living Brain](https://arxiv.org/abs/2604.04514), arXiv:2604.04514
3. [SuperLocalMemory V3: Information-Geometric Foundations for Zero-LLM Enterprise Agent Memory](https://arxiv.org/abs/2603.14588), arXiv:2603.14588
4. [Privacy-Preserving Multi-Agent Memory with Bayesian Trust Defense Against Memory Poisoning](https://arxiv.org/abs/2603.02240), arXiv:2603.02240

Cite with [CITATION.cff](https://github.com/qualixar/superlocalmemory/blob/main/CITATION.cff) or GitHub's "Cite this repository".

## Documentation

**Start:** [Getting started](https://github.com/qualixar/superlocalmemory/blob/main/docs/getting-started.md) · [IDE setup](https://github.com/qualixar/superlocalmemory/blob/main/docs/ide-setup.md) · [Plugins](https://github.com/qualixar/superlocalmemory/blob/main/docs/plugins.md) · [Quick proof](https://github.com/qualixar/superlocalmemory/blob/main/docs/QUICK_PROOF.md)
**Use:** [Recall](https://github.com/qualixar/superlocalmemory/blob/main/docs/recall.md) · [Memory health](https://github.com/qualixar/superlocalmemory/blob/main/docs/memory-health.md) · [Answer check](https://github.com/qualixar/superlocalmemory/blob/main/docs/answer-check.md) · [Auto-memory](https://github.com/qualixar/superlocalmemory/blob/main/docs/auto-memory.md) · [Web access](https://github.com/qualixar/superlocalmemory/blob/main/docs/remote-access/README.md) · [Optimize](https://github.com/qualixar/superlocalmemory/blob/main/docs/optimize-overview.md)
**Reference:** [CLI](https://github.com/qualixar/superlocalmemory/blob/main/docs/cli-reference.md) · [MCP tools](https://github.com/qualixar/superlocalmemory/blob/main/docs/mcp-tools.md) · [Configuration](https://github.com/qualixar/superlocalmemory/blob/main/docs/configuration.md) · [Troubleshooting](https://github.com/qualixar/superlocalmemory/blob/main/docs/troubleshooting.md) · [Compliance](https://github.com/qualixar/superlocalmemory/blob/main/docs/compliance.md) · [Wiki](https://github.com/qualixar/superlocalmemory/wiki)

## Upgrade

```bash
npm update -g superlocalmemory    # or: pipx upgrade superlocalmemory
slm restart && slm doctor
```

Upgrades never move or delete memory, and a store update takes a restore point first. [Host upgrades](https://github.com/qualixar/superlocalmemory/blob/main/docs/host-upgrades.md)

## Platform support

| | SuperLocalMemory | Laya (on-device answer check) |
|---|---|---|
| Apple Silicon macOS | Yes | Yes, installed by default |
| 64-bit Windows | Yes | No (Jev, the online check, works) |
| 64-bit Linux (x86-64, ARM64) | Yes | No (Jev works) |
| Intel Mac, 32-bit Windows | No prebuilt install | — |

Python 3.12+, Node 18+ for npm. Pictures and documents need 16 GB of memory.

## Contributing and license

Issues and pull requests are welcome: [CONTRIBUTING.md](https://github.com/qualixar/superlocalmemory/blob/main/CONTRIBUTING.md). Security reports: [SECURITY.md](https://github.com/qualixar/superlocalmemory/blob/main/SECURITY.md). Licensed under [AGPL-3.0-or-later](https://github.com/qualixar/superlocalmemory/blob/main/LICENSE); for a commercial license see [COMMERCIAL-LICENSE.md](https://github.com/qualixar/superlocalmemory/blob/main/COMMERCIAL-LICENSE.md).

---

<div align="center">

<img src="https://raw.githubusercontent.com/qualixar/superlocalmemory/main/assets/mascot/slm-mascot-pointing.png" width="120" alt="SuperLocalMemory mascot pointing to the repository star button">

### Built by Qualixar

**SuperLocalMemory** is made by [Varun Pratap Bhardwaj](https://varunpratap.com) at [Qualixar](https://qualixar.com): AI Reliability Engineering for agents you can trust with real work.

If SLM keeps your agents from forgetting, **[star the repository](https://github.com/qualixar/superlocalmemory)**. It's how other developers find it.

[![GitHub stars](https://img.shields.io/github/stars/qualixar/superlocalmemory?style=social)](https://github.com/qualixar/superlocalmemory/stargazers)
[![Follow on X](https://img.shields.io/badge/follow-%40varunPbhardwaj-000000?logo=x)](https://x.com/varunPbhardwaj)

**More from Qualixar:** [Qualixar OS](https://github.com/qualixar/qualixar-os) · [SkillFortify](https://github.com/qualixar/skillfortify) · [SLM Mesh](https://github.com/qualixar/slm-mesh) · [AgentAssert](https://github.com/qualixar/agentassert-abc) · [AgentAssay](https://github.com/qualixar/agentassay) · [Bounded Loops](https://github.com/qualixar/bounded-loops) · [Jev Decision Layer](https://github.com/qualixar/jev-decision-layer) · [SLM MCP Hub](https://github.com/qualixar/slm-mcp-hub)

</div>
