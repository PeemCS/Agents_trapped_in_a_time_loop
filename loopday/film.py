"""Choose a chronological film cut from LOOPDAY event logs."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


PLAN_VERSION = 1
MIN_SECONDS = 60
MAX_SECONDS = 175
MAX_SHOTS = 33
SPEAKING_TYPES = {"utterance", "invitation", "reply", "dialogue", "recognition"}
KIND_PRIORITY = {
    "test_result": 95,
    "puddle": 87,
    "prediction": 86,
    "performance": 93,
    "kindness": 78,
    "kindness_offered": 78,
    "exit": 74,
    "reply": 91,
    "invitation": 82,
    "divergence": 67,
    "npc_mode": 67,
    "skill": 70,
    "skill_up": 70,
    "suspicion_spike": 77,
    "recognition": 76,
    "day_two": 100,
}
ANCHOR_PRIORITY = {"radio": 99, "ned_greeting": 89, "snow": 80, "party": 77, "ceremony": 83}
EDIT_LINKS = ("evidence", "action_evidence", "prediction", "observation", "source_event")


def text_for(event: dict[str, Any]) -> str:
    """Read display text from either the prototype or the ZIP's field names."""
    for field in ("line", "text", "outcome_text", "utterance", "description"):
        value = event.get(field)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    return ""


def cast_member(run: dict, actor: str | None) -> str:
    character = run.get("cast", {}).get(actor, {})
    if isinstance(character, dict):
        return str(character.get("name") or actor or "")
    return str(character or actor or "")


def shot_style(event: dict) -> tuple[str, int, str | None]:
    kind, anchor = event.get("type"), event.get("anchor")
    if kind == "day_two":
        return "clock", 4_100, "tomorrow"
    if kind == "day_start" or anchor == "radio":
        return "clock", 3_150, "radio"
    if kind in {"pencil", "test_result", "prediction", "experiment_result"}:
        return "insert", 3_450, "snap" if event.get("state") == "broken" else None
    if anchor == "snow" or kind == "exit":
        return "road", 3_600, "steps" if event.get("state") == "left_town" else "wind"
    if anchor == "ceremony":
        return "square", 3_600, "bell"
    if event.get("subject") == "kid_tree" and kind in {"kindness", "world_event"}:
        return "tree", 3_450, "snap" if event.get("status") == "resolved_unhelped" else None
    if kind == "puddle":
        avoided = event.get("avoided", {"dry": True, "wet": False}.get(event.get("state")))
        if avoided is None:
            line = text_for(event).lower()
            avoided = "around" in line or "avoid" in line
        return "puddle", 3_000, None if avoided else "splash"
    if kind in {"performance", "skill", "skill_up"}:
        return "piano", 4_250, "piano" if kind == "performance" else "practice"
    if anchor == "party":
        return "ballroom", 3_700, None
    if kind in {"kindness", "kindness_offered"}:
        return ("ballroom" if event.get("location") == "hotel" else "two_shot"), 3_700, None
    if kind in SPEAKING_TYPES or anchor == "ned_greeting":
        return "two_shot", 2_250, None
    if kind == "position":
        return "walk", 2_300, "steps"
    if kind == "night":
        return "night", 3_200, None
    return "street", 2_300, None


def _score(event: dict, last_loop: int) -> int:
    kind, anchor = event.get("type"), event.get("anchor")
    if anchor in ANCHOR_PRIORITY:
        return ANCHOR_PRIORITY[anchor]
    if kind in KIND_PRIORITY:
        return KIND_PRIORITY[kind]
    if kind == "pencil" and event.get("state") == "broken":
        return 89
    if kind in SPEAKING_TYPES and text_for(event):
        return 70
    if kind == "position" and event.get("actor", event.get("agent")) == "phil":
        return 46
    if kind == "night" and event.get("loop") == last_loop:
        return 82
    if kind == "experiment_result" and text_for(event):
        return 76
    return 0


