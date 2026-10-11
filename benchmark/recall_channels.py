"""Model-free synthetic recall profiler; never reads an existing store.

Run with PYTHONPATH=src uv run --frozen python benchmark/recall_channels.py
--directory "$TMPDIR/wp4b" --facts 30000 --samples 20 --label before.
The directory must be new on the first run. Output includes cProfile and SQL plans.
"""

from __future__ import annotations

import argparse
import cProfile
import json
import math
import os
import re
import statistics
import time
from pathlib import Path

from superlocalmemory.core.config import RetrievalConfig
from superlocalmemory.retrieval.bm25_channel import BM25Channel
from superlocalmemory.retrieval.engine import RetrievalEngine
from superlocalmemory.retrieval.entity_channel import EntityGraphChannel
from superlocalmemory.retrieval.temporal_channel import TemporalChannel
from superlocalmemory.storage import schema
from superlocalmemory.storage.database import DatabaseManager


def seed(db: DatabaseManager, count: int) -> None:
    """Deterministic SQL seeder using the product schema, indexes and triggers."""
    db.initialize(schema)
    with db.transaction():
        conn = db._txn_state.conn
        for profile in ("default", "team", "other"):
            conn.execute("INSERT OR IGNORE INTO profiles(profile_id, name) VALUES (?, ?)",
                         (profile, profile))
            conn.execute("INSERT INTO memories(memory_id, profile_id, content) VALUES (?, ?, ?)",
                         (profile, profile, "synthetic"))
        conn.executemany(
            "INSERT INTO canonical_entities(entity_id, canonical_name, profile_id) "
            "VALUES (?, ?, ?)",
            ((f"e{i}", "Alice" if i == 0 else f"Project{i}", "default")
             for i in range(count // 2)),
        )
        conn.executemany(
            "INSERT INTO atomic_facts(fact_id, memory_id, profile_id, scope, shared_with, "
            "content, canonical_entities_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (fact_row(i, count) for i in range(count)),
        )
        conn.executemany(
            "INSERT INTO temporal_events(event_id, entity_id, fact_id, referenced_date) "
            "VALUES (?, ?, ?, ?)",
            ((f"t{i}", f"e{i % (count // 2)}", f"f{i:06}",
              f"2025-{i % 12 + 1:02}-{i % 28 + 1:02}") for i in range(count)),
        )
        conn.executemany(
            "INSERT INTO graph_edges(edge_id, source_id, target_id, weight) VALUES (?, ?, ?, ?)",
            ((f"g{i}-{j}", f"f{i:06}", f"f{(i + j) % count:06}", 0.7)
             for i in range(count) for j in range(1, 12)),
        )


def fact_row(i: int, count: int) -> tuple:
    profile = "default" if i % 10 < 8 else ("team" if i % 10 == 8 else "other")
    scope = "global" if i % 10 == 8 else ("shared" if i % 10 == 9 else "personal")
    entities = [f"e{i % (count // 2)}"]
    if i % 3 == 0:
        entities.append("e0")
    return (f"f{i:06}", profile, profile, scope, '["default"]',
            f"Alice project memory release {i % 100} engineering topic{i % 500}",
            json.dumps(entities), f"2025-{i % 12 + 1:02}-{i % 28 + 1:02} 12:00:00")


def measure(call, samples: int) -> dict:
    times = []
    rankings = []
    for _ in range(samples):
        started = time.perf_counter()
        result = call()
        times.append((time.perf_counter() - started) * 1000)
        rankings.append(result if isinstance(result, list) else str(result))
    ordered = sorted(times)
    return {"p50_ms": statistics.median(times),
            "p95_ms": ordered[math.ceil(len(ordered) * .95) - 1],
            "samples_ms": times, "ranking": rankings[-1]}


def profile_calls(db, directory, samples, label) -> dict:
    entity, temporal, bm25 = EntityGraphChannel(db), TemporalChannel(db), BM25Channel(db)
    engine = RetrievalEngine(db, RetrievalConfig(),
                             {"entity_graph": entity, "temporal": temporal, "bm25": bm25})
    calls = {
        "bm25": lambda: bm25.search("Alice memory release", "default"),
        "entity": lambda: entity.search("Alice", "default"),
        "temporal": lambda: temporal.search("Alice March 2025", "default"),
        "recall": lambda: engine.recall("Alice March 2025 memory release", "default"),
    }
    queries = {}
    execute = db.execute

    def traced(sql, params=()):
        if sql.lstrip().upper().startswith("SELECT") and sql not in queries:
            queries[sql] = params
        return execute(sql, params)

    output = {}
    db.execute = traced
    try:
        for name, call in calls.items():
            output[name] = measure(call, samples)
            profiler = cProfile.Profile()
            profiler.runcall(call)
            profiler.dump_stats(str(directory / f"{label}-{name}.prof"))
    finally:
        engine.close(wait=True)
        db.execute = execute
    plans = {sql: [tuple(r) for r in execute("EXPLAIN QUERY PLAN " + sql, params)]
             for sql, params in queries.items()}
    (directory / f"{label}-plans.json").write_text(json.dumps(plans, indent=2))
    return output


def synthetic_path(directory: Path, facts: int) -> tuple[Path, bool]:
    """Reject existing unmarked stores and paths outside TMPDIR before opening SQLite."""
    root = Path(os.environ.get("TMPDIR", "/tmp")).resolve()
    directory = directory.resolve()
    if not directory.is_relative_to(root) or directory == root:
        raise ValueError("profiler directory must be inside TMPDIR")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "synthetic.db"
    if path.is_symlink():
        raise ValueError("synthetic database must not be a symlink")
    marker = directory / "synthetic-store.json"
    expected = {"seeder": "wp4b-recall-channels-v1", "facts": facts}
    if path.exists():
        if not marker.is_file() or json.loads(marker.read_text()) != expected:
            raise ValueError("existing database was not seeded by this profiler")
        return path, False
    marker.write_text(json.dumps(expected))
    return path, True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--facts", type=int, default=30000)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--label", default="before")
    args = parser.parse_args()
    if args.facts < 2 or args.samples < 1:
        parser.error("facts must be >= 2 and samples must be >= 1")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.label):
        parser.error("label must contain only letters, numbers, underscores or hyphens")
    path, needs_seed = synthetic_path(args.directory, args.facts)
    db = DatabaseManager(path)
    if needs_seed:
        seed(db, args.facts)
    result = profile_calls(db, args.directory, args.samples, args.label)
    (args.directory / f"{args.label}.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({name: {k: v for k, v in row.items() if k.endswith("_ms")}
                      for name, row in result.items()}, indent=2))
    db.close()


if __name__ == "__main__":
    main()
