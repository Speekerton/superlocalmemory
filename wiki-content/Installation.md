# Installation

SLM installs as a single `slm` command, either through npm (which gives it a private Python environment) or through pipx or pip (which put it in a Python environment you control). Installing only puts the program on disk. It does not create your data folder, edit an IDE, start a daemon or download a model. Those happen when you run `slm setup`, so you decide each step. SLM 4.1.25 supports Apple Silicon Macs, 64-bit Windows and 64-bit Linux on Python 3.12 to 3.14.

## What you need

| Requirement | Value | Check |
|---|---|---|
| Python | 3.12, 3.13 or 3.14 (`requires-python >=3.12,<3.15`) | `python3 --version` |
| Node.js and npm | Node 18 or later and npm 9 or later, only for the npm route | `node --version` |
| Memory | The wizard recommends 4 GB or more; images and documents need 16 GB | |
| Disk | About 500 MB for the embedding model and 130 MB for the reranker, both downloaded once | |

Optional downloads are asked about separately: a compression model (about 560 MB), the on-device answer check (about 1.1 GB, Apple Silicon only) and images and documents (about 1.5 GB, see [Pictures and Documents](Pictures-and-Documents)).

## What is supported

| System | Text memory | Images and documents |
|---|---|---|
| macOS on Apple Silicon | Supported | Supported (16 GB RAM) |
| Windows x64 | Supported | Supported (16 GB RAM) |
| Linux x86_64 | Supported | Supported (16 GB RAM) |
| Intel Mac | Not supported | Not supported |
| 32-bit Windows | Not supported | Not supported |
| Linux ARM64 (Raspberry Pi, Graviton, Ampere) | Text memory works as on other 64-bit Linux | Not supported yet |

The package metadata does not block an unsupported architecture, so an install on Intel Mac or 32-bit Windows fails later, where a pinned dependency has no build for it. On Linux ARM64 the project documents only images and documents as unsupported, and says text memory works there as before.

## Install

**npm, the shortest route.** This installs the command globally and builds a private Python environment (`.slm-venv`) inside the package, so it never touches your system Python.

```bash
npm install -g superlocalmemory
```

The installer searches for `python3.14`, `python3.13`, `python3.12`, then `python3` and `python`. If your supported interpreter is somewhere unusual, set `SLM_PYTHON` to its path before you run the install. A path that is not a Python 3.12 to 3.14 is refused, and the installer does not quietly pick another.

**pipx.** Good if you want an isolated command without npm.

```bash
pipx install superlocalmemory
```