def _select(events: list[dict]) -> list[int]:
    loops = sorted({event.get("loop", 1) for event in events})
    last_loop = loops[-1]
    noteworthy = {1, last_loop}
    matching_rescues = {event.get("subject") for event in events if event.get("type") == "kindness"}
    by_id = {event.get("id"): event for event in events if event.get("id")}
    important = _credited_events(events, by_id)
    for event in events:
        if event.get("type") in {"test_result", "experiment_result", "skill", "performance"}:
            noteworthy.add(event.get("loop", 1))
            # Retain the action that made a next-morning result meaningful.
            evidence = event.get("action_evidence")
            if evidence in by_id:
                noteworthy.add(by_id[evidence].get("loop", 1))
            if len(noteworthy) >= 5:
                break

    seen_anchors: set[tuple[str, int]] = set()
    seen_lines: set[tuple[int, str, str]] = set()
    hits: list[tuple[int, int]] = []
    for index, event in enumerate(events):
        loop, kind, anchor = event.get("loop", 1), event.get("type"), event.get("anchor")
        if loop not in noteworthy and kind != "day_two" and event.get("id") not in important:
            continue
        if anchor in {"ceremony", "snow", "party"} and loop not in {1, last_loop}:
            continue
        if isinstance(anchor, str):
            marker = anchor, loop
            if marker in seen_anchors:
                continue
            seen_anchors.add(marker)
        if kind in SPEAKING_TYPES:
            signature = (loop, event.get("actor") or "", text_for(event).casefold())
            if signature in seen_lines:
                continue
            seen_lines.add(signature)
        priority = _score(event, last_loop)
        if kind == "world_event" and event.get("subject") in matching_rescues and text_for(event):
            active = event.get("status") == "active"
            if active or (loop == loops[0] and event.get("status") == "resolved_unhelped"):
                priority = 72 if active else 69
        if priority and event.get("id") in important:
            priority = max(96, priority)
        if priority and kind == "night" and events[-1].get("type") == "day_two":
            continue
        if priority:
            hits.append((priority, index))
    selected = sorted(index for _, index in sorted(hits, key=lambda item: (-item[0], item[1]))[:MAX_SHOTS])
    return selected or [0]


def _credited_events(events: list[dict], by_id: dict) -> set[str]:
    """Prefer the world events explicitly linked to the ending or a test."""
    pending = [event for event in events if event.get("type") in {"ending_decision", "test_result"}]
    credited = set()
    while pending:
        event = pending.pop()
        for key in EDIT_LINKS:
            value = event.get(key)
            for target in value if isinstance(value, list) else (value,):
                if isinstance(target, str) and target in by_id and target not in credited:
                    credited.add(target)
                    pending.append(by_id[target])
    return credited


def _stretch(shots: list[dict], target_ms: int) -> None:
    total = sum(shot["duration_ms"] for shot in shots)
    if total == 0:
        return
    # Never manufacture a feature-length result from an empty or broken run.
    duration = min(target_ms, sum(max(6_800, shot["duration_ms"]) for shot in shots))
    if abs(total - duration) < 20:
        return
    elapsed = 0
    previous = 0
    for shot in shots:
        elapsed += shot["duration_ms"]
        next_time = round(elapsed * duration / total)
        shot["duration_ms"] = next_time - previous
        previous = next_time


def build_film(run: dict, target_seconds: float = 94) -> dict:
    if not math.isfinite(target_seconds) or not MIN_SECONDS <= target_seconds <= MAX_SECONDS:
        raise ValueError(f"Film target must be {MIN_SECONDS}–{MAX_SECONDS} seconds.")
    events = run.get("events")
    if not isinstance(events, list) or not events or any(not isinstance(event, dict) for event in events):
        raise ValueError("The run needs at least one valid event.")
    selected = set(_select(events))
    positions = {}
    shots = []
    for event_index, event in enumerate(events):
        if isinstance(event.get("positions"), dict):
            positions.update(event["positions"])
        actor = event.get("actor", event.get("agent", event.get("speaker")))
        if event.get("type") == "position" and actor and event.get("location"):
            positions[actor] = event["location"]
        if event_index not in selected:
            continue
        camera, hold_ms, sound = shot_style(event)
        kind = event.get("type")
        caption = text_for(event) if camera != "clock" else ""
        if kind == "day_two":
            caption = text_for(event).removeprefix("February 3.").strip()
        spoken = kind in SPEAKING_TYPES or (event.get("anchor") == "ned_greeting" and actor)
        if spoken:
            hold_ms = min(7_200, max(2_500, 850 + 290 * len(caption.split())))
        title = None
        if camera == "clock":
            title = "February 3" if kind == "day_two" else "February 2"
        location = event.get("location") or positions.get(actor)
        if camera == "clock":
            location = "inn"
        shot = {
            "id": f"s{len(shots) + 1:03d}",
            "event_index": event_index,
            "event_id": event.get("id", f"event-{event_index}"),
            "loop": event.get("loop", 1),
            "tick": event.get("tick", 0),
            "time": event.get("time", "06:00"),
            "camera": camera,
            "location": location,
            "actor": actor,
            "speaker": cast_member(run, actor) if spoken else "",
            "caption": caption,
            "title": title,
            "duration_ms": hold_ms,
            "sound": sound,
        }
        shots.append(shot)
    _stretch(shots, round(target_seconds * 1_000))
    start = 0
    for shot in shots:
        shot["start_ms"] = start
        start += shot["duration_ms"]
    mode = run.get("meta", {}).get("mode", "unknown")
    complete = bool(run.get("meta", {}).get("complete"))
    return {
        "version": PLAN_VERSION,
        "duration_ms": start,
        "shots": shots,
        "source": {
            "mode": mode,
            "complete": complete,
            "ending": run.get("meta", {}).get("ending", "unknown"),
            "ending_reason": run.get("meta", {}).get("ending_reason"),
            "events": len(events),
        },
        "full_length": MIN_SECONDS * 1_000 <= start <= MAX_SECONDS * 1_000,
    }


