# Bounded Loops

A bounded loop is an agent loop that ends only when an independent check passes, never because the agent says it is finished. SLM ships its own small loop engine and records every lap as ordinary memory, so a run's history survives restarts and shows up in recall and on the dashboard. The name is shared with a separate, optional product, also called Bounded Loops, that runs multi-step graphs; SLM can read that product's finished-run evidence over a published contract but never runs it or lets it influence recall. This page covers both, starting with the one invariant that matters: the gate decides, the agent's claim is only logged.

## The invariant

Each lap the engine runs in a fixed order: check the kill switch, check the budget, let the runner do one lap of work, add up the token spend, ask the gate for a verdict, then decide. The runner may report `agent_claimed_done`. The engine writes that flag to the ledger for audit and never reads it when deciding to stop. The reason is practical: an agent that is wrong about being done is the failure the loop exists to catch, so the stop condition has to come from something the agent cannot assert into existence.

A run ends in exactly one of five terminal statuses.

| Status | Meaning | Reasons you may see |
|---|---|---|
| `DONE` | The gate passed, and approval was granted or not required. The only success state | `gate-passed` |
| `HALT` | A safety bound tripped | `max-iterations`, `token-budget`, `wallclock`, `no-progress` |
| `PAUSE` | The gate passed but required approval was not granted | `awaiting-approval` |
| `KILLED` | The kill switch tripped between laps (set the environment variable `SLM_LOOP_KILL`) | `killed` |
| `ERROR` | The runner or the gate raised before a verdict | the error text |

Report the exact status. A `HALT` is not a success with an excuse attached; it means a bound stopped the run before the gate passed. The token and wall-clock budgets are hard ceilings that win over the gate: a lap that overshoots halts even if its own gate would have passed.

Autonomy is set by a rung. `L1` (report) exits on a passing gate with no approval. `L2` (assisted) and `L3` (unattended) require approval before a passing gate becomes `DONE`, unless the bounds force the posture either way. The MCP and CLI entry points below run at `L1`.

## Waiting on another agent: `slm_loop_run`

Over MCP the gate is an SLM recall. `slm_loop_run` converges on the first lap where recalling `gate_query` returns a confident match scoring at least `gate_min_score`. That makes it a shell-free coordination primitive: one agent waits, under strict bounds, for a memory another agent will write.

```python
# Agent A records the signal
await remember("review complete: PR #42 is approved", tags="review,pr-42")

# Agent B waits for it
result = await slm_loop_run(
    name="wait-for-pr-review",
    gate_query="PR #42 approved",
    gate_min_score=0.5,
    max_iterations=30,
    max_wallclock_s=60.0,
    poll_interval_s=2.0,
)
```

The call blocks, polling the gate, until the gate passes or a bound trips, then returns `ok`, `status`, `reason`, `passed`, `laps`, `run_id`, a short ledger and a note that the gate decided. On internal failure it returns `ok: false` with a message instead of raising.

| Parameter | Default | Limit |
|---|---|---|
| `name` | required | 1 to 128 characters; also the memory tag |
| `gate_query` | required | 1 to 2,000 characters |
| `gate_min_score` | 0.0 | Minimum top-result score (0.0 means any confident hit above the evidence floor) |
| `max_iterations` | 20 | 1 to 200 |
| `max_wallclock_s` | 15.0 | Capped at 120; 0 removes the wall-clock limit |
| `poll_interval_s` | 1.0 | At least 0.25 |
| `max_tokens` | 0 | 0 means no token budget |
| `no_progress_window` | 0 | Leave at 0 for a pure watcher, which never "changes" and would halt before the gate can pass |
| `require_support` | false | Pass only when the answer check ran and judged the memories sufficient |

