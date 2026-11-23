"""Evidence-backed observations, discoveries, and practical memories."""

from collections import Counter
from dataclasses import dataclass, field
import math

from .replay import digest, words


def similarity(left: str, right: str) -> float:
    old, new = Counter(words(left)), Counter(words(right))
    if not old or not new:
        return 0.0
    dot = sum(value * new[token] for token, value in old.items())
    return dot / math.sqrt(sum(value * value for value in old.values()) *
                           sum(value * value for value in new.values()))


def _strength(record: dict, loop: int) -> float:
    rate = 0.35 if record["kind"] == "observation" else 0.09
    age = max(0, loop - record.get("last_access_loop", record["loop"]))
    rehearsals = record.get("access_count", 0)
    return min(1.0, record["importance"] * math.exp(-rate * age) + 0.15 * math.log1p(rehearsals))


@dataclass
class Memory:
    records: list[dict] = field(default_factory=list)

    def observe(self, loop: int, event: dict, importance: float = 0.8, valence: float = 0.0) -> dict:
        location = event.get("location")
        importance = min(1.0, max(0.0, importance + 0.20 * abs(valence)))
        normalized = " ".join(words(event["text"]))
        key = digest(normalized)
        for record in reversed(self.records):
            if record.get("key") in {key, normalized} and record.get("location") == location:
                record.update({
                    "event_id": event["id"], "text": event["text"], "fuzzed": False,
                    "original_text": event["text"], "key": key,
                    "verbatim": event["text"], "last_access_loop": loop,
                    "importance": max(record["importance"], importance),
                    "access_count": record.get("access_count", 0) + 1,
                    "event_ids": [*record.get("event_ids", [])[-7:], event["id"]],
                    "operation": "UPDATE",
                })
                if event.get("appointment"):
                    record["appointment"] = event["appointment"].copy()
                return record
        record = {
            "id": f"m-{event['id']}", "kind": "observation", "loop": loop,
            "tick": event.get("tick"), "event_id": event["id"], "event_ids": [event["id"]],
            "text": event["text"], "verbatim": event["text"] if importance >= 0.7 else None,
            "original_text": event["text"],
            "key": key, "importance": importance, "location": location, "fuzzed": False,
            "valence": valence, "access_count": 0, "last_access_loop": loop, "operation": "ADD",
        }
        if event.get("appointment"):
            record["appointment"] = event["appointment"].copy()
        self.records.append(record)
        return record

    def consolidate(self, loop: int, kind: str, text: str, evidence: dict, *,
                    pinned: bool = False) -> dict:
        if kind not in {"belief", "skill", "reflection"}:
            raise ValueError(f"Unknown memory kind: {kind}")
        record = {
            "id": f"m-{evidence['id']}-{kind}", "kind": kind, "loop": loop, "tick": evidence.get("tick"),
            "event_id": evidence["id"], "event_ids": [evidence["id"]],
            "dependencies": [evidence["source_event"]] if evidence.get("source_event") else [],
            "text": text, "importance": 0.9 if pinned else 0.8,
            "location": evidence.get("location"), "fuzzed": False, "pinned": pinned,
            "valence": 0.0, "access_count": 0, "last_access_loop": loop, "operation": "ADD",
        }
        self.records.append(record)
        return record

    def recall(
        self, loop: int, location: str, limit: int = 8, *, query: str = "",
        valence: float = 0.0, withheld: frozenset[str] = frozenset(), touch: bool = False,
    ) -> list[dict]:
        earlier = [
            record for record in self.records
            if (record["loop"] < loop or
                (record["loop"] == loop and record["kind"] in {"belief", "skill", "reflection"}))
            and record.get("id") not in withheld and record["event_id"] not in withheld
            and withheld.isdisjoint(record.get("event_ids", []))
            and withheld.isdisjoint(record.get("dependencies", []))
        ]

        def relevance(record: dict) -> tuple:
            recency = math.exp(-0.45 * (loop - record.get("last_access_loop", record["loop"])))
            affect = 1 - abs(valence - record.get("valence", 0.0)) / 2
            score = (
                0.42 * similarity(query, record["text"])
                + 0.24 * _strength(record, loop)
                + 0.14 * recency + 0.10 * affect
                + 0.10 * (record.get("location") == location)
            )
            return bool(record.get("pinned") or record.get("appointment")), score, record["loop"]

        ranked = sorted(earlier, key=relevance, reverse=True)[:limit]
        if touch:
            for record in ranked:
                record["access_count"] = record.get("access_count", 0) + 1
                record["last_access_loop"] = loop
        return [{
            "event_id": record["event_id"], "kind": record["kind"],
            "text": record["text"], "fuzzed": record.get("fuzzed", False),
            **({"appointment": record["appointment"].copy()} if record.get("appointment") and not record.get("fuzzed") else {}),
        } for record in ranked]

    def deja_vu(
        self, loop: int, text: str, withheld: frozenset[str] = frozenset(),
    ) -> tuple[float, str | None]:
        strongest, evidence = 0.0, None
        needle = words(text)
        for record in self.records:
            if (record["kind"] != "observation" or record["loop"] >= loop or record.get("id") in withheld
                    or record["event_id"] in withheld
                    or not withheld.isdisjoint(record.get("event_ids", []))):
                continue
            if record.get("verbatim") and words(record["verbatim"]) == needle:
                return 1.0, record["event_id"]
            score = similarity(text, record["text"])
            if score > 0.6:
                score *= 0.9 * (0.7 if record.get("fuzzed") else 1.0)
                if score > strongest:
                    strongest, evidence = score, record["event_id"]
        return round(strongest, 3), evidence

    def rehearse(self, loop: int, sources: list[str], *, valence: float, seed: int,
                 decision: str) -> list[tuple[dict, str]]:
        """Strengthen cited memories and occasionally change their emotional coloring."""
        changed = []
        for record in self.records:
            if record["event_id"] not in sources or record["loop"] >= loop:
                continue
            record["access_count"] = record.get("access_count", 0) + 1
            record["last_access_loop"] = loop
            chance = int(digest([seed, loop, record.get("id"), decision])[:8], 16) / 2**32
            if record["kind"] != "observation" or record.get("fuzzed") or chance >= 0.2:
                continue
            tone = ("The memory feels colder now." if valence < -0.20 else
                    "The detail feels a little more hopeful now." if valence > 0.20 else
                    "That detail seems worth keeping in mind.")
            before = record["text"]
            original = record.setdefault("original_text", before)
            after = f"{original} {tone}"
            if after != before:
                record["text"] = after
                changed.append((record, before))
        return changed

    def fade(self, loop: int) -> list[tuple[str, dict]]:
        operations = []
        kept = []
        for record in self.records:
            strength = _strength(record, loop)
            record["strength"] = round(strength, 4)
            if record.get("pinned"):
                kept.append(record)
                continue
            if strength < 0.14:
                operations.append(("DELETE", record))
                continue
            if strength < 0.30 and not record.get("fuzzed"):
                record = {
                    **record, "fuzzed": True, "verbatim": None,
                    "text": f"A hazy recollection associated with {record['location'] or 'town'}.",
                }
                record.pop("original_text", None)
                record.pop("appointment", None)
                if record.get("key") and len(record["key"]) != 64:
                    record["key"] = digest(record["key"])
                operations.append(("FUZZ", record))
            kept.append(record)
        self.records = kept
        return operations
