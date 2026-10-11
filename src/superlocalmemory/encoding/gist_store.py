# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Persist a CCQ replacement atomically, reusing equal source observations."""

from __future__ import annotations

import json
import logging

from superlocalmemory.core.lifecycle_state import set_fact_lifecycle_zone
from superlocalmemory.storage.models import AtomicFact, MemoryRecord
from superlocalmemory.storage.source_identity import store_source_fact

logger = logging.getLogger(__name__)


def _encode_gist(embedder, text):
    if embedder is not None:
        try:
            embedder.encode(text)
        except Exception as exc:
            logger.warning("Gist embedding generation failed: %s", exc)


def _archive_sources(db, fact_ids, profile_id, new_id):
    set_fact_lifecycle_zone(db, fact_ids, "archive", profile_id=profile_id)
    for fact_id in fact_ids:
        db.execute(
            "INSERT INTO fact_access_log "
            "(log_id,fact_id,profile_id,accessed_at,access_type,session_id) "
            "VALUES (?,?,?,datetime('now'),'consolidation','ccq')",
            (new_id(), fact_id, profile_id),
        )


def store_block(db, embedder, cluster, gist, profile_id, new_id):
    block_id = new_id()
    _encode_gist(embedder, gist.gist_text)  # model work stays outside the writer transaction
    with db.transaction():
        record = MemoryRecord(
            memory_id=block_id, profile_id=profile_id, content=gist.gist_text, session_id="ccq"
        )
        fact = AtomicFact(
            memory_id=block_id,
            profile_id=profile_id,
            content=gist.gist_text,
            canonical_entities=list(gist.key_entities),
            importance=0.8,
            confidence=1.0,
            session_id="ccq",
        )
        store_source_fact(db, record, fact)
        db.store_ccq_block(
            block_id=block_id,
            profile_id=profile_id,
            content=gist.gist_text,
            source_fact_ids=json.dumps(list(cluster.fact_ids)),
            gist_embedding_rowid=None,
            char_count=len(gist.gist_text),
            cluster_id=cluster.cluster_id,
        )
        _archive_sources(db, cluster.fact_ids, profile_id, new_id)
    return block_id