Each lap does one recall of at most three memories. Two details keep the gate honest. The loop's own ledger rows are excluded from the gate, because they are stored as memories and would otherwise match the query on the next lap and pass it falsely; only a memory from someone else can satisfy the gate. And when [Answer Check](Answer-Check) is on, a recall the check judged insufficient can never pass, even if its relevance score looks high; with `require_support` true, a recall the check did not or could not run on also fails. With the check on, each lap asks it once about those memories, which with the online check is a request to the provider.

`slm_loop_history(name, limit, profile_id)` lists recorded runs (`run_id`, lap count, final decision, time), and `slm_loop_show(run_id, limit, profile_id)` returns every lap with its decision, pass flag, detail, the recorded `agent_claimed_done` and the tokens. Both are read-only. The three tools are in the `code`, `full` and `power` MCP profiles ([MCP Tools](MCP-Tools)).

## From the command line and from hosts

```bash
slm loop demo                      # keyless demo; proves the engine and ledger end to end
slm loop demo --iterations 10 --json
slm loop history                   # runs for the default demo loop name
slm loop history --name my-loop --json
slm loop show <run_id>
```

The CLI is for inspection and the demo only; the demo uses a built-in stub runner. To run a real loop from a host, use the `/slm-loop` command and the `slm-loop` skill in the Claude Code and Codex plugins, which hand the work to the `slm-loop-runner` agent. For a task with a checkable condition such as a test suite, a schema or a linter, the agent runs that command itself each lap; SLM does not execute commands. The runner agent reports the exact terminal status and never dresses up a non-`DONE` result.

## The ledger

Every lap is written to SLM memory with the tag `loop:<name>`, a run id, the lap number, the decision (`continue`, `done`, `halt`, `pause`, `killed`, `error`), the gate's one-line detail and a budget snapshot. Because it is ordinary memory it is queryable with `slm recall`, appears in the dashboard, and moves with your backups. Ledger writes fail open: a write error is counted and reported with the run instead of aborting a loop in flight, since the gate is the correctness guarantee and the ledger is observability.

## The separate Bounded Loops product

The graph runner Bounded Loops is a different package with its own gates and receipts. The two never import each other, and installing SLM never installs or starts it. When both are present, an MCP client can call `observe_bounded_loop_evidence(workspace)` to take one explicit, read-only snapshot of finished graph runs in an absolute workspace path. SLM finds only the installed `bounded-loops-mcp` executable (callers cannot supply a command), checks that it advertises the exact contract `bounded-loops.dev/slm-bridge/v1`, and stores compatible evidence under the active profile in the learning database. The call has a five-second producer timeout.

This is observation only. In v1 the field `eligible_for_learning` must be false, and the rows are not used for recall, ranking, routing, reward or any behaviour change, because a graph run succeeding is not proof that a memory decision should be learned. Recall and remember never launch Bounded Loops or open this store. No graph artifacts, commands, paths or gate prose are copied; only the producer's public, sanitised evidence document is read, and the evidence is deleted with its profile. A second tool, `observe_bounded_loop_execution_learning(workspace)`, ingests contract v2 terminal evidence into an execution-reliability store that never writes semantic facts or preferences; it is not in any named profile and is available under `whole`. The Living Brain shows the count as Bounded Loop observations ([Living Brain](Living-Brain)).

## Dashboard

Integrations > Bounded Loops has four parts: Bridge status, How it works, a "Run it" block with the CLI command and MCP call, and Framework adapters. Detection of the separate product uses a PATH lookup for `bounded-loops-mcp`, then a version call with a 1.5-second timeout, and it does not claim the bridge is live. If it is absent the pane says "not installed", which is a normal, complete state. The framework list shows the nine adapters in [Framework Adapters](Framework-Adapters). For coordination between agents without a loop see [Multi-Agent Memory](Multi-Agent-Memory).

Code: `src/superlocalmemory/loops/` (`engine.py`, `models.py`, `rules.py`, `budget.py`, `ledger.py`), `mcp/tools_loops.py`, `cli/loop_cmd.py`, `integrations/bounded_loops_mcp.py`, `mcp/tools_brain.py`, `ui/js/od-boundedloops.js`.
