# GDPR Compliance

SuperLocalMemory ships built-in controls that support GDPR compliance
programs. The wider picture is in [Governance](Governance) and [Compliance](Compliance).

These are engineering controls. Compliance depends on deployment configuration,
use case, and operator responsibility. SLM is not a legal certification.

## Controls summary

| Control | Where | CLI / Dashboard |
|---------|-------|-----------------|
| Data export (Art. 15/20) | Full profile data export as checksummed JSONL | `slm evidence export` · Dashboard → Governance → Data Privacy → Export |
| Erasure (Art. 17) | Typed-confirmation profile erasure removes scoped profile data (the `default` profile cannot be erased) | Dashboard → Governance → Data Privacy → Erase; CLI supports individual `slm forget` / `slm delete`, not `slm profile delete` |
| Erasure audit log | Erasure is logged to the tamper-proof audit chain before any data is deleted | Dashboard → Governance → Audit |
| Retention rules (Art. 5) | Time-based archive, tombstone or notify rules | Dashboard → Governance → Compliance |
| Audit trail (Art. 5(2)) | Hash-chained record of every store, recall, mutation, and erasure | `slm diagnostics export` · Dashboard → Governance → Audit |
| PII redaction | Configurable redaction before memory content crosses trust boundaries | `slm config set privacy.pii_redaction true` |

## Retention rules

A retention rule has a name, a number of days, a framework label (`custom` by default, or GDPR or HIPAA as labels), an action of `archive`, `tombstone` or `notify`, and an optional filter. Rules are managed in the dashboard's Governance pane and through the compliance API, and a background scheduler enforces them every hour. See [Governance](Governance).

## Erasure completeness

Erasing a profile removes data from memory, entity, graph, mesh, audit,
session, backup-destination, and retention-rule tables. Erasure is logged to
the tamper-proof `audit_chain.db` before the delete operations begin, satisfying
Art. 5(2) accountability requirements.

After erasure, verify with:

```bash
slm diagnostics export /tmp/post-erase-report.json
```

## Notes for operators

- RBAC must be configured (`require_login = true`) to enforce access boundaries
  in multi-user deployments.
- PII redaction is heuristic, not exhaustive. Verify coverage for your content.
- The tamper-proof audit chain is stored separately from the main database and
  is excluded from erasure operations by design.

## Related pages

- [Security, Company Mode and Teams](Security-Company-Mode-and-Teams)
- [Getting Started](Getting-Started)
