# Automatic memory description and health

WP-19 uses one description pass for every canonical save and one default-on idle
health worker. It adds metadata without changing source text. Rules always work
offline; model suggestions may use only a local bounded classifier. Caller and
user classifications are preserved.

`valid_from` is event time: the referenced/event date when known, otherwise the
observation date, otherwise unknown (never save time, which is transaction time:
using it made undated facts "not yet valid" for an earlier `as_of`). It is
independent of system transaction time, which records when the product learned
the fact. Unknown event dates stay
unknown; enrichment does not invent dates or labels to meet a coverage percentage.

Enrichment may fill a missing observation date from `created_at` (when the memory
was recorded). That value is written to the ledger with source `inferred` and is
never used as `valid_from`: only the fact's own event date, or the observation
date it carried before enrichment, can start its validity. As-of recall is
therefore the same before and after enrichment.

Implementation order, each with a failing regression then a passing commit:

1. Repair event-time anchoring in the canonical fact writer and materializer.
2. Restore entity extraction on incomplete facts; local kind suggestions and
   explicit non-answer stub filtering; contract across save surfaces.
3. Add an additive migration and resumable enrichment ledger, conservative
   metadata derivation, product safety copy, conflict-safe undo.
4. Add an idle worker with RAM reservation, foreground preemption, background
   pause and owned shutdown; unify automatic safe repairs under memory health.
5. Wire shared CLI/dashboard actions and doctor coverage/progress.
6. Run the requested complete directories sequentially, UI suite, touched-file
   Ruff, import-linter and public-repository leak checks; independent review.

Evidence at baseline: the canonical fact writer creates transaction anchors with
no event-time start. The optional temporal validator later supplies observation
time only, leaving installations without that validator empty. The shared
`enriched_fact.enrich` validates existing entity strings but does not recover
missing extraction. The kind classifier's LLM branch only consumes extraction
hints, so the preserved verbatim source fact gets rules even when Ollama is local.

All development and verification use synthetic isolated stores. The installed
product and its listeners are excluded. Commits remain local.

Entity coverage drop (A2): with the release extractor, the same sentences give
the same names (people, projects and tools at mid-sentence positions), so the
stricter validity filter was not rejecting real names. The drop came from the
description step: `enriched_fact.enrich` only validated names a model or an
older extractor had already supplied, so every save whose fact arrived without
names (the preserved verbatim fact, and model extractions that returned none)
was stored with none. It now runs the shared extractor on every fact and keeps
only names that pass the validity rules; an explicit role ("Zephyr is our
project") also admits a sentence-initial name.

Safety copies: the product's pre-change copy is taken once per store, before
the first automatic change, and reused by every later run and repair; each run
is undoable from its own ledger, so a copy per batch would only fill the disk.
A finished pass is followed only by facts saved after it.

Failed-save repair: there is no `slm ops repair-saves` on this branch, so the
Memory health card covers hidden-memory re-filing, search-sketch repair,
entity-link repair and the upgrade store check; failed operations stay under
`slm ops`.

Review follow-ups (H1-H3, M1-M5, L1-L3):

- Automatic repairs only add. Search-sketch repair runs on idle ticks, never
  for an action whose latest run was undone, never for an item an undone run
  touched. Entity-link repair (deletes aliases and junk entities) and hidden
  re-filing (moves lifecycle zones) are counted into a `suggested` row and run
  only on the user's Fix (`slm enrich fix`, the card). Failures are one row per
  action and error class with an attempt count and exponential back-off.
- Legacy facts without a `fact_temporal_validity` row stay `legacy_unknown`:
  enrichment fills `atomic_facts.valid_from` and an empty `valid_from` on an
  existing temporal row, never creates a row and never touches
  `system_created_at`. Every writer uses fill-only event starts, including a
  duplicate re-save through the store pipeline.
- Stub exclusion is opt-in for recall answer paths only (engine hydration,
  degraded recall, degraded session context). Lists, counts, export and the
  dashboard include stubs with a `stub` flag. The stub rule is a label plus a
  machine-shaped id (8+ hex with a letter a-f, 12+ digits, UUID, ULID) or dated
  session boilerplate, so a receipt number or a date stamp is not a stub. An
  edit sets `non_answer_user=0` (which the save-time mark and enrichment obey)
  only when the correction is applied; a proposal alone, or a rejected one,
  leaves the flag as it was.
- A profile fold maps the undo ledger's entity ids through its own merge, so
  undo after a profile delete restores exactly.
- Background kind suggestions refuse Ollama cloud models by tag and by
  `/api/show` remote fields; an unverifiable model keeps the rules.
- The health report lists every changing run with its id; the card's Undo and
  `slm enrich undo` (no id: latest, confirmed) use it. States are plain
  sentences and exception class names are logged, never shown.
