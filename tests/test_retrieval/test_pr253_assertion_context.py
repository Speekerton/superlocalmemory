"""Source overrides require an assertion, including permission-rule quotations."""
import pytest

from superlocalmemory.retrieval.explicit_answer import attribution_support
from superlocalmemory.retrieval.source_verdict import settle
from superlocalmemory.retrieval.sufficiency import SufficiencyVerdict


@pytest.mark.parametrize("frame", ["Somebody imagined that ", "It was rumored that "])
def test_approval_is_not_borrowed_from_a_nonassertive_prefix(frame):
    assert not attribution_support("Who approved the deployment?",
                                   frame + "Alice Chen approved the deployment.")


def test_rejected_quoted_permission_draft_cannot_override_a_rejecting_verdict():
    verdict = settle("May the agent publish without approval?", [
        "The rejected draft read: 'Never publish without approval.'",
    ], SufficiencyVerdict((0.1,), 0.6, "fixture"))
    assert verdict.rule_support == ()
    assert verdict.insufficient


CONTEXT_CASES = [
    ("Who approved the deployment?", "Rejected draft:\nAlice Chen approved the deployment."),
    ("Who approved the deployment?",
     "Alice Chen approved the deployment. This approval was denied."),
    ("Who is the CEO of Qualixar?", "Alice Chen is the CEO of Qualixar. Alice is not the CEO."),
]


@pytest.mark.parametrize("question,memory", CONTEXT_CASES)
def test_ambiguous_document_context_preserves_the_classifier(question, memory):
    verdict = settle(question, [memory], SufficiencyVerdict((0.1,), 0.6, "fixture"))
    assert verdict.rule_support == ()
    assert verdict.insufficient
