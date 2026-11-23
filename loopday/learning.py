"""Fit a bounded outcome ranker and export observed preference pairs."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import fmean
from typing import Iterable


class TrainingError(ValueError):
    """The data or saved model is unsuitable for the requested operation."""


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def number(value: object) -> float | None:
    if type(value) not in (int, float):
        return None
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


@dataclass(frozen=True)
class DecisionSample:
    group: str
    source: str
    checkpoint: str
    observation: dict
    action: str
    completion: str
    outcome: float
    model: str = ""
    condition: str = ""
    evidence_id: str = ""
    model_revision: str = ""
    prompt_version: str = ""
    alias_names: bool = False
    environment: str = ""

    @classmethod
    def from_event(cls, event: dict, meta: dict, run_id: str) -> DecisionSample | None:
        if event.get("type") != "decision" or event.get("actor") != "phil":
            return None
        source = event.get("source", meta.get("mode"))
        if source not in {"fixture", "live"} or event.get("mode") == "replay":
            return None
        observation = event.get("policy_observation")
        checkpoint = event.get("checkpoint_fingerprint")
        completion = event.get("completion")
        action = event.get("action")
        outcome = number(event.get("return_to_go"))
        if (not isinstance(observation, dict) or not isinstance(checkpoint, str)
                or not checkpoint or not isinstance(completion, str) or not isinstance(action, str)
                or outcome is None):
            return None
        options = observation.get("actions")
        if not isinstance(options, list) or action not in options:
            return None
        try:
            decoded = json.loads(completion)
        except (ValueError, TypeError, RecursionError):
            return None
        if not isinstance(decoded, dict) or decoded.get("action") != action:
            return None
        if source == "live":
            support = decoded.get("support", [])
            if not isinstance(support, list) or any(not isinstance(item, str) for item in support):
                return None
            if support:
                evidence_lists = [observation.get(field, []) for field in ("current_evidence", "memories")]
                if any(not isinstance(entries, list) for entries in evidence_lists):
                    return None
                visible = {
                    entry["event_id"] for entries in evidence_lists for entry in entries if isinstance(entry, dict)
                    and isinstance(entry.get("event_id"), str)
                }
                if not set(support).issubset(visible):
                    return None
        metadata = event.get("model_metadata") or event.get("decision_metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        environment = ""
        paired_batch = None
        if meta.get("mode") == "live_candidate_local_continuation":
            intervention = meta.get("intervention")
            batch_id = metadata.get("batch_id")
            if (not isinstance(intervention, dict) or source != "live"
                    or intervention.get("target_event_id") != event.get("id")
                    or intervention.get("batch_id") != batch_id
                    or intervention.get("environment") != "local_continuation"
                    or metadata.get("environment") != "local_continuation"
                    or metadata.get("selection") != "paired_intervention"
                    or metadata.get("selected_action") != action
                    or not isinstance(batch_id, str) or not re.fullmatch(r"[a-f0-9]{64}", batch_id)
                    or metadata.get("completion_sha256") != hashlib.sha256(completion.encode()).hexdigest()):
                return None
            environment = "local_continuation"
            paired_batch = batch_id
        elif metadata.get("selection") == "paired_intervention":
            return None
        seed = meta.get("seed")
        group = f"seed:{seed}" if type(seed) is int else f"run:{run_id}"
        condition = stable_json({
            "condition": meta.get("condition"),
            "steering": metadata.get("steering", event.get("steering")),
            "adapter": metadata.get("adapter", event.get("adapter")),
            "thinking": metadata.get("thinking_enabled"),
            "persona_bank": metadata.get("persona_bank"),
            "precision": metadata.get("precision"),
            "withheld_memory": event.get("withheld_memory", []),
            "alias_names": metadata.get("alias_names") is True,
            "environment": environment, "paired_batch": paired_batch,
        })
        revision = metadata.get("model_revision")
        prompt_version = metadata.get("prompt_version")
        return cls(group, source, checkpoint, observation, action, completion, outcome,
                   str(metadata.get("model", event.get("model")) or ""), condition,
                   f"{run_id}:{event.get('id', '')}", revision if isinstance(revision, str) else "",
                   prompt_version if isinstance(prompt_version, str) else "", metadata.get("alias_names") is True,
                   environment)


def read_samples(paths: Iterable[Path]) -> list[DecisionSample]:
    from .audit import ArtifactError, audit_run

    samples = []
    evidence = set()
    for path in paths:
        if path.is_dir():
            path = path / "run.json"
        try:
            if path.stat().st_size > 120_000_000:
                raise TrainingError("Run artifact exceeds 120 MB.")
            raw = path.read_bytes()
            artifact = json.loads(raw)
            meta, events = artifact["meta"], artifact["events"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise TrainingError(f"Cannot read run artifact {path}.") from error
        if not isinstance(meta, dict) or not isinstance(events, list):
            raise TrainingError(f"Invalid run artifact {path}.")
        if meta.get("complete") is not True:
            continue
        try:
            audit_run(artifact)
            verify_returns(events)
        except (ArtifactError, TrainingError) as error:
            raise TrainingError(f"Run artifact {path} failed ledger verification. {error}") from error
        run_id = str(meta.get("run_id") or hashlib.sha256(raw).hexdigest()[:20])
        for event in events:
            if isinstance(event, dict):
                if sample := DecisionSample.from_event(event, meta, run_id):
                    if sample.evidence_id not in evidence:
                        samples.append(sample)
                        evidence.add(sample.evidence_id)
    return samples


def verify_returns(events: list[dict]) -> None:
    """Check that labels are the accumulated rewards from finished days."""
    by_day = defaultdict(list)
    for event in events:
        if event.get("type") == "decision" and event.get("actor") == "phil":
            by_day[event["loop"]].append(event)
    for day in by_day.values():
        if not any("return_to_go" in event for event in day):
            continue
        total = 0.0
        for event in reversed(day):
            reward, outcome = number(event.get("reward")), number(event.get("return_to_go"))
            if reward is None or outcome is None:
                raise TrainingError("A finished day has an unlabeled decision.")
            total += reward
            if (not math.isclose(total, outcome, abs_tol=1e-5)
                    or event.get("r_t", reward) != reward or event.get("G_t", outcome) != outcome):
                raise TrainingError("A recorded return disagrees with the subsequent rewards.")


def stable_split(samples: Iterable, salt: str = "loopday-1",
                 min_holdout_groups: int = 1) -> tuple[list, list]:
    rows = list(samples)
    groups = {row.group for row in rows}
    if len(groups) < 2:
        return rows, []
    def order(group: str) -> bytes:
        return hashlib.sha256(f"{salt}\0{group}".encode()).digest()
    count = min(len(groups) - 1, max(min_holdout_groups, len(groups) // 4))
    held_out = set(sorted(groups, key=order)[:count])
    return ([row for row in rows if row.group not in held_out],
            [row for row in rows if row.group in held_out])


def features(observation: dict, action: str) -> tuple[str, ...]:
    location = observation.get("location", "")
    raw_tick = observation.get("tick", 0)
    tick = raw_tick if type(raw_tick) is int else 0
    family = action.split(":", 1)[0]
    features = [
        f"action:{action}", f"family:{family}", f"action:{action}|place:{location}",
        f"family:{family}|time:{max(0, tick)//4}",
    ]
    raw_present = observation.get("present")
    if isinstance(raw_present, list) and "rita" in raw_present:
        features.append(f"family:{family}|with:rita")
    records = observation.get("memories")
    if isinstance(records, list) and records:
        features.append(f"family:{family}|memory:yes")
    level = observation.get("piano_level", 0)
    if type(level) is int and level > 0:
        features.append(f"family:{family}|skill:piano")
    return tuple(features)


@dataclass
class OutcomeRanker:
    intercept: float
    weights: dict[str, float]
    support: dict[str, int]
    report: dict

    @property
    def usable(self) -> bool:
        delta = number(self.report.get("held_out_r2"))
        coverage = number(self.report.get("held_out_coverage"))
        train_count = number(self.report.get("train_rows"))
        test_count = number(self.report.get("held_out_scored"))
        source = self.report.get("source")
        environments = self.report.get("environments", [])
        return bool(source == "live" and isinstance(environments, list) and "local_continuation" not in environments
                    and delta is not None and delta >= 0.05
                    and coverage is not None and coverage >= 0.75
                    and train_count is not None and train_count >= 12
                    and test_count is not None and test_count >= 4)

    def score(self, observation: dict, action: str) -> float | None:
        if self.support.get(action, 0) < 2:
            return None
        value = self.intercept + sum(self.weights.get(key, 0) for key in features(observation, action))
        return value if math.isfinite(value) else None

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "intercept": self.intercept, "weights": self.weights,
                   "support": self.support, "report": self.report}
        path.write_text(stable_json(payload) + "\n")

    @classmethod
    def load(cls, path: Path | str) -> OutcomeRanker:
        try:
            path = Path(path)
            if path.stat().st_size > 2_000_000:
                raise TrainingError("Ranker manifest exceeds the supported size.")
            payload = json.loads(path.read_text())
            if payload.get("schema_version") != 1:
                raise TrainingError("Unsupported ranker schema.")
            intercept = number(payload["intercept"])
            weights, support, report = payload["weights"], payload["support"], payload["report"]
            if (intercept is None or not isinstance(weights, dict)
                    or any(number(weight) is None for weight in weights.values())
                    or not isinstance(support, dict)
                    or any(type(n) is not int or n < 0 for n in support.values())
                    or not isinstance(report, dict)):
                raise TrainingError("Invalid ranker parameters.")
        except (OSError, KeyError, ValueError, AttributeError, TypeError) as error:
            if isinstance(error, TrainingError):
                raise
            raise TrainingError(f"Cannot read ranker manifest {path}.") from error
        return cls(intercept, weights, support, report)


def fit_ranker(samples: Iterable[DecisionSample], *, regularization: float = 2.0,
               source: str = "live") -> OutcomeRanker:
    rows = [sample for sample in samples if sample.source == source]
    train, held_out = stable_split(rows)
    if not train or not 0 < regularization < 1000:
        raise TrainingError("A positive regularization and observed training decisions are required.")
    intercept = fmean(row.outcome for row in train)
    residual = [row.outcome - intercept for row in train]
    active = defaultdict(list)
    support = defaultdict(int)
    for i, row in enumerate(train):
        support[row.action] += 1
        for feature in features(row.observation, row.action):
            active[feature].append(i)
    weights = dict.fromkeys(sorted(active), 0.0)
    # Coordinate descent minimizes squared error with an L2 penalty.
    for _ in range(80):
        largest_update = 0.0
        for feature, before in weights.items():
            indices = active[feature]
            after = (sum(residual[i] for i in indices) + before * len(indices)) / (len(indices) + regularization)
            delta = after - before
            if delta:
                for i in indices:
                    residual[i] -= delta
            weights[feature] = after
            largest_update = max(largest_update, abs(delta))
        if largest_update < 1e-8:
            break
    model = OutcomeRanker(intercept, weights, dict(support), {})
    predictions = [(row, model.score(row.observation, row.action)) for row in held_out]
    scored = [(row.outcome, prediction) for row, prediction in predictions if prediction is not None]
    errors = [(actual - prediction) ** 2 for actual, prediction in scored]
    baseline = [(actual - intercept) ** 2 for actual, _ in scored]
    baseline_sse = sum(baseline)
    model.report = {
        "source": source, "train_rows": len(train), "held_out_rows": len(held_out),
        "environments": sorted({row.environment for row in rows if row.environment}),
        "train_groups": sorted({row.group for row in train}),
        "held_out_groups": sorted({row.group for row in held_out}),
        "held_out_scored": len(scored), "held_out_coverage": len(scored) / max(1, len(held_out)),
        "held_out_mae": fmean(abs(actual - prediction) for actual, prediction in scored) if scored else None,
        "baseline_mae": fmean(abs(actual - intercept) for actual, _ in scored) if scored else None,
        "held_out_r2": 1 - sum(errors) / baseline_sse if baseline_sse else None,
        "r2_definition": "skill relative to the training-set mean on the supported held-out rows",
    }
    return model


def preference_pairs(samples: Iterable[DecisionSample], *, source: str = "live",
                     min_gap: float = 0.15) -> list[dict]:
    if not math.isfinite(min_gap) or min_gap <= 0:
        raise TrainingError("The preference margin must be positive.")
    # Defer this import to keep dataset reading independent of the provider adapter.
    from .providers import PHIL_MODEL, PROMPT_VERSION, decision_messages

    buckets = defaultdict(list)
    for row in samples:
        if row.source != source:
            continue
        if source == "live" and (row.model != PHIL_MODEL or row.prompt_version != PROMPT_VERSION
                                 or not re.fullmatch(r"[a-f0-9]{40}", row.model_revision)):
            continue
        prompt = decision_messages("phil", row.observation, alias_names=row.alias_names)
        key = (row.group, row.checkpoint, row.model, row.model_revision,
               row.prompt_version, row.condition, stable_json(prompt))
        buckets[key].append(row)
    pairs = []
    for key in sorted(buckets):
        group, checkpoint, model, revision, prompt_version, condition, prompt = key
        rows = buckets[key]
        by_action = defaultdict(list)
        for row in rows:
            by_action[row.action].append(row)
        if len(by_action) < 2:
            continue
        ranked = sorted(by_action.items(), key=lambda item: (fmean(r.outcome for r in item[1]), item[0]))
        weaker, stronger = ranked[0][1], ranked[-1][1]
        low, high = fmean(r.outcome for r in weaker), fmean(r.outcome for r in stronger)
        if high - low < min_gap:
            continue

        def representative(group: list[DecisionSample], average: float) -> DecisionSample:
            return min(group, key=lambda row: (abs(row.outcome - average), row.completion, row.evidence_id))

        winner, loser = representative(stronger, high), representative(weaker, low)
        pairs.append({
            "prompt": json.loads(prompt), "chosen": winner.completion, "rejected": loser.completion,
            "chosen_action": winner.action, "rejected_action": loser.action,
            "margin": high - low, "checkpoint": checkpoint, "group": group,
            "source": source, "model": model, "condition": condition,
            "model_revision": revision, "prompt_version": prompt_version,
            "environment": winner.environment,
            "policy_observation": winner.observation, "alias_names": winner.alias_names,
            "chosen_evidence": [row.evidence_id for row in stronger if row.evidence_id],
            "rejected_evidence": [row.evidence_id for row in weaker if row.evidence_id],
        })
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("fixture", "live"), default="live")
    parser.add_argument("--ranker", type=Path, help="Write a JSON reward model manifest.")
    parser.add_argument("--preferences", type=Path, help="Write observed DPO pairs as JSONL.")
    parser.add_argument("runs", type=Path, nargs="+")
    args = parser.parse_args()
    if not (args.ranker or args.preferences):
        parser.error("Set --ranker and/or --preferences.")
    try:
        samples = read_samples(args.runs)
        if args.ranker:
            ranker = fit_ranker(samples, source=args.source)
            ranker.save(args.ranker)
            print(stable_json({**ranker.report, "usable": ranker.usable}))
        if args.preferences:
            pairs = preference_pairs(samples, source=args.source)
            args.preferences.parent.mkdir(parents=True, exist_ok=True)
            args.preferences.write_text("".join(stable_json(pair) + "\n" for pair in pairs))
            print(stable_json({"pairs": len(pairs), "source": args.source}))
    except TrainingError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
