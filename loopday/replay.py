"""Replay decisions only when their public inputs agree."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata


_STOPWORDS = frozenset("a an are can could i is it please the to would you".split())
_GREETING_WORDS = frozenset("afternoon evening good hello hey hi morning there".split())
_CAST_NAMES = frozenset("connors hanson larry ned phil rita ryerson".split())
_DAYPARTS = frozenset({"morning", "afternoon", "evening"})
_COURTESY_WORDS = frozenset({"please"})
_NUMERALS = re.compile(r"(?<!\w)[+−-]?\d+(?:[.:,/]\d+)*%?")


def digest(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def words(text: str) -> tuple[str, ...]:
    lowered = unicodedata.normalize("NFKC", text.casefold()).replace("’", "'")
    lowered = re.sub(r"\b(?:can't|cannot)\b", " not ", lowered)
    lowered = re.sub(r"n['’]t\b", " not ", lowered)
    return tuple(re.findall(r"[\w]+", lowered))


def utterance_intent(text: str) -> str:
    tokens = set(words(text))
    if tokens and tokens <= _GREETING_WORDS | _CAST_NAMES | _STOPWORDS:
        return "greeting"
    if tokens & {"danger", "careful", "watch", "avoid", "warning"}:
        return "warning"
    if tokens & {"thank", "thanks", "appreciate"}:
        return "gratitude"
    if text.rstrip().endswith("?"):
        return "question"
    return "statement"


def scene_item(event: dict, actor: str | None = None) -> dict:
    """Key facts from a witnessed event, excluding run-local identity and layout labels."""
    kind = event["type"]
    item = {
        "type": kind,
        "actor": event.get("actor"),
        "target": event.get("to"),
        "location": event.get("location"),
        "action": event.get("action"),
        "anchor": event.get("anchor"),
        "subject": event.get("subject"),
        "status": event.get("status"),
        "state": event.get("state"),
        "text": event["text"],
    }
    if kind == "utterance":
        item["intent"] = event.get("intent") or utterance_intent(event["text"])
    if actor and actor in event.get("transport", {}).get("verified_recipients", []):
        item["verified_delivery"] = True
    return item


def _similar_utterance(before: str, after: str, intent: str) -> bool:
    if intent == "greeting":
        old_terms = set(words(before)) - _STOPWORDS
        new_terms = set(words(after)) - _STOPWORDS
        old_time, new_time = old_terms & _DAYPARTS, new_terms & _DAYPARTS
        same_time = not (old_time and new_time) or old_time == new_time
        return same_time and old_terms - _GREETING_WORDS == new_terms - _GREETING_WORDS
    # Keep all content words, including unfamiliar names and place names. A
    # high lexical overlap alone can hide a changed time, quantity, or request.
    old = tuple(token for token in words(before) if token not in _COURTESY_WORDS)
    new = tuple(token for token in words(after) if token not in _COURTESY_WORDS)
    return bool(old) and old == new and _NUMERALS.findall(before) == _NUMERALS.findall(after)


def same_scene_item(previous: dict, current: dict) -> bool:
    if previous == current:
        return True
    if previous.get("type") != "utterance" or current.get("type") != "utterance":
        return False
    before, after = previous.copy(), current.copy()
    before_text, after_text = before.pop("text"), after.pop("text")
    return before == after and _similar_utterance(before_text, after_text, before["intent"])


def comparable(observation: dict, events: list[dict]) -> dict:
    return {
        "tick": observation["tick"],
        "location": observation["location_id"],
        "present": sorted(observation["present"]),
        "actions": sorted(observation["actions"]),
        "daily_facts": observation.get("daily_facts", []),
        "relationship": observation.get("relationship"),
        "world": observation["world"],
        "scene": [scene_item(event, observation["actor"]) for event in events],
    }


def match(previous: dict, current: dict) -> str | None:
    if previous == current:
        return "exact"
    before, after = previous.copy(), current.copy()
    before_scene, after_scene = before.pop("scene"), after.pop("scene")
    if before != after or len(before_scene) != len(after_scene):
        return None
    if all(same_scene_item(old, new) for old, new in zip(before_scene, after_scene)):
        return "semantic"
    return None


def changed_event(previous: dict | None, current_events: list[dict], actor: str) -> dict | None:
    if previous is None:
        return current_events[-1] if current_events else None
    old = previous["scene"]
    additions = [
        event for event in current_events
        if not any(same_scene_item(entry, scene_item(event, actor)) for entry in old)
    ]
    # A newly witnessed consequence is more specific than a shifted commute or a
    # different item at the start of a fixed-length observation buffer.
    substantive = [item for item in additions if item["type"] not in {"position", "anchor"}]
    if substantive:
        return substantive[-1]
    return additions[-1] if additions else None
