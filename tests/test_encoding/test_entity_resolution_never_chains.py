# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""Two different things are never made one entity, and merges never chain.

Measured on the author's 26k-fact store (4.1.25 audit): 71% of the entity
links on freshly written notes were wrong. The resolver merged any name whose
whole-string Jaro-Winkler score reached 0.85 against a canonical name OR an
alias, and each such merge wrote an alias the next name could match: one
entity, "Lost", collected 145 aliases (Cost, Post, Last, PostgreSQL, ...), and
a question about "Plorth" landed on it through the alias "Plot".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from superlocalmemory.encoding.entity_resolver import EntityResolver
from superlocalmemory.retrieval.entity_channel import extract_query_entities
from superlocalmemory.storage import schema as real_schema
from superlocalmemory.storage.database import DatabaseManager
from superlocalmemory.storage.models import CanonicalEntity, EntityAlias

P = "default"

#: Each pair scored >= 0.85 and was auto-merged before 4.1.25 (ENGINE-AUDIT H1
#: and LOCAL-TEST finding 1).
DISTINCT_PAIRS = [
    ("AgentAssert", "AgentAssay"),
    ("SLM 4.1.24", "SLM 4.1.25"),
    ("Python 3.12", "Python 3.14"),
    ("Claude Code", "Claude Opus"),
    ("Gemini 3.1 Pro", "Gemini 3.8 Flash"),
    ("John Smith", "John Smyth"),
    ("Qualixar OS", "Qualixar"),
    ("Opus 4.5", "Opus 4.6"),
    ("Meena", "Menon"),
    ("Sanjay", "Sajal"),
    ("Wants", "Warren"),
    ("Rao Builders", "Built"),
    ("Warranty", "Wants"),
]

#: Names the old alias set of "Lost" held on the author's store.
LOST_ALIASES = ["Cost", "Post", "Last", "Logs", "Plot", "PostgreSQL", "Podcasts", "Vlogs",
                "Astro", "BLAST", "MONSTER"]


@pytest.fixture()
def db(tmp_path: Path) -> DatabaseManager:
    mgr = DatabaseManager(tmp_path / "memory.db")
    mgr.initialize(real_schema)
    return mgr


@pytest.fixture()
def chained(db: DatabaseManager) -> DatabaseManager:
    """A store holding the old chained alias set of "Lost"."""
    db.store_entity(CanonicalEntity(entity_id="e_lost", profile_id=P, canonical_name="Lost"))
    db.store_alias(EntityAlias(entity_id="e_lost", alias="Lost", source="canonical"), P)
    for alias in LOST_ALIASES:
        db.store_alias(EntityAlias(entity_id="e_lost", alias=alias, confidence=0.9,
                                   source="jaro_winkler"), P)
    return db


@pytest.mark.parametrize(("first", "second"), DISTINCT_PAIRS)
def test_different_names_never_become_one_entity(db, first, second) -> None:
    resolver = EntityResolver(db, llm=None)
    a = resolver.resolve([first], P)[first]
    b = resolver.resolve([second], P)[second]
    assert a != b, f"{first!r} and {second!r} were merged"


def test_three_near_names_do_not_chain(db) -> None:
    """Kubernetes <- Kubernets is one typo; Kubernet is one typo from the
    alias but two from the entity's name, so it must not join."""
    resolver = EntityResolver(db, llm=None)
    root = resolver.resolve(["Kubernetes"], P)["Kubernetes"]
    assert resolver.resolve(["Kubernets"], P)["Kubernets"] == root
    assert resolver.resolve(["Kubernet"], P)["Kubernet"] != root


def test_a_long_chain_of_near_names_stays_apart(db) -> None:
    resolver = EntityResolver(db, llm=None)
    names = ["Wants", "Wan", "Warren", "Wang", "Watt", "Yang"]
    ids = [resolver.resolve([n], P)[n] for n in names]
    assert len(set(ids)) == len(names)


@pytest.mark.parametrize(("variant", "name"), [
    ("agentassert", "AgentAssert"),
    ("Wi-Fi", "WiFi"),
    ("Super Local Memory", "SuperLocalMemory"),
    ("Qualixar's", "Qualixar"),
    ("GPT-4", "GPT4"),
    ("Elodie Marchand", "Élodie Marchand"),
    ("Kubernets", "Kubernetes"),
    ("Alice Smitth", "Alice Smith"),
    ("Kestrel Harbor", "Kestrel Harbour"),
])
def test_true_variants_still_merge(db, variant, name) -> None:
    resolver = EntityResolver(db, llm=None)
    root = resolver.resolve([name], P)[name]
    assert resolver.resolve([variant], P)[variant] == root


