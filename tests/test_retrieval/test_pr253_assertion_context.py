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
