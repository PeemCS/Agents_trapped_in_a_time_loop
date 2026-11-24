#!/usr/bin/env python3
"""Exact entropy of a post-hoc, source-constrained distribution over film edits of one completed life."""

import argparse
from collections import Counter
from functools import lru_cache
import math
from pathlib import Path
import random

from edit import coach_clusters, make_edl, read_trace, verify, write_json


def screen(trace_path, seed=117, low=60, high=82):
    world, digest = read_trace(trace_path)
    es = world["events"]
    names = world["cast_names"]
    roles = ("reporter", "producer", "camera")
    bit = {r: 1 << i for i, r in enumerate(roles)}
    frequency = Counter((r["role"], r["decision"]["action"]) for e in es for r in [e, *e["cast"]])
    cluster = next(coach_clusters(es), None)
    forced = {0, len(es) - 1}
    if cluster:
        forced.update((cluster["arrival"], cluster["hold"]))
    wake = cluster["wake"] if cluster else None
    dawn_cost = 4 if cluster else 0
    menus = []
    for i, e in enumerate(es):
        options = [] if i in forced else [(0, 0.0, 0, None)]
        for r in [e, *e["cast"]]:
            role = r["role"]
            a = r["decision"]["action"]
            line = r["decision"]["words"].strip()
            spoken = line if 0 < len(line.split()) <= 20 else ""
            if i in forced and role != "reporter":
                continue
            cost = max(4, math.ceil(len(spoken.split()) / 2.4 + 1.0))
            moves = r["origin"] != r["place"]
            typed = a in (
                "call_sister",
                "call_live_report",
                "leave_pencil_mark",
                "file_forecast",
                "air_forecast",
                "clear_tables",
                "film_festival",
                "film_cornet_player",
                "send_camera_take",
                "patch_reporter_line",
                "patch_camera_line",
                "host_bulletin",
            )
            scarcity = 1 / math.sqrt(frequency[(role, a)])
            utility = (
                0.9 * int(moves) + 1.45 * int(typed) + 0.85 * scarcity + 0.35 * bool(spoken) - 0.19 * cost
            )
            choice = {
                "event_index": i,
                "event_id": e["id"],
                "focus": r["actor"],
                "view": "action",
                "framing": "street" if moves else "close",
                "start": 0.25 if i == wake else 0,
                "end": 1,
                "seconds": cost,
                "speech": [{"actor": r["actor"], "text": spoken}] if spoken else [],
            }
            options.append((cost, utility, bit[role], choice))
        menus.append(options)

    def distribution(beta):
        # Each cached state sums all valid suffixes and their first moments. Max-shifting avoids overflow.
        @lru_cache(None)
        def suffix(i, used, mask):
            if used > high:
                return -math.inf, 0, 0
            if i == len(menus):
                return (0, 0, 0) if used >= low and mask == 7 else (-math.inf, 0, 0)
            branches = []
            for cost, score, added, _ in menus[i]:
                z, e, t = suffix(i + 1, used + cost, mask | added)
                if math.isfinite(z):
                    branches.append((beta * score + z, score + e, cost + t))
            if not branches:
                return -math.inf, 0, 0
            largest = max(v[0] for v in branches)
            weights = [math.exp(v[0] - largest) for v in branches]
            total = sum(weights)
            return (
                largest + math.log(total),
                sum(w * b[1] for w, b in zip(weights, branches)) / total,
                sum(w * b[2] for w, b in zip(weights, branches)) / total,
            )

        z, expected, duration = suffix(0, dawn_cost, 0)
        if not math.isfinite(z):
            raise ValueError("no feasible edit under the length and three-actor constraints")
        rng = random.Random(seed)
        used = dawn_cost
        mask = 0
        shots = []
        for i, menu in enumerate(menus):
            if i == wake:
                shots.append(
                    {
                        "event_index": i,
                        "event_id": es[i]["id"],
                        "view": "morning",
                        "focus": names["reporter"],
                        "framing": "close",
                        "start": 0.22,
                        "end": 0.22,
                        "seconds": dawn_cost,
                        "speech": [],
                    }
                )
            scored = []
            for choice in menu:
                cost, reward, added, _ = choice
                tail = suffix(i + 1, used + cost, mask | added)[0]
                if math.isfinite(tail):
                    scored.append((beta * reward + tail, choice))
            peak = max(s[0] for s in scored)
            opt = rng.choices([s[1] for s in scored], weights=[math.exp(s[0] - peak) for s in scored])[0]
            cost, _, added, shot = opt
            used += cost
            mask |= added
            if shot:
                shots.append(shot)
        edit = make_edl(trace_path, "chronicle")
        edit.update(
            selection="constrained-posterior-sample",
            purpose="Editor-only post-hoc sample. Physical actor choices are fixed.",
            shots=shots,
            cluster=cluster,
        )
        checked = verify(trace_path, edit)
        assert low <= checked["seconds"] <= high
        return {
            "inverse_temperature": beta,
            "entropy_bits": (z - beta * expected) / math.log(2),
            "expected_editor_utility": expected,
            "expected_estimated_seconds": duration + dawn_cost,
            "sample_seconds": used,
            "verified_sample_shots": len(shots),
            "chosen_actor_events": [(s["event_id"], s["focus"], s["view"]) for s in shots],
        }, edit

    results = []
    sample = None
    for beta in (0, 0.5, 1, 2, 5):
        row, edl = distribution(beta)
        results.append(row)
        if beta == 1:
            sample = edl

    @lru_cache(None)
    def count(i, used, mask):
        if used > high:
            return 0
        if i == len(menus):
            return int(used >= low and mask == 7)
        return sum(count(i + 1, used + c, mask | b) for c, _, b, _ in menus[i])

    number = count(0, dawn_cost, 0)
    support = math.log2(number)
    assert math.isclose(support, results[0]["entropy_bits"], abs_tol=1e-10)
    for row in results:
        row["fraction_of_uniform_path_entropy"] = row["entropy_bits"] / support
    return {
        "source_sha256": digest,
        "exact_feasible_cut_paths": number,
        "constraints": "60 to 82 estimated seconds by default; first and last reporter decision; three distinct focused actors; all selected lines whole and from their speaker; first closed coach trip with hero arrival, city evening and next-morning hotel when present.",
        "method": "Exact dynamic-programming partition function over legal edit paths. p(cut) is proportional to exp(beta * editor utility). Utility weights source-confirmed movement, finite physical acts, rarity of the role-specific action and short lines, with a time charge. Actor decisions and world rewards are unchanged. Entropy is over independently selectable film edits, not reward outcomes, agent actions, or inferred personality. Real TTS duration is measured separately.",
        "temperatures": results,
    }, sample


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--sample", type=Path, required=True)
    a = p.parse_args()
    report, cut = screen(a.trace)
    write_json(a.output, report)
    write_json(a.sample, cut)
    print([(r["inverse_temperature"], round(r["entropy_bits"], 2)) for r in report["temperatures"]])
