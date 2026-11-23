"""Verify LOOPDAY run artifacts and compare observed outcomes."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from bisect import bisect_left
import json
from pathlib import Path
from typing import Any


class ArtifactError(ValueError):
    """A run artifact has a malformed or inconsistent event ledger."""


def read_run(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactError(f"Cannot read {path}: {error}") from error
    if not isinstance(data, dict):
        raise ArtifactError(f"{path} must contain a run object.")
    return data


def event_index(run: dict) -> dict[str, dict]:
    events = run.get("events")
    if not isinstance(events, list):
        raise ArtifactError("The run needs an ordered events array.")
    by_id = {}
    previous_order = -1
    current_day = 0
    current_tick = 0
    day_two = False
    for event in events:
        if not isinstance(event, dict):
            raise ArtifactError("Every ledger entry must be an object.")
        event_id = event.get("id")
        order = event.get("order")
        day = event.get("loop")
        tick = event.get("tick")
        kind = event.get("type")
        if not isinstance(event_id, str) or not event_id or event_id in by_id:
            raise ArtifactError("Every ledger entry needs a unique event ID.")
        if type(order) is not int or order <= previous_order:
            raise ArtifactError(f"{event_id} is out of ledger order.")
        if not isinstance(kind, str) or not kind or type(tick) is not int or not 0 <= tick <= 35:
            raise ArtifactError(f"{event_id} has an invalid event type or tick.")
        if type(day) is not int or day < 1 or day < current_day:
            raise ArtifactError(f"{event_id} has an invalid loop number.")
        if day_two:
            raise ArtifactError(f"{event_id} appears after the Day 2 ending.")
        if kind == "day_start":
            if day != current_day + 1 or tick != 0:
                raise ArtifactError(f"{event_id} must start the next loop at 06:00.")
        elif kind == "day_two":
            if not current_day or day != current_day or tick != 0:
                raise ArtifactError(f"{event_id} must end the current run at 06:00.")
            day_two = True
        elif day != current_day or tick < current_tick:
            raise ArtifactError(f"{event_id} is outside its day's timeline.")

        by_id[event_id] = event
        previous_order, current_day, current_tick = order, day, tick
    return by_id


def _prior(event: dict, event_id: Any, by_id: dict[str, dict], label: str) -> dict:
    candidate = by_id.get(event_id) if isinstance(event_id, str) else None
    if candidate is None or candidate["order"] >= event["order"]:
        raise ArtifactError(f"{event['id']} has an invalid {label} reference.")
    return candidate


def _references(event: dict, key: str) -> list[str]:
    value = event.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ArtifactError(f"{event['id']} has malformed {key} references.")
    return value


def _experiment(event: dict, by_id: dict[str, dict]) -> dict:
    prediction_id = event.get("prediction_id", event.get("prediction"))
    action_id = event.get("action_event_id", event.get("action_evidence"))
    observation_id = event.get("observation_event_id", event.get("observation"))
    prediction = _prior(event, prediction_id, by_id, "prediction")
    action = _prior(event, action_id, by_id, "action")
    observation = _prior(event, observation_id, by_id, "observation")
    if prediction["type"] != "prediction" or not prediction["order"] < action["order"] < observation["order"]:
        raise ArtifactError(f"{event['id']} has an invalid experimental sequence.")
    if len({prediction.get("actor"), action.get("actor"), observation.get("actor"), event.get("actor")}) != 1:
        raise ArtifactError(f"{event['id']} attributes its experiment to different actors.")
    if observation.get("state") is not None and event.get("state") != observation["state"]:
        raise ArtifactError(f"{event['id']} disagrees with the recorded observation.")
    if action["type"] == "pencil" or observation["type"] == "pencil":
        if (action["type"] != "pencil" or observation["type"] != "pencil" or action.get("state") != "broken"
                or prediction["loop"] != action["loop"] or prediction["tick"] != action["tick"]
                or action["loop"] >= observation["loop"] or (observation["loop"], observation["tick"]) != (event["loop"], event["tick"])
                or len({row.get("location") for row in (prediction, action, observation, event)}) != 1):
            raise ArtifactError(f"{event['id']} does not show the pencil state across a day reset.")
        if "predicted" in event or "observed" in event:
            expected = prediction.get("predicted")
            matched = expected == observation.get("state") if expected else None
            if (event.get("predicted") != expected or event.get("observed") != observation.get("state")
                    or event.get("agrees_with_prediction") is not matched):
                raise ArtifactError(f"{event['id']} misstates the recorded prediction or result.")
    return {
        "result_id": event["id"], "prediction_id": prediction_id,
        "action_event_id": action_id, "observation_event_id": observation_id,
        "actor": event.get("actor"), "state": event.get("state"),
        "prediction": prediction.get("text"), "observed": observation.get("text"),
    }


def _witnessed(row: dict, source: dict, purpose: str) -> None:
    witnesses = source.get("witnesses")
    if witnesses is not None and (not isinstance(witnesses, list) or row.get("actor") not in witnesses):
        raise ArtifactError(f"{row['id']} uses {purpose} outside its observations.")


def _replay(event: dict, by_id: dict[str, dict]) -> None:
    if replayed := event.get("replay_source_event"):
        original = _prior(event, replayed, by_id, "replay source")
        if (event.get("mode") != "replay" or original["type"] != "decision" or original["loop"] != 1
                or any(original.get(field) != event.get(field) for field in ("actor", "action", "tick", "exchange", "location"))
                or original.get("mode") != event.get("source")
                or event.get("replay_match") not in {"exact", "semantic"}
                or (event["replay_match"] == "exact" and original.get("fingerprint") != event.get("fingerprint"))):
            raise ArtifactError(f"{event['id']} disagrees with its original decision.")


def _corroborate(event: dict, origin: dict, heard: dict) -> None:
    _witnessed(event, heard, "a town fact")
    if (origin["loop"] != event["loop"] or heard["loop"] != event["loop"]
            or heard["order"] < origin["order"]
            or (heard is not origin and (heard["type"] != "gossip" or heard.get("source_event") != origin["id"]))):
        raise ArtifactError(f"{event['id']} uses a fact without a valid witness or relay.")


def _ending(event: dict, by_id: dict[str, dict], social: dict) -> None:
    evidence = [_prior(event, ref, by_id, "ending evidence") for ref in _references(event, "evidence")]
    if event.get("reason") == "rita_chose_to_stay":
        reply = (_prior(event, event["reply_event_id"], by_id, "Rita reply") if event.get("reply_event_id")
                 else social.get((event["loop"], "reply")))
        if (not reply or reply["type"] != "reply" or reply.get("actor") != "rita"
                or reply.get("accepted") is not True or reply["loop"] != event["loop"]
                or len(set(_references(reply, "evidence"))) < 2
                or not set(reply["evidence"]) <= {source["id"] for source in evidence}
                or any(source["loop"] != event["loop"] or source["type"] not in {"performance", "kindness"}
                       for source in evidence)):
            raise ArtifactError(f"{event['id']} does not follow Rita's accepted reply.")
        if "decision_id" in reply:
            choice = _prior(reply, reply["decision_id"], by_id, "consent decision")
            invitation = _prior(reply, reply.get("invitation_id"), by_id, "invitation")
            if (choice["type"] != "decision" or choice.get("actor") != "rita" or choice.get("action") != "accept_invitation"
                    or invitation["type"] != "invitation" or invitation.get("actor") != "phil" or invitation.get("to") != "rita"
                    or invitation["id"] != event.get("invitation_id") or reply.get("gate_level") != 3
                    or choice["loop"] != reply["loop"] or choice["tick"] != reply["tick"]
                    or invitation["loop"] != reply["loop"] or invitation["order"] >= choice["order"]):
                raise ArtifactError(f"{event['id']} has inconsistent consent evidence.")
    elif event.get("reason") == "community_recognition":
        helpers = {source["id"] for source in evidence if source["type"] == "kindness"
                   and source["loop"] == event["loop"] and source.get("actor") == "phil"}
        credits = {source.get("actor") for source in evidence if source["type"] == "recognition"
                   and source["loop"] == event["loop"] and source.get("source_event") in helpers}
        if (len(helpers) < 2 or len(credits - {None, "phil"}) < 2
                or not any(row["type"] == "test_result" and row.get("observed", row.get("state")) == "whole" for row in evidence)):
            raise ArtifactError(f"{event['id']} does not show two independent witnesses and tested evidence.")


def audit_run(run: dict) -> dict:
    by_id = event_index(run)
    report = run.get("meta", {})
    if not isinstance(report, dict):
        raise ArtifactError("Run metadata must be an object.")
    if "event_count" in report and report["event_count"] != len(by_id):
        raise ArtifactError("The ledger length disagrees with run metadata.")
    decisions = []
    experiments = []
    anchors = []
    citing_orders: dict[tuple[str, str], list[int]] = defaultdict(list)
    recalling_orders: dict[tuple[str, str], list[int]] = defaultdict(list)
    band_deliveries: set[str] = set()
    band_used: set[str] = set()
    social: dict[tuple[int, str], dict] = {}
    counts: Counter = Counter()
    for event in by_id.values():
        kind = event["type"]
        counts[kind] += 1
        delivery = event.get("transport")
        if isinstance(delivery, dict) and delivery.get("verified_recipients") and delivery.get("receipt"):
            band_deliveries.add(event["id"])
        if kind == "decision":
            if not isinstance(event.get("actor"), str) or not isinstance(event.get("action"), str):
                raise ArtifactError(f"{event['id']} has an invalid decision.")
            options = event.get("available_actions")
            if options is not None and (not isinstance(options, list) or event["action"] not in options):
                raise ArtifactError(f"{event['id']} records an unavailable action.")
            _replay(event, by_id)
            decisions.append(event)
            recalled = _references(event, "recalled")
            current = _references(event, "current_evidence")
            for reference in recalled:
                source = _prior(event, reference, by_id, "recalled")
                _witnessed(event, source, "a recalled memory")
                recalling_orders[event["actor"], reference].append(event["order"])
            for reference in current:
                source = _prior(event, reference, by_id, "current evidence")
                _witnessed(event, source, "current evidence")
                if source["loop"] != event["loop"]:
                    raise ArtifactError(f"{event['id']} treats a previous day as a current observation.")
            for reference in _references(event, "stated_support"):
                _prior(event, reference, by_id, "stated support")
                if reference not in recalled and reference not in current:
                    raise ArtifactError(f"{event['id']} cites evidence absent from its prompt.")
                citing_orders[event["actor"], reference].append(event["order"])
            for fact in event.get("known_fact_sources", []):
                if not isinstance(fact, dict):
                    raise ArtifactError(f"{event['id']} has a malformed town fact.")
                origin = _prior(event, fact.get("source_event"), by_id, "original fact")
                heard = _prior(event, fact.get("heard_via"), by_id, "heard fact")
                _corroborate(event, origin, heard)
            for received in event.get("message_receipts", []):
                if not isinstance(received, dict):
                    raise ArtifactError(f"{event['id']} has a malformed delivery reference.")
                source = _prior(event, received.get("event_id"), by_id, "message receipt")
                delivery = source.get("transport", {})
                if (source["id"] not in band_deliveries or received.get("receipt") != delivery.get("receipt")
                        or event["actor"] not in delivery.get("verified_recipients", [])):
                    raise ArtifactError(f"{event['id']} cites a Band receipt unverified for its actor.")
                band_used.add(source["id"])
        elif kind == "test_result":
            experiments.append(_experiment(event, by_id))
        elif kind == "anchor":
            anchors.append((event["loop"], event["tick"], event.get("anchor")))
        elif kind == "gossip" and event.get("teller_evidence"):
            origin = _prior(event, event.get("source_event"), by_id, "gossip original")
            heard = _prior(event, event["teller_evidence"], by_id, "gossip relay")
            _corroborate(event, origin, heard)
        elif kind == "reply":
            for reference in _references(event, "evidence"):
                _prior(event, reference, by_id, "ending evidence")
            social[event["loop"], kind] = event
        elif kind == "ending_decision":
            _ending(event, by_id, social)
            social[event["loop"], kind] = event
        elif kind == "day_two" and event.get("ending_reason"):
            earned = social.get((event["loop"], "ending_decision"))
            if not earned or earned.get("reason") != event["ending_reason"]:
                raise ArtifactError(f"{event['id']} does not match the earned ending.")

    day_two = counts["day_two"] == 1
    if report.get("complete") is True and report.get("ending") in {"repeat", "day_two"}:
        if day_two != (report["ending"] == "day_two"):
            raise ArtifactError("The recorded ending disagrees with run metadata.")
    for test in experiments:
        result_order = by_id[test["result_id"]]["order"]
        references = (test["observation_event_id"], test["result_id"])
        for counts_by_ref, field in ((recalling_orders, "later_recalled"), (citing_orders, "later_cited")):
            matches = (counts_by_ref[test["actor"], reference] for reference in references)
            test[field] = any(bisect_left(orders, result_order + 1) < len(orders) for orders in matches)

    return {
        "mode": report.get("mode"), "complete": report.get("complete"),
        "ending": report.get("ending"), "event_count": len(by_id),
        "ending_reason": report.get("ending_reason"),
        "day_two": day_two, "decision_count": len(decisions),
        "replayed": sum(event.get("mode") == "replay" for event in decisions),
        "decisions_with_recall": sum(bool(event.get("recalled")) for event in decisions),
        "decisions_with_cited_memory": sum(bool(set(event.get("stated_support", [])) & set(event.get("recalled", [])))
                                           for event in decisions),
        "divergences": counts["divergence"],
        "rejected_actions": counts["rejected"],
        "band_verified_deliveries": len(band_deliveries), "band_observed_deliveries": len(band_used),
        "anchors": anchors, "experiments": experiments,
    }


def _decision_slots(events: list[dict]) -> dict[tuple, dict]:
    occurrences: Counter = Counter()
    result = {}
    for event in events:
        if event["type"] == "decision":
            key = event["loop"], event["tick"], event["actor"]
            result[(*key, occurrences[key])] = event
            occurrences[key] += 1
    return result


def compare_runs(first: dict, second: dict) -> dict:
    a = audit_run(first)
    b = audit_run(second)
    a_slots = _decision_slots(first["events"])
    b_slots = _decision_slots(second["events"])
    first_change = None
    for slot in sorted(a_slots.keys() & b_slots.keys()):
        earlier, later = a_slots[slot], b_slots[slot]
        if earlier["action"] != later["action"]:
            day, tick, actor, _ = slot
            first_change = {
                "loop": day, "tick": tick, "actor": actor,
                "first_event": earlier["id"], "first_action": earlier["action"],
                "second_event": later["id"], "second_action": later["action"],
            }
            for field in ("checkpoint_fingerprint",):
                if earlier.get(field) and later.get(field):
                    first_change["same_checkpoint"] = earlier[field] == later[field]
            break
    overlapping = min(
        max((day for day, _, _ in a["anchors"]), default=0),
        max((day for day, _, _ in b["anchors"]), default=0),
    )
    a_starts = [anchor for anchor in a["anchors"] if anchor[0] <= overlapping]
    b_starts = [anchor for anchor in b["anchors"] if anchor[0] <= overlapping]
    return {
        "first": a, "second": b,
        "overlapping_loops": overlapping,
        "same_overlapping_anchors": bool(overlapping) and a_starts == b_starts,
        "comparable_decision_slots": len(a_slots.keys() & b_slots.keys()),
        "first_changed_action": first_change,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="First run.json artifact.")
    parser.add_argument("comparison", type=Path, nargs="?", help="Optional second run.json.")
    args = parser.parse_args()
    try:
        run = read_run(args.run)
        report = compare_runs(run, read_run(args.comparison)) if args.comparison else audit_run(run)
    except ArtifactError as error:
        parser.exit(1, f"Invalid run: {error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
