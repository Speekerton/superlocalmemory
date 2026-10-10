# Health and Repair

SLM checks itself in five separate ways, and repairs most problems without losing a memory. This page names each mechanism, because "watchdog" is not one feature: it is several small ones that cover different failures.

## Pre-flight and component health

`slm doctor` runs a checklist and `slm doctor --fix` repairs what it can by re-downloading missing models or installing the vector extension. `--quick` is fast, `--deep` runs a full SQLite integrity check. A component registry runs read-only probes, and a healer acts on what they find, with firm limits: it never uses sudo, never pulls an Ollama model on its own and never installs a multi-gigabyte dependency unasked. In the dashboard, **Health** shows components with a **Retry now** button. The daemon also self-heals at start, removing only lock and process files that are provably dead.

## Store integrity and repair

`slm db integrity` reports five separate answers (pages, relations, fidelity, projections and repair) and changes nothing. `slm db repair` previews by default. With `--apply` it fixes orphan rows, stale or orphaned vectors, erased-text leftovers and settled obligations, in small receipted batches (100 rows per batch with a 50 ms pause by default). `--undo RUN_ID` puts back what a run changed. `slm db fidelity` lists facts whose text drifted from what their memory said. In the dashboard, Health has a **Memory store** card that runs the once-per-upgrade check, and **Repair now** takes a backup copy first. Why batches and receipts: a repair that holds the database for minutes would stall every other writer, and a repair you cannot undo is a risk.

## Operations recovery

`slm ops list`, `resolve` and `status`, and the MCP tools `list_failed_operations` and `resolve_operation` (in the `whole` profile) surface the dead-letter queue, stuck ingestion, exhausted projection obligations and writer stalls. The dashboard shows the same under Governance, Admin: Ops Health.

## Process watchdogs

A health monitor kills the heaviest worker when total memory passes a budget (40 percent of RAM, with a 2,500 MB floor, unless `SLM_RSS_BUDGET_MB` says otherwise) and kills workers that have been silent for 60 seconds. Every worker also watches its parent process and exits if the parent dies. The picture worker has its own memory cap (`SLM_MEDIA_WORKER_RSS_LIMIT_MB`, 1,600 MB by default). `slm reap` kills orphaned SLM processes whose IDE parent has died, and `slm restart` is the heavy option: it kills orphans, cleans state, starts again and verifies health.

## Math-layer health

`slm health` and the MCP `health` and `consistency_check` tools check the mathematical layers, including a sheaf-based contradiction check. In the dashboard, the Health pane's status strip shows the daemon, memory database, math layers and mesh broker, with trust signals and connected agents below.

## Escape hatches

`slm disable` writes a `.disabled` marker in the data folder and stops the daemon; `slm enable` removes it. Both are for the case where you need SLM to stand down without uninstalling it.

Code: `core/component_registry.py`, `core/component_healer.py`, `storage/integrity_health.py`, `storage/integrity_repair.py`, `storage/integrity_receipts.py`, `cli/integrity_cmd.py`, `core/health_monitor.py`, `infra/process_reaper.py`, `infra/self_heal.py`, `server/routes/integrity.py`.
