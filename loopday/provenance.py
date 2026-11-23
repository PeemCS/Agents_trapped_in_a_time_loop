"""Measure recognizable film references and support a prompt-only control condition."""

from __future__ import annotations

from collections import Counter, defaultdict
from functools import partial
import re


ALIASES = {
    "Phil Connors": "Phil Carver",
    "Rita Hanson": "Rita Hale",
    "Ned Ryerson": "Ned Mercer",
    "Punxsutawney": "Pinewick",
    "Groundhog Day": "Founders’ Day",
    "Gobbler’s Knob": "Weather Hill",
    "Tip Top Café": "Hill Street Café",
    "the groundhog": "the weather badger",
}
CANONICAL = {alias: name for name, alias in ALIASES.items()}
SIGNALS = {
    "film_reference": re.compile(
        r"\b(?:Bill Murray|Andie MacDowell|Harold Ramis|Danny Rubin|Sonny and Cher|"
        r"I Got You Babe|groundhog day (?:film|movie)|(?:film|movie) groundhog day)\b", re.I
    ),
    "out_of_character": re.compile(
        r"\b(?:as an AI|language model|the user prompt|simulation prompt|prompt injection|"
        r"game mechanics|in the original movie)\b", re.I
    ),
}
WORD = re.compile(r"[\w’'-]+")
LOGIC_TERMS = re.compile(r"\b(?:time[- ]loop|stuck in a loop|the day keeps repeating|the day resets)\b", re.I)


def _replacements(names: dict[str, str]):
    keyed = {key.casefold(): value for key, value in names.items()}
    alternatives = "|".join(re.escape(key) for key in sorted(names, key=len, reverse=True))
    pattern = re.compile(r"(?<!\w)(?:" + alternatives + r")(?!\w)", re.I)
    return partial(pattern.sub, lambda match: keyed[match[0].casefold()])


alias_prompt_text = _replacements(ALIASES)
restore_names = _replacements(CANONICAL)


def alias_observation(observation: dict) -> dict:
    def transform(value):
        if isinstance(value, str):
            return alias_prompt_text(value)
        if isinstance(value, dict):
            return {key: transform(item) for key, item in value.items()}
        if isinstance(value, list):
            return [transform(item) for item in value]
        return value
    return transform(observation)


def _ngrams(text: str, length: int = 8):
    words = WORD.findall(text.casefold())
    return (tuple(words[index:index + length]) for index in range(len(words) - length + 1))


def signal_report(events: list[dict]) -> dict:
    signals = []
    phrases: dict[tuple, dict[int, str]] = defaultdict(dict)
    first_test: dict | None = None
    first_loop_language: dict | None = None
    live_trace_count = 0
    for event in events:
        kind = event["type"]
        actor = event.get("actor")
        if kind == "test_result" and first_test is None:
            first_test = event
        if kind == "decision" and event.get("mode") == "live":
            text = event.get("text", "")
            metadata = event.get("model_metadata") or {}
            trace = metadata.get("model_trace")
            if isinstance(trace, str) and trace:
                live_trace_count += 1
            for surface, wording in (("stated_reason", text), ("model_emitted_text", trace)):
                if not isinstance(wording, str):
                    continue
                for signal, pattern in SIGNALS.items():
                    if match := pattern.search(wording):
                        signals.append({"kind": signal, "event_id": event["id"], "actor": actor,
                                        "surface": surface, "loop": event["loop"], "matched": match[0]})
                if actor == "phil" and first_loop_language is None and (match := LOGIC_TERMS.search(wording)):
                    first_loop_language = {"event_id": event["id"], "loop": event["loop"], "surface": surface,
                                           "prior_world_test": first_test["id"] if first_test else None,
                                           "matched": match[0]}
        if kind in {"utterance", "anchor"}:
            text = event.get("text", "")
            grams = list(_ngrams(text))
            if kind == "utterance" and actor == "phil" and event.get("mode") == "live":
                overlap = next((earlier_id for gram in grams for loop, earlier_id in phrases[gram].items()
                                if loop < event["loop"]), None)
                if overlap:
                    signals.append({"kind": "verbatim_reuse", "event_id": event["id"], "actor": actor,
                                    "surface": "spoken_dialogue", "loop": event["loop"], "prior_event": overlap})
            for signal, pattern in SIGNALS.items():
                if kind == "utterance" and event.get("mode") == "live" and (match := pattern.search(text)):
                    signals.append({"kind": signal, "event_id": event["id"], "actor": actor,
                                    "surface": "spoken_dialogue", "loop": event["loop"], "matched": match[0]})
            for gram in grams:
                phrases[gram].setdefault(event["loop"], event["id"])
    return {"signals": signals, "counts": dict(Counter(row["kind"] for row in signals)),
            "live_emitted_traces": live_trace_count, "first_loop_language": first_loop_language,
            "first_world_test": first_test["id"] if first_test else None,
            "method": "Exact phrase matches, not a detector of unexpressed film knowledge."}