def test_old_fuzzy_aliases_are_never_matched_again(chained) -> None:
    resolver = EntityResolver(chained, llm=None)
    out = resolver.resolve(["Plorth", "Postgres", "PostgreSQL", "Post"], P)
    assert "e_lost" not in out.values(), out


def test_a_merge_writes_an_alias_that_no_fuzzy_rule_will_use(db) -> None:
    resolver = EntityResolver(db, llm=None)
    root = resolver.resolve(["Kubernetes"], P)["Kubernetes"]
    resolver.resolve(["Kubernets"], P)
    sources = {dict(r)["alias"]: dict(r)["source"] for r in db.execute(
        "SELECT alias, source FROM entity_aliases WHERE entity_id = ?", (root,))}
    assert sources["Kubernets"] == "typo"


class _Model:
    def __init__(self, answer: bool) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    def generate(self, prompt: str, **_kw) -> str:
        self.prompts.append(prompt)
        n = prompt.count("\n- ") or 1
        return json.dumps({str(i + 1): self.answer for i in range(n)})


def test_mode_a_keeps_a_borderline_pair_apart(db) -> None:
    resolver = EntityResolver(db, llm=None)
    a = resolver.resolve(["PostgreSQL"], P)["PostgreSQL"]
    assert resolver.resolve(["Postgres"], P)["Postgres"] != a


def test_mode_b_merges_a_borderline_pair_only_when_the_model_says_so(db) -> None:
    yes = EntityResolver(db, llm=_Model(True))
    a = yes.resolve(["PostgreSQL"], P)["PostgreSQL"]
    assert yes.resolve(["Postgres"], P)["Postgres"] == a
    no = EntityResolver(db, llm=_Model(False))
    assert no.resolve(["John Smyth"], P)["John Smyth"] != no.resolve(
        ["John Smith"], P)["John Smith"]


def test_the_model_is_never_asked_about_names_whose_numbers_differ(db) -> None:
    model = _Model(True)
    resolver = EntityResolver(db, llm=model)
    a = resolver.resolve(["Python 3.12"], P)["Python 3.12"]
    assert resolver.resolve(["Python 3.14"], P)["Python 3.14"] != a
    b = resolver.resolve(["AgentAssert"], P)["AgentAssert"]
    assert resolver.resolve(["AgentAssay"], P)["AgentAssay"] != b
    assert model.prompts == []


def test_a_nonsense_question_finds_nothing_in_a_chained_store(chained) -> None:
    resolver = EntityResolver(chained, llm=None)
    names = extract_query_entities("zxqv plorth wimble")
    assert names == []
    assert resolver.lookup(["Zxqv", "Plorth", "Wimble"], P) == {}


def test_a_question_is_at_least_as_strict_as_a_save(db) -> None:
    resolver = EntityResolver(db, llm=None)
    resolver.resolve(["AgentAssert", "SLM 4.1.24", "Claude Code"], P)
    assert resolver.lookup(["AgentAssay", "SLM 4.1.25", "Claude Opus", "Post"], P) == {}
    found = resolver.lookup(["agentassert", "Agent Assert"], P)
    assert set(found) == {"agentassert", "Agent Assert"}


def test_an_old_model_alias_is_not_trusted_until_repaired(db) -> None:
    """The pre-4.1.25 model mapping filed "Priya" under "gdrive"."""
    db.store_entity(CanonicalEntity(entity_id="e_g", profile_id=P, canonical_name="gdrive"))
    db.store_alias(EntityAlias(entity_id="e_g", alias="Priya", source="llm"), P)
    resolver = EntityResolver(db, llm=None)
    assert resolver.lookup(["Priya"], P) == {}
    assert resolver.resolve(["Priya"], P)["Priya"] != "e_g"


def test_a_question_uses_no_old_fuzzy_alias_even_spelled_exactly(chained) -> None:
    resolver = EntityResolver(chained, llm=None)
    assert resolver.lookup(["Plot", "PostgreSQL", "Podcasts"], P) == {}
    assert resolver.lookup(["Lost"], P) == {"Lost": "e_lost"}
