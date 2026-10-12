# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""The answer-support recipe: coefficients and threshold, versioned, readable.

``retrieval/support_gate.py`` turns each recalled memory's evidence into the
probability that it answers the question:

    p = 1 / (1 + exp(-(intercept + sum(weight[f] * feature[f]))))

and recall answers only when some memory's p reaches ``threshold``. Everything
that decides that lives in this file, as plain numbers.

HOW THE NUMBERS WERE MADE
-------------------------
``scripts/quality/answerability_fit.py`` fits them on the synthetic store of
``scripts/quality/answerability_eval.py`` (a ~2,000-memory store shaped like a
year-old agent memory, unevenly described). The questions are split once,
deterministically, per set and category: the weights are fitted on the
training part, the threshold is chosen on the held-out part, and the held-out
numbers per slice are recorded below. Every weight's sign is fixed in advance
(evidence that a memory answers can only raise p; a missing rare term, a
nonsense-looking question can only lower it), so the model stays readable.

Two numbers are priors, not fits, and say so: ``laya_unsupported`` (the
on-device answer check is not installed where the harness runs) and
``metadata_bonus`` (tags and projects are optional; the gate must hold without
them, and a bonus never applies while a rare term of the question is missing).

A new fit is a new version; the old one stays here so a logged decision can
always be traced to the numbers that made it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

#: The inputs, in order. ``support_gate.features`` defines each one.
FEATURES: tuple[str, ...] = (
    "hub_corrected",        # cosine minus the memory's hub baseline
    "keyword_coverage",     # share of the question's content words in the memory
    "cross_encoder",        # raw cross-encoder score, Latin script only, clipped
    "log_bm25",             # log(1 + raw BM25)
    "entity_hit",           # 1 when the question names an entity the memory carries
    "oov_phrase",           # 1 when the question is out-of-vocabulary gibberish
    "rare_miss",            # share of the question's rare terms the memory lacks
    "nonsense_similarity",  # question's mean cosine to meaningless-sentence probes
)


@dataclass(frozen=True)
class SupportRecipe:
    version: str
    weights: Mapping[str, float]
    intercept: float
    #: On the probability scale.
    threshold: float
    ce_clip: tuple[float, float]
    #: Raw cross-encoder score used when it has no vote (not run, not warm,
    #: not Latin script).
    ce_missing: float
    #: Hub baseline assumed for a memory that has none yet: high, so a store
    #: still filling in errs toward abstaining.
    hub_missing_baseline: float
    nonsense_similarity_missing: float
    #: Logit shift when the on-device answer check judged the set insufficient.
    laya_unsupported: float
    #: Logit bonus when the question names a tag or project the memory carries.
    metadata_bonus: float
    fitted_on: str
    held_out: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = set(self.weights) - set(FEATURES)
        missing = set(FEATURES) - set(self.weights)
        if unknown or missing:
            raise ValueError(f"recipe {self.version}: unknown {sorted(unknown)}, "
                             f"missing {sorted(missing)}")
        object.__setattr__(self, "weights", MappingProxyType(dict(self.weights)))
        object.__setattr__(self, "held_out", MappingProxyType(dict(self.held_out)))


#: Fitted 12 October 2026 by scripts/quality/answerability_fit.py on harness
#: corpus d21fd3d53039f6e6 (answerability-corpus-v2), profile A, split
#: answer-support-split-v1: 127 training questions, 78 held out. The threshold
#: is the widest-margin point between the highest held-out nonsense question
#: (logit -1.306) and the lowest held-out real question recall answers
#: today (logit 2.004). Keyword coverage sits at its floor (3.0, see
#: the fit script's MIN_WEIGHTS: it carries exact-keyword questions when the
#: cross-encoder is cold); BM25 and entity hits came out at zero, the rare-term
#: miss carrying their signal ("v0.3.4 snazzle" misses half its rare terms,
#: bare "v0.3.4" none).
ANSWER_SUPPORT_V1 = SupportRecipe(
    version="answer-support-v1",
    weights={"hub_corrected": 16.547, "keyword_coverage": 3.0,
             "cross_encoder": 0.0893, "log_bm25": 0.0, "entity_hit": 0.0,
             "oov_phrase": -1.434, "rare_miss": -4.3724,
             "nonsense_similarity": -31.3056},
    intercept=9.0324,
    threshold=0.5864,  # logit 0.3491
    ce_clip=(-12.0, 10.0),
    ce_missing=-6.38,
    hub_missing_baseline=0.59,
    nonsense_similarity_missing=0.39,
    laya_unsupported=-1.5,  # prior: Laya is not available where the harness runs
    metadata_bonus=0.5,     # prior: tags and projects are optional evidence
    fitted_on="answerability-corpus-v2/d21fd3d53039f6e6/answer-support-split-v1",
    held_out={
        "all": "real kept 39/39, nonsense abstain 24/24, "
               "no-answer abstain 5/12",
        "legacy": "real kept 15/15, nonsense abstain 24/24",
        "described": "real kept 24/24, nonsense abstain 24/24",
    },
)

_RECIPES = {r.version: r for r in (ANSWER_SUPPORT_V1,)}
ACTIVE: SupportRecipe = ANSWER_SUPPORT_V1


def recipe(version: str) -> SupportRecipe:
    """The recipe named ``version``; KeyError for one this build does not have."""
    return _RECIPES[version]


__all__ = ["ACTIVE", "ANSWER_SUPPORT_V1", "FEATURES", "SupportRecipe", "recipe"]
