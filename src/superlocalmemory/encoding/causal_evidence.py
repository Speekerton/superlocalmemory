"""Conservative source-backed cause endpoints; a shared entity is not evidence."""
import re
from datetime import datetime, timezone

WINDOW_SECONDS = 7 * 86400
_BACKWARD = re.compile(r"\b(?:because(?: of)?|caused by|due to)\b", re.I)
_FORWARD = re.compile(r"\b(?:led to|resulted in|therefore|consequently|as a result)\b", re.I)
_UNASSERTED = re.compile(r"\b(?:not|never|might|may|would|could|if|unless)\b", re.I)
_STOP = {"the", "a", "an", "of", "by", "is", "was", "were", "has", "had"}


def _tokens(text):
    return set(re.findall(r"\w+", text.casefold())) - _STOP


def cause_clause(text):
    """Extract an asserted cause span, abstaining on purpose/negation/hypothesis."""
    if _UNASSERTED.search(text):
        return None
    cue = _BACKWARD.search(text)
    if cue:
        return text[cue.end():].strip(" .,")
    cue = _FORWARD.search(text)
    return text[:cue.start()].strip(" .,") if cue else None


def _time(fact):
    raw = fact.referenced_date or fact.observation_date or fact.created_at
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (ValueError, AttributeError):
        return None


def supports_cause(prior, effect, clause):
    """Cause words must be present in a prior observation within one week."""
    cause_time, effect_time = _time(prior), _time(effect)
    if cause_time is None or effect_time is None or _UNASSERTED.search(prior.content):
        return False
    elapsed = (effect_time - cause_time).total_seconds()
    words = _tokens(clause)
    return 0 < elapsed <= WINDOW_SECONDS and len(words) >= 2 and words <= _tokens(prior.content)
