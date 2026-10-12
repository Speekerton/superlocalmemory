# IDE Setup

`slm connect` wires SLM into an AI coding tool so the tool can call SLM's MCP server and, where the tool has a rules file, read a short instruction block that tells it when to recall and remember. The command supports 12 named targets: eleven that get an MCP entry written for them, and Claude Code, which is installed as a plugin instead. A second, older mode of the same command, bare `slm connect` and `slm connect --list`, knows only seven editors and only writes instruction files. Both are covered below because the difference trips people up. After any change, restart the tool completely, not just the window.

## Two modes of `slm connect`

Naming a target, as in `slm connect cursor`, does the full job. It merges an `superlocalmemory` entry into that tool's MCP config, leaving every other server and key in the file untouched, writes atomically, and aborts without touching the file if it cannot parse it. It also appends SLM's short protocol block to the tool's rules file where one exists, between `<!-- SLM-START -->` and `<!-- SLM-END -->` markers, and never overwrites your own rules. That block holds only product-authored instructions; recalled memory text is never copied into these high-trust files. Live context arrives over MCP at run time as bounded, untrusted evidence.

Running `slm connect` with no target, or `slm connect --list`, uses the older connector. It looks for seven editors (Claude Code, Cursor, VS Code / Copilot, Windsurf, Gemini CLI, Continue.dev and Zed), and for each one it finds it appends the same instruction block to the rules file, or merges JSON for Continue and Zed. In `--list`, `[+]` means the editor was detected on this computer and `[-]` means it was not; it does not mean SLM is connected. The README's figure of 12 IDEs refers to the named targets, not to what `--list` prints. To get an MCP entry written, name the target.

## The 12 targets

| Target | MCP config written | Notes |
|---|---|---|
| `cursor` | `~/.cursor/mcp.json` (key `mcpServers`) | Rules file `.cursorrules`; `--here` writes `.cursor/mcp.json` in the project |
| `antigravity` | `~/.antigravity/mcp.json` (`mcpServers`) | Global only |
| `windsurf` | `~/.codeium/windsurf/mcp_config.json` (`mcpServers`) | Rules file `.windsurfrules` |
| `gemini-cli` | `~/.gemini/settings.json` (`mcpServers`) | Rules file `GEMINI.md` |
| `vscode-copilot` | `.vscode/mcp.json` (key `servers`, not `mcpServers`) | Project-scoped: requires `--here` from the project root; rules file `.github/copilot-instructions.md` |
| `zed` | `~/.config/zed/settings.json` (key `context_servers`) | No rules file |
| `jetbrains` | `~/.config/JetBrains/mcp.json` (`mcpServers`); `--here` writes `.mcp.json` | Rules file `.junie/AGENTS.md` |
| `opencode` | `~/.config/opencode/config.json` (top-level key `mcp`) | |
| `claude-desktop` | The Claude Desktop config file for your OS (`~/Library/Application Support/Claude/` on macOS, `%APPDATA%\Claude` on Windows, `~/.config/Claude` on Linux) | The desktop app, not Claude Code |
| `codex` | `~/.codex/config.toml` (TOML table `mcp_servers`) | Rules file `AGENTS.md` |
| `continue` | `~/.continue/config.yaml` (list `contextProviders`, matched by `serverName`) | Ignores `--transport`; always stdio |
| `claude-code` | Nothing | Prints the plugin install commands |

Names are exact: `slm connect vscode` is refused with "Unknown IDE" and a list of the valid ids, and the VS Code target is `vscode-copilot`. Several of these paths are marked best-effort in the source because the editors document them loosely, so if a tool does not pick the entry up, check where that version of the tool actually reads MCP config.

Useful flags: `--dry-run` shows what would be written and changes nothing, `--here` uses project scope, `--json` returns the result as an object (`mcp_config` is one of `wrote`, `merged`, `unchanged`, `would_write`, `skipped`, `error`), and `--profile <name>` selects an MCP tool profile (see below). `slm connect --cross-platform` runs the adapters that keep instruction files fresh for Cursor (`.cursor/rules/*.mdc`), Antigravity (`.agent/skills/`) and Copilot (`.github/copilot-instructions.md`), and `--disable <adapter>` turns one off.

## Transports

By default the entry launches a stdio server: `{"command": "slm", "args": ["mcp"]}`. Each connection then starts its own `slm mcp` process, which costs memory per open tool. Two alternatives share the single daemon instead.

| `--transport` | What is written | Needs |
|---|---|---|
| `stdio` (default) | `slm mcp` as a subprocess | Nothing; works with no daemon |
| `http` | `{"type": "http", "url": "http://127.0.0.1:8765/mcp/"}` | The daemon running; `--port` changes 8765 |
| `http-mcp-remote` | A stdio entry running `mcp-remote` against that URL, for tools that speak only stdio | The daemon, plus `mcp-remote` installed globally with npm |