**pip in a virtual environment.** Use this when you also want the Python API. Keep the environment active whenever you run `slm`.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install superlocalmemory
```

Do not use `sudo pip`, and do not override an externally managed system Python. Do not install the same `slm` command through more than one tool.

**From a repository clone.** For contributors and researchers. The script delegates to an existing uv or pipx and refuses to run without one.

```bash
git clone https://github.com/qualixar/superlocalmemory.git
cd superlocalmemory
./scripts/install.sh install       # also: upgrade, uninstall, --manager uv|pipx, --dry-run
# Windows PowerShell: .\scripts\install.ps1 -Action Install
```

## Per-system notes

**macOS (Apple Silicon).** macOS ships an older Python, so install one first, for example `brew install python@3.12`. The on-device [answer check](Answer-Check) works only here.

**Windows (x64).** Install a 64-bit Python 3.12 to 3.14 first. For the Claude Code plugin on native Windows, install SLM first with `pipx install superlocalmemory` or `pip install superlocalmemory`, so `slm` is on PATH before the plugin starts it.

**Linux (x86_64).** Install Python 3.12 or later with your package manager. On Ubuntu 22.04, use the deadsnakes archive: `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.12 python3.12-venv`. If the system Python cannot create virtual environments, install your distribution's `python3-venv` package. A virtual environment (`python3.12 -m venv ~/.slm-venv`) avoids conflicts with the system Python.

## Activate it

Nothing is active until you run setup.

```bash
slm setup       # choose a mode and what to enable
slm warmup      # load the embedding model; downloads about 500 MB the first time
slm doctor      # check dependencies, the embedding worker and the daemon
slm status      # mode, profile, data folder, database size
```

`slm warmup` exits non-zero if recall is not ready, which makes it usable in a script. `slm doctor --fix` re-downloads missing models and installs sqlite-vec before reporting. Behind a proxy, set `HTTP_PROXY` and `HTTPS_PROXY` so the model download can reach its host.

## The setup wizard

`slm setup` asks in this order. `slm setup --auto` (or no terminal) takes every default without asking: Mode A, no integrations, no auto-start.

| Step | What it asks | Default |
|---|---|---|
| 1. System check | Nothing; reports Python version, platform, RAM, the data folder and whether sentence-transformers is installed | |
| 2. Operating mode | Mode A, B or C ([Modes Explained](Modes-Explained)), then whether other profiles' shared and global memories appear in your recall | Mode A, or B if Ollama is detected; shared recall off |
| 3. Code knowledge graph | Whether to build structural maps of your repositories | On |
| 4. Models | Downloads the embedding model and the reranker; asks before the optional compression model; on Apple Silicon asks about the on-device answer check | Compression model skipped |
| 5. Daemon | Always on, or shut down after 30 minutes, 1 hour or 2 hours idle | Always on |
| 6. Mesh | Agent-to-agent messaging ([Multi-Agent Memory](Multi-Agent-Memory)) | On |
| 7. Ingestion adapters | gmail, calendar, transcript | All off |
| 8. Entity compilation | Per-entity summaries | On |
| 9. Skill evolution | Background skill improvement, which makes model calls ([Skill Evolution](Skill-Evolution)) | Off |
| 10. Verification | A self-test that recall works | |

After step 10 the wizard checks that the data folder is not inside a cloud-sync folder such as iCloud, Dropbox or OneDrive, offers the concurrent-recall queue, then asks, separately and with a default of no, whether to install the Claude Code plugin and hooks, then whether to connect other detected IDEs (default yes), and whether to install the auto-start service. Declining any of these costs nothing; you can run `slm connect claude-code`, `slm connect IDE` or `slm serve install` later.

## Where your data lives

The data folder is `~/.superlocalmemory` (on Windows, `.superlocalmemory` in your user folder). Three environment variables can change it, and the first one set wins: `SLM_DATA_DIR`, then `SL_MEMORY_PATH`, then `SLM_HOME`. A configured base directory comes after them. Installers manage the program; the data folder is separate, and no installer, upgrade or uninstall moves or deletes it. It holds `memory.db`, `learning.db`, configuration, logs (`logs/daemon.log`), downloaded models under `runtimes/`, and backups.

## Run the daemon at login

```bash
slm serve install      # user-level service, no administrator rights
slm serve status
slm serve uninstall
```

`install` writes a LaunchAgent on macOS, a systemd user service on Linux and a Task Scheduler task that runs at logon on Windows. On Linux, verify the install with `slm doctor` first, and persist `SLM_DATA_DIR` in the service if you moved the data folder. For access from other computers, see `slm remote` in [CLI Reference](CLI-Reference).

## Connect your tools

```bash
slm connect --list          # which editors were detected
slm connect cursor          # write the MCP entry for a named tool
```

The per-tool targets, transports and the Claude Code and Codex plugins are in [IDE Setup](IDE-Setup). The tool profiles that decide how many MCP tools a client sees are in [MCP Tools](MCP-Tools).

## Upgrade

Package managers update the program and deliberately leave your host integrations alone.

```bash
npm install -g superlocalmemory@latest      # npm route
pipx upgrade superlocalmemory               # pipx route
python -m pip install --upgrade superlocalmemory   # pip route, environment active
slm restart
slm doctor
slm upgrade-hosts                           # preview which host integrations are stale
slm upgrade-hosts --host codex --apply      # refresh only what you reviewed
```

A few minutes after SLM first starts on a new version it checks the memory store once, read-only, and shows the result under Health in the dashboard ([Health and Repair](Health-and-Repair)). Schema migrations are additive and forward-only. There is no downgrade of the schema; to go back, use a restore point (`slm db restore-points`, `slm db prepare-downgrade`) or restore a verified copy of the whole data folder. See [Host Upgrades](Host-Upgrades) and [Upgrade Memory Engine](Upgrade-Memory-Engine). Coming from SLM 2? Use [Migration from V2](Migration-from-V2).

## Uninstall

Remove the integrations first, then the program.

```bash
slm serve uninstall                  # remove the login service
slm hooks remove                     # Claude Code hooks (add --agent codex for Codex)
slm codex remove                     # Codex skills, agents and hooks
slm media disable --remove-files     # delete the downloaded picture models, if you enabled them
npm uninstall -g superlocalmemory    # or: pipx uninstall superlocalmemory / pip uninstall superlocalmemory
```

Uninstalling removes code only. Your memories stay in the data folder, which also keeps the picture models (about 1.5 GB under `runtimes/media`) and the on-device answer-check model (`runtimes/laya`) until you remove them. To erase everything, export or back up what you need, then delete the data folder yourself.

## Install problems

| Symptom | Fix |
|---|---|
| `slm: command not found` | With npm, add `$(npm prefix -g)/bin` to PATH, or run `npx superlocalmemory status`. With pip, add the Python scripts directory to PATH |
| Permission errors from npm | Do not use sudo. Point npm's prefix at a folder you own, or install inside a virtual environment |
| `ModuleNotFoundError: superlocalmemory` | Activate the environment SLM was installed into, or reinstall with `python -m pip install --force-reinstall superlocalmemory` |
| The installer says no supported Python | Install Python 3.12 to 3.14, or set `SLM_PYTHON` to its path |
| Embedding model download fails | Check the connection and proxy variables, then run `slm warmup` again |

More in [Troubleshooting](Troubleshooting). Next, follow [Getting Started](Getting-Started) for your first hour.

Code: `pyproject.toml`, `package.json`, `scripts/postinstall.js`, `scripts/preuninstall.js`, `scripts/install.sh`, `scripts/install.ps1`, `cli/setup_wizard.py`, `cli/service_installer.py`, `infra/data_root.py`, `runtimes/media_env.py`.