def build_teaser(film: dict, events: list[dict]) -> dict:
    """Build a short paired-pass edit using the same logged source events."""
    all_shots = film["shots"]
    opener = all_shots[0]
    first_puddle = next((shot for shot in all_shots if shot["camera"] == "puddle"), None)
    next_puddle = next((shot for shot in all_shots if shot["camera"] == "puddle" and first_puddle
                        and shot["loop"] > first_puddle["loop"]), None)
    reset = next((shot for shot in all_shots if shot["camera"] == "clock" and shot["loop"] > opener["loop"]
                  and events[shot["event_index"]].get("type") != "day_two"), None)
    result = next((shot for shot in all_shots if events[shot["event_index"]].get("type") == "test_result"), None)
    payoff = next((shot for shot in reversed(all_shots) if events[shot["event_index"]].get("type") == "performance"), None)
    material = [shot for shot in (opener, first_puddle, reset, result, next_puddle, payoff) if shot]
    if len(material) <= 2:
        material = all_shots[:min(4, len(all_shots))]
    source = sorted({shot["event_index"]: shot for shot in material}.values(), key=lambda shot: shot["event_index"])
    shots = []
    start = 0
    for index, shot in enumerate(source):
        duration = min(4_000, max(2_400, shot["duration_ms"]))
        caption = shot["caption"]
        if shot["camera"] == "puddle":
            caption = ""  # Keep the matched actions legible in the portrait crop.
        filtered = {**shot, "id": f"t{index + 1:03d}", "start_ms": start, "duration_ms": duration,
                    "caption": caption, "eyebrow": f"Loop {shot['loop']} · {shot['time']}" if shot["camera"] == "puddle" else ""}
        if index == 0:
            filtered["hook"] = "The town resets at six." if reset else "LOOPDAY"
        shots.append(filtered)
        start += duration
    return {**film, "shots": shots, "duration_ms": start, "full_length": False, "cut": "teaser"}


def subtitles(plan: dict, *, vtt: bool = False) -> str:
    """Export plain event captions for editors and accessible video playback."""
    def timestamp(ms: int) -> str:
        minutes, remainder = divmod(ms, 60_000)
        hours, minutes = divmod(minutes, 60)
        seconds, remainder = divmod(remainder, 1_000)
        separator = "." if vtt else ","
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{remainder:03d}"

    spoken = []
    for shot in plan["shots"]:
        line = "\n".join(filter(None, (shot["title"], shot["caption"])))
        if not line:
            continue
        if shot["speaker"]:
            line = shot["speaker"] + ": " + line
        if vtt:
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        start = shot["start_ms"]
        timing = timestamp(start) + " --> " + timestamp(start + shot["duration_ms"])
        spoken.append(f"{len(spoken) + 1}\n{timing}\n{line}")
    prefix = "WEBVTT\n\n" if vtt else ""
    return prefix + "\n\n".join(spoken) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("runs/preflight/run.json"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--seconds", type=float, default=94)
    parser.add_argument("--captions", type=Path, help="Export .srt or .vtt captions alongside the film plan")
    args = parser.parse_args()
    try:
        run = json.loads(args.run.read_text(encoding="utf-8"))
        plan = build_film(run, args.seconds)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))
    output = args.out or args.run.with_name("film.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.captions:
        if args.captions.suffix.lower() not in {".srt", ".vtt"}:
            parser.error("Use .srt or .vtt for the subtitle file.")
        args.captions.parent.mkdir(parents=True, exist_ok=True)
        args.captions.write_text(subtitles(plan, vtt=args.captions.suffix.lower() == ".vtt"), encoding="utf-8")
    print(f"{output} · {len(plan['shots'])} shots · {plan['duration_ms'] / 1_000:.1f}s")


if __name__ == "__main__":
    main()