`slm connect <target> --transport http --verify` probes the daemon's health endpoint after writing and warns, with `slm serve start` as the fix, if it does not answer. A write is never blocked by a failed probe. If a hand-written config uses `npx` for the bridge instead of a global install, the command in the file must be `npx` with `-y mcp-remote`; naming `mcp-remote` directly fails with "command not found" unless it is installed globally.

With stdio, `--profile code` adds `SLM_MCP_PROFILE=code` to the entry's environment, which narrows the tool list ([MCP Tools](MCP-Tools)). With the HTTP transports `slm connect` appends `?profile=<name>` to the URL, but the daemon does not read that parameter, so it does not narrow the tool list; only `SLM_MCP_PROFILE` does that. To work on a different memory profile for one call, pass `profile_id` on the tool call: the named profile serves that call, the active profile never moves, and a name that is not a profile is refused rather than created.

To label what each tool writes, set `SLM_AGENT_ID` in the entry's `env` block, or connect over a URL such as `http://127.0.0.1:8765/mcp/cursor`; the Claude Code and Codex plugins already do this ([Multi-Agent Memory](Multi-Agent-Memory)). The Codex template in `ide/configs/codex-mcp.toml` sets `SLM_AGENT_ID = "codex"`.

## Claude Code and Codex

Claude Code is configured through the SLM plugin, not an MCP file. `slm connect claude-code` prints the two commands, and `slm setup` can run them for you:

```bash
claude plugin marketplace add qualixar/superlocalmemory
claude plugin install superlocalmemory@qualixar
```

The plugin brings the MCP server, 16 skills, four advisor agents, the `/slm-loop` command and lifecycle hooks. If you do not want the plugin, `slm hooks install` writes additive hooks directly, and you can add the MCP server by hand with `claude mcp add --transport http superlocalmemory http://127.0.0.1:8765/mcp/`. On native Windows install SLM first (`pipx install superlocalmemory` or `pip install superlocalmemory`) so `slm` is on PATH; the plugin's server runs your installed SLM and says so in its log if it is missing.

Codex gets the MCP entry from `slm connect codex`, lifecycle hooks from `slm hooks install --agent codex` (written to `~/.codex/hooks.json`), and its own skills and subagents from `slm codex install|remove|status`. Both plugins serve the default 57-tool profile unless you add `SLM_MCP_PROFILE=code`. Details and the upgrade path are in [Host Upgrades](Host-Upgrades).

## Tools that are not in the matrix

Grok CLI, Hermes, Kimi, CommandCode and pi.dev have no `slm connect` target; the repository documents hand-edited entries for them. All use the same server command or URL. Hermes is the one with real integration: a native Hermes plugin (`hermes-plugin/`) adds namespaced skills, `/slm` commands and lifecycle hooks, and `slm upgrade-hosts` recognises it by an `superlocalmemory` entry under `mcp_servers` in `~/.hermes/config.yaml`. Grok CLI supports stdio only, so use `command = "slm"` with `args = ["mcp"]` and `SLM_AGENT_ID = "grok"`, or the `mcp-remote` bridge. For pi.dev, add `{"mcpServers": {"superlocalmemory": {"command": "slm", "args": ["mcp"], "directTools": true}}}` to `~/.pi/agent/mcp.json` and enable it from pi.dev's `/mcp` menu; there is no plugin or connect target for it. Antigravity has a connect target, but the repository documentation says the Antigravity IDE and the `agy` CLI read `~/.gemini/antigravity/mcp_config.json` while `slm connect antigravity` writes `~/.antigravity/mcp.json`; if tools do not appear, check which file your version reads.

## Verifying

```bash
slm status                 # daemon, mode, profile, database size
slm doctor                 # dependencies, embedding worker, daemon connectivity
slm mcp                    # should sit waiting for stdio input; Ctrl+C to stop
```

Then ask the tool something that needs memory, such as "what do you know about my recent work?". If nothing is stored yet, `slm remember "test"` first. All connected tools share one memory database, so a memory saved from Claude Code is recallable from Cursor.

## When a tool does not see SLM

Restart the tool fully, not just the window. Confirm `which slm` returns a path, because stdio entries run `slm` from the tool's own environment, which may have a different PATH than your shell. Rerun `slm connect <target>`; it is idempotent. For HTTP entries, a 404 or connection refused means the daemon is down (`slm serve start` or `slm restart`). Editors do not conflict with each other, since each has its own config file. More in [Troubleshooting](Troubleshooting); the first-time wizard is `slm setup`, which detects tools and asks before connecting them ([Installation](Installation), [Getting Started](Getting-Started)).

Code: `src/superlocalmemory/hooks/portable_kit.py` (the target matrix and merge logic), `hooks/ide_connector.py` (the older seven-editor connector), `cli/commands.py` (`cmd_connect`), `cli/main.py`, `ide/configs/`.
