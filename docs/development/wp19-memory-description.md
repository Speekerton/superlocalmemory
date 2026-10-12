# Automatic memory description and health

WP-19 uses one description pass for every canonical save and one default-on idle
health worker. It adds metadata without changing source text. Rules always work
offline; model suggestions may use only a local bounded classifier. Caller and
user classifications are preserved.

`valid_from` is event time: the referenced/event date when known, otherwise the
observation date, otherwise save time. It is independent of system transaction
time, which records when the product learned the fact. Unknown event dates stay
unknown; enrichment does not invent dates or labels to meet a coverage percentage.

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
