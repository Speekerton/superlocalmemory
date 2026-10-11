# Bounded Loops observation bridge

SuperLocalMemory and Bounded Loops are separate optional products. SLM owns
durable, profile-scoped memory and learning evidence. Bounded Loops owns graph
execution, gate decisions, and receipt truth. Neither package imports the
other, and installing SLM never installs, starts, or configures Bounded Loops.

When both are installed, an MCP client can call
`observe_bounded_loop_evidence(workspace)` to take one explicit read-only
snapshot of terminal graph runs in that workspace. SLM resolves only the
installed `bounded-loops-mcp` executable; callers cannot supply a shell command
or arguments. The workspace must be an existing absolute path.

## Compatibility

The bridge negotiates the producer's advertised MCP capability, not a package
version. It requires this exact contract:

```text
bounded-loops.dev/slm-bridge/v1
```

The producer must advertise `bl_graph_evidence` with the
`observe_terminal_run` operation. SLM then lists terminal runs and fetches each
one with its `run_ref` address. It never sends `run_id` as a replacement for
that address. An absent or incompatible producer returns a structured refusal;
it does not change SLM memory behaviour.

## What SLM stores

Compatible evidence is stored in the additive `learning.db` migration M041,
under the active SLM profile. It preserves the producer's terminal state,
demonstration flag, receipt head, digests, and node gate outcomes. The Living
Brain shows the resulting count as **Bounded Loop observations**.

This is deliberately observation-only. In v1, `eligible_for_learning` must be
false, and SLM does not use these rows for recall, ranking, routing, reward, or
automatic behavioural change. A successful graph run is not proof that a
memory decision should be learned. A future contract can add an explicitly
audited learning authority without changing this v1 boundary.

## Privacy, erasure, and performance

No graph artifacts, commands, paths, or gate prose are copied into SLM. The
bridge reads only the producer's public sanitized evidence document. Evidence
is deleted with its SLM profile and a durable profile-closure tombstone blocks
stale processes from writing it again after erasure.

Observation is an explicit MCP operation and has a five-second producer timeout.
Recall and remember never launch Bounded Loops or open this evidence store;
they never enter its recall or ranking logic. Observation writes use the
bounded learning-db receipt gate and can return a retryable refusal under
contention rather than delaying a memory answer.

## Answer check and loop gates

This bridge is unaffected by [Answer check](answer-check.md) — it observes
Bounded Loops' own graph receipts, not SLM recall. The `slm_loop_run` MCP
tool also verifies an independently executed receipt. Recall supplies context;
its relevance and answerability cannot establish a passing execution.

The MCP watcher requires a `gate_contract` for `DONE`: `task_id`, `run_id`,
`producer`, `min_timestamp` (UTC ISO), and `command_digest`. An optional
`evidence_digest` pins one output digest. Ordinary memories, including a related
"build passed" claim, cannot create execution evidence.

An operator-side checker calls
`superlocalmemory.loops.execution_receipts.run_check(db, profile_id=...,
 task_id=..., run_id=..., producer=..., command=[...], cwd=...)`.
It executes the command without a shell and derives the verdict from its exit
status. `command_digest(command, cwd)` supplies the command identity before a
check starts; output may arrive later. The watcher validates the stored output
hash and the newest matching execution. A newer failure supersedes an older
pass for the same run. Give each verification job its own run ID.

Receipt rows are append-only and cannot be populated through `remember`.
Missing, self-authored, failed, stale, wrong-run or mismatched evidence cannot
produce `DONE`; the watcher halts at its configured bound. `require_support`
also requires the answer check to support the recalled context.
