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

The MCP watcher requires exactly `gate_contract={"job_id": job["job_id"]}`.
An operator registers the command, its check definition files, and the explicit
mutable artifact paths or globs before execution:

```python
from superlocalmemory.loops.receipt_jobs import register_job, run_registered_check

job = register_job(
    db, profile_id="default", task_id="build", watcher_name="build",
    producer="operator-checker", command=[python_executable, "-m", "pytest", "tests"],
    cwd=project, check_paths=["tests", "pytest.ini"],
    artifact_paths=["src/**/*.py"], data_root=slm_data_root,
    allow_prestart_evidence=False,
)
receipt = run_registered_check(db, job["job_id"], timeout=30)
# The MCP client waits with slm_loop_run(name="build", gate_query="build",
#                                     gate_contract={"job_id": job["job_id"]})
```

Include all tests, scripts, fixtures such as `conftest.py`, and configuration in
`check_paths`. Registration copies these regular files into a content-addressed
store under the SLM data root. Their SHA-256 hashes and the command are pinned;
later live edits to these files do not change the registered check. Definition
files and mutable artifacts must occupy distinct paths. Paths are confined to
the project; symlinks, devices and FIFOs are refused. Explicit directory inputs
include their regular-file trees. Globs are expanded again for each run and
admission, so added or removed matching files change the revision. Files outside
these declarations never enter the run directory.

Every run uses a fresh private directory outside the project. It copies only the
pinned definition and declared artifacts, reading each input once and hashing
the bytes copied. The revision is the SHA-256 of the sorted relative-path and
content-hash manifest. The subprocess runs there without a shell, with closed
stdin, an allow-listed environment, private HOME/temp/XDG directories, and a
bounded timeout. Installed pytest plugins are disabled unless explicitly loaded
with `-p`. Checker descendants are stopped before validation and cleanup.
Project aliases in command paths are canonicalized at registration. Standalone
absolute project paths and `--option=/project/path` arguments are relocated into
the copy. The executable must be operator-owned outside the project; project
executables are refused at registration. Embedded code and check scripts must
use relative paths for verdict-bearing inputs; external dependencies require a trusted operator
contract. Outputs and caches remain in the private run and are discarded.

Only after validation succeeds does the registered runner publish a receipt.
An owner-only per-data-root HMAC key authenticates its job, definition hash,
copied revision, exit status, output digest, and execution identity. The public
`execution_receipts.run_check` API produces diagnostic receipts without admission;
its `validate_result` callback cannot mint an admitted PASS.

DONE requires the newest matching authenticated PASS and a fresh copy/hash of
current declared artifacts with exactly the same revision. Changed artifacts
require a rerun; the same job can run against a new artifact revision. Changed
check definitions require a new registration. A newer registration supersedes
older jobs for the profile/watcher; expiration, cross-profile, self-authored,
stale, failed or unauthenticated receipts cannot finish a loop. By default a
watcher accepts only receipts produced after it started; only the operator may
enable pre-start evidence. Legacy registrations require re-registration.

Private directories are 0700 and files are 0600. The data root and check tool
installation must be controlled by the operator and inaccessible to the task
writer. This is filesystem-copy isolation, not an OS sandbox: a same-UID shell
agent with access to the store/key or arbitrary operator code is outside this
boundary. No live-tree ctime or ancestor stamps are used. Hosts with secure
no-follow directory handles can run checks regardless of filesystem timestamp
semantics. Native Windows currently lacks the required Python primitives and
is refused at registration with an explicit platform reason. The waiting MCP
user receives that reason, rather than a bare `max-iterations`; other refusals
appear in `receipt_reason` and the gate detail.

Receipt and registration rows are immutable and erased with their owning
profile. The filesystem definition store belongs to the operator's data root;
profile deletion does not garbage-collect these pinned files. Ordinary `remember`
writes cannot create execution evidence. `require_support` additionally requires
Answer check support for recalled context; support alone cannot establish PASS.
