"""Summarize physical story outcomes and the model's measured outputs by day."""

from __future__ import annotations

from collections import Counter, defaultdict
import math
import re
from statistics import fmean


RITA_ACTIONS = frozenset({"talk:rita", "invite_rita"})
NAMES_RITA = re.compile(r"\bRita\b", re.I)


def _projections(rows: list[dict]) -> dict:
    axes = defaultdict(list)
    for row in rows:
        metadata = row.get("model_metadata") or {}
        bank = metadata.get("persona_bank")
        revision = metadata.get("model_revision")
        scores = metadata.get("projection_z")
        if not (isinstance(bank, str) and isinstance(revision, str) and isinstance(scores, dict)):
            continue
        for axis, score in scores.items():
            if type(score) in (float, int) and math.isfinite(score):
                axes[(bank, revision, axis)].append(score)
    return [{"bank": bank, "model_revision": revision, "axis": axis, "mean_z": fmean(scores), "n": len(scores)}
            for (bank, revision, axis), scores in sorted(axes.items())]


def summarize_days(events: list[dict]) -> list[dict]:
    loops = defaultdict(list)
    for event in events:
        loops[event["loop"]].append(event)
    report = []
    for loop, rows in loops.items():
        night = next((row for row in reversed(rows) if row["type"] == "night"), None)
        phil = [row for row in rows if row["type"] == "decision" and row.get("actor") == "phil"]
        choices = [row for row in rows if row["type"] == "decision"]
        npc = [row for row in choices if row.get("actor") != "phil"]
        rita_available = [row for row in phil if RITA_ACTIONS.intersection(row.get("available_actions", []))]
        mentioned = sum(bool(NAMES_RITA.search(row["text"])) for row in rita_available)
        targeted = sum(row["action"] in RITA_ACTIONS for row in rita_available)
        rewards = [float(row["reward"]) for row in phil if type(row.get("reward")) in (int, float)]
        report.append({
            "loop": loop, "complete": night is not None, "ending": night.get("ending") if night else None,
            "ending_reason": night.get("ending_reason") if night else None,
            "event_count": len(rows), "decisions_by_mode": dict(Counter(row.get("mode", "unknown") for row in choices)),
            "npc_replay_decisions": sum(row.get("mode") == "replay" for row in npc),
            "npc_fresh_decisions": sum(row.get("mode") in {"fixture", "live", "local_policy"} for row in npc),
            "divergence_events": sum(row["type"] == "divergence" for row in rows),
            "evidence_uses": [row["id"] for row in rows if row["type"] == "evidence_use"],
            "first_test_result": next((row["id"] for row in rows if row["type"] == "test_result"), None),
            "reflections": [row["id"] for row in rows if row["type"] == "reflection"],
            "phase_timeline": [{"tick": row["tick"], "phase": row["phase"], "event_id": row["id"]}
                               for row in rows if row["type"] == "emotion" and "phase" in row],
            "memory_count": night.get("memory_count") if night else None,
            "memory_ops": dict(Counter(row["op"] for row in rows if row["type"] == "memory" and "op" in row)),
            "relationship_at_night": night.get("relationship") if night else None,
            "gate_at_night": night.get("gate_level") if night else None,
            "mean_phil_reward": fmean(rewards) if rewards else None,
            "targeting_rita": {"n": len(rita_available), "targeted_choices": targeted, "reasons_naming_rita": mentioned},
            "calibrated_projections": _projections(phil),
        })
    return report
