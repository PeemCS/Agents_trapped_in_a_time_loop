#!/usr/bin/env python3
"""Estimate two pre-booked airtime rules from already-recorded held-out choices, without new inference."""

from collections import Counter
from pathlib import Path
from edit import read_trace, write_json

ED = Path(__file__).resolve().parent


def simulate():
    rows = []
    for file in sorted((ED.parent / "takes" / "heldout" / "v2").glob("seed-*.json")):
        trace, digest = read_trace(file)
        for e in trace["events"]:
            if e["clock"] != "7:00 pm":
                continue
            actual = e["world_after"]["bulletin"]
            before = e["world_before"]
            actors = {r["role"]: r for r in [e, *e["cast"]]}
            bookings = []
            for role, agreement in before["assignments"].items():
                if agreement["status"] != "accepted" or role not in actual["delivered_assignments"]:
                    continue
                accept_tick = int(agreement["event_id"].split("-")[1][1:])
                invite_tick = int(agreement["invite_id"].split("-")[1][1:])
                bookings.append((accept_tick, invite_tick, role))
            winner = min(bookings)[2] if bookings else None
            if winner == "reporter":
                alternate = (
                    "live_report"
                    if actors[winner]["decision"]["words"].strip()
                    else "silent_live_reporter_line"
                )
            elif winner == "camera":
                assert before["camera_footage"]
                alternate = "camera_take"
            else:
                alternate = actual["channel"]
            standby = alternate if actual["channel"] == "station_ident" else actual["channel"]
            rows.append(
                {
                    "source_sha256": digest,
                    "seed": trace["seed"],
                    "day": e["day"],
                    "actual": actual["channel"],
                    "booked_and_delivered": [x[2] for x in sorted(bookings)],
                    "standby": standby,
                    "binding_booking": alternate,
                }
            )
    assert len(rows) == 24
    totals = {k: dict(Counter(r[k] for r in rows)) for k in ("actual", "standby", "binding_booking")}
    changes = {k: sum(r[k] != r["actual"] for r in rows) for k in ("standby", "binding_booking")}
    result = {
        "method": "Retrospective first-order mechanism study on 24 completed evenings. Freeze every chosen action, utterance, invitation, prior signed acceptance and completed contribution. Select the earliest accepted assignment that had already been signed before the evening slot and then was actually delivered. Ties use earlier invitation, then role. Standby uses that booking only when the actual switch was otherwise unattended. Binding bookings honor it even when the producer selected another channel. No actor observed or responded to the hypothetical rules.",
        "actual_and_counterfactual_channels": totals,
        "changed_evenings": changes,
        "rows": rows,
    }
    write_json(ED / "booking-replay.json", result)
    print(totals, changes)


if __name__ == "__main__":
    simulate()
