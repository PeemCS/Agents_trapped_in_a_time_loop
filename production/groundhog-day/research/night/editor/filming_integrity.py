#!/usr/bin/env python3
"""Exercise specific tamper cases against the two rehearsal film validators."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile

from edit import read_trace, verify, write_json
from thinking_film import locate


def check(montage, montage_edl, thinking, thinking_folder):
    evidence = []

    def reject(name, fn):
        try:
            fn()
        except (AssertionError, ValueError) as err:
            evidence.append(
                {
                    "case": name,
                    "rejected": True,
                    "error": str(err)[:180] or "source receipt equality assertion",
                }
            )
            return
        raise RuntimeError("accepted a known-invalid edit: " + name)

    physical = json.loads(montage_edl.read_text())
    verify(montage, physical)
    swapped = copy.deepcopy(physical)
    swapped["shots"][4]["montage_index"] = 1
    reject(
        "Mark the second Pittsburgh evening as the first.",
        lambda: verify(montage, swapped),
    )
    dropped = copy.deepcopy(physical)
    dropped["shots"].pop(8)
    reject(
        "Remove a hotel reset while still claiming five complete trips.",
        lambda: verify(montage, dropped),
    )
    fanfic = copy.deepcopy(physical)
    fanfic["shots"][0]["speech"][0]["text"] = "Wait, I recognize this movie."
    reject(
        "Inject a spoken recognition the reporter never uttered.",
        lambda: verify(montage, fanfic),
    )
    name_call = copy.deepcopy(physical)
    name_call["shots"][4]["speech"] = [
        {"actor": "Larry", "text": "Getting the wide shot now."}
    ]
    reject(
        "Give the Pittsburgh terminal a quote heard only at the square.",
        lambda: verify(montage, name_call),
    )
    t, digest = read_trace(thinking)
    notes = json.loads((thinking_folder / "notes.json").read_text())["notes"]
    knowledge = []
    for item in notes:
        with (thinking.parent / item["stream_path"]).open() as raw:
            req = json.loads(raw.readline())
        body = req["body"]
        wire_hash = hashlib.sha256(
            json.dumps(
                body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        assert (
            body["think"] is True
            and req["id"] == Path(item["stream_path"]).stem
            and wire_hash == req["request_sha256"]
        )
        visible = next(
            json.loads(m["content"])
            for m in body["messages"]
            if m["role"] == "user" and '"evidence_now"' in m["content"]
        )
        slot = t["events"][item["slot_index"]]
        focus = next(r for r in [slot, *slot["cast"]] if r["actor"] == item["actor"])
        assert (
            visible["where"] == focus["origin"] and visible["clock"] == focus["clock"]
        )
        date = next(
            line
            for line in visible["evidence_now"]
            if line.startswith("Tuesday, February 2, 2016")
        )
        knowledge.append(
            {
                "event": item["event_id"],
                "stream_id": req["id"],
                "inference_cache_key": item["request_id"],
                "request_sha256": req["request_sha256"],
                "where_before_action": visible["where"],
                "clock_before_action": visible["clock"],
                "exact_date_seen_in_inference_request": date,
            }
        )
    note = notes[0]
    e = t["events"][note["slot_index"]]
    assert (
        locate(thinking.parent, e, note["actor"], note["quote"])["stream_sha256"]
        == note["stream_sha256"]
    )
    reject(
        "Substitute an invented external model-note quotation.",
        lambda: locate(
            thinking.parent, e, note["actor"], "I am the protagonist of a movie."
        ),
    )
    wrong = copy.deepcopy(e)
    who = next(r for r in [wrong, *wrong["cast"]] if r["actor"] == note["actor"])
    who["inference"]["cache_hit"] = True
    reject(
        "Label a cached generation as a fresh note.",
        lambda: locate(thinking.parent, wrong, note["actor"], note["quote"]),
    )
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        path = Path(note["stream_path"])
        (base / path).parent.mkdir(parents=True, exist_ok=True)
        (base / path).write_bytes((thinking.parent / path).read_bytes() + b"\n")
        reject(
            "Append a byte to the NDJSON provider receipt.",
            lambda: locate(base, e, note["actor"], note["quote"]),
        )
    bad = copy.deepcopy(e)
    next(r for r in [bad, *bad["cast"]] if r["actor"] == note["actor"])["decision"][
        "words"
    ] = "Rewritten line."
    reject(
        "Keep the original stream but alter the committed final decision.",
        lambda: locate(thinking.parent, bad, note["actor"], note["quote"]),
    )
    edl = json.loads((thinking_folder / "edit.json").read_text())
    air = copy.deepcopy(edl)
    first = next(
        s
        for s in air["shots"]
        if s["view"] == "action"
        and s["speech"]
        and t["events"][s["event_index"]]["clock"] != "7:00 pm"
    )
    first["verified_air_sources"] = [first["event_id"]]
    reject(
        "Claim an ordinary daytime remark went on air.", lambda: verify(thinking, air)
    )
    return {
        "positive_controls_passed": True,
        "montage_source": physical["source_sha256"],
        "thinking_source": digest,
        "pre_action_observations_from_original_provider_requests": knowledge,
        "tamper_cases": evidence,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("montage", "montage_edl", "thinking", "thinking_folder", "output"):
        p.add_argument(arg, type=Path)
    a = p.parse_args()
    write_json(a.output, check(a.montage, a.montage_edl, a.thinking, a.thinking_folder))
