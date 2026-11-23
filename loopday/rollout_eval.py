"""Fit and evaluate a policy on forced-action rollouts of the local town."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from dataclasses import dataclass
import hashlib
from io import StringIO
import json
from pathlib import Path
import random
import re
from statistics import fmean

from .learning import DecisionSample, OutcomeRanker, TrainingError, fit_ranker, number, stable_split
from .providers import completion_action
from .run_storage import exclusive_run, write_json


SOURCE = "world_rollout"
DIGEST = re.compile(r"[a-f0-9]{64}")
BASELINES = ("ranker", "fixture", "uniform", "oracle")


@dataclass(frozen=True)
class Trial:
    index: int
    outcome: float
    day_two: bool
    evidence: str


@dataclass
class Checkpoint:
    identifier: str
    group: str
    prefix: str
    observation: dict
    baseline: str
    trials: dict[str, dict[int, Trial]]

    def trial_index(self) -> set[int]:
        shared = next(iter(self.trials.values())).keys()
        if (set(self.trials) != set(self.observation["actions"]) or 0 not in shared
                or any(rows.keys() != shared for rows in self.trials.values())):
            raise TrainingError("Each checkpoint requires every legal action and a matching set of trials.")
        return set(shared)

    def samples(self) -> list[DecisionSample]:
        return [
            DecisionSample(self.group, SOURCE, self.identifier, self.observation, action,
                           json.dumps({"action": action}), fmean(row.outcome for row in rows.values()))
            for action, rows in self.trials.items()
        ]


def read_verified_index(path: Path) -> tuple[set[str], str]:
    try:
        if path.stat().st_size > 12_000_000:
            raise TrainingError("Verified evidence index exceeds the supported size.")
        raw = path.read_bytes()
        body = raw.decode("utf-8-sig")
        if path.suffix == ".csv":
            rows = list(csv.DictReader(StringIO(body)))
        elif path.suffix in (".jsonl", ".ndjson"):
            rows = [json.loads(line) for line in body.splitlines() if line.strip()]
        else:
            rows = json.loads(body)
        if not isinstance(rows, list) or not rows:
            raise TrainingError("Verified index must contain at least one evidence ID.")
        ids = set()
        for row in rows:
            evidence = row.get("evidence_id") if isinstance(row, dict) else row
            if not isinstance(evidence, str) or not DIGEST.fullmatch(evidence) or evidence in ids:
                raise TrainingError("Verified index contains a malformed or duplicate evidence ID.")
            ids.add(evidence)
        return ids, hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, TypeError, csv.Error, RecursionError) as error:
        if isinstance(error, TrainingError):
            raise
        raise TrainingError(f"Cannot read verified evidence index {path}.") from error


def read_rollouts(path: Path, verified_index: set[str] | None = None) -> tuple[list[Checkpoint], str]:
    try:
        cases = {}
        complete = hashlib.sha256()
        with path.open("rb") as stream:
            for i, line in enumerate(stream):
                if i >= 100_000 or len(line) > 64_000:
                    raise TrainingError("Rollouts exceed the supported dataset size.")
                complete.update(line)
                row = json.loads(line)
                if not isinstance(row, dict) or row.get("source") != SOURCE:
                    raise TrainingError("Expected the local forced-action rollout format.")
                checkpoint, prefix, evidence = (row[key] for key in ("checkpoint", "prefix_hash", "evidence_id"))
                observation, action, baseline = (row[key] for key in ("observation", "action", "baseline_action"))
                trial, seed, group = (row[key] for key in ("trial", "seed", "group"))
                outcome = number(row.get("outcome"))
                if (not all(isinstance(digest, str) and DIGEST.fullmatch(digest)
                            for digest in (checkpoint, prefix, evidence))
                        or type(trial) is not int or not 0 <= trial <= 7
                        or type(seed) is not int or group != f"seed:{seed}" or outcome is None
                        or not isinstance(observation, dict)):
                    raise TrainingError("Rollout rows require bounded, identified outcomes and seeds.")
                if row.get("condition") != ("fixed_policy" if trial == 0 else "exploring_continuation"):
                    raise TrainingError("The trial label does not match its continuation policy.")
                actions = observation.get("actions")
                if (not isinstance(actions, list) or not all(isinstance(item, str) for item in actions)
                        or len(actions) < 2 or len(actions) != len(set(actions)) or baseline not in actions
                        or not isinstance(action, str) or completion_action(row.get("completion"), actions) != action):
                    raise TrainingError("Rollout rows require valid choices from one legal action set.")
                key = group, checkpoint
                case = cases.get(key)
                if case is None:
                    case = cases[key] = Checkpoint(checkpoint, group, prefix, observation, baseline, defaultdict(dict))
                elif (case.prefix, case.observation, case.baseline) != (prefix, observation, baseline):
                    raise TrainingError("The world or policy observation changed before an action intervention.")
                if trial in case.trials[action]:
                    raise TrainingError("Duplicate checkpoint/action/trial row.")
                case.trials[action][trial] = Trial(trial, outcome, row.get("ending") == "day_two", evidence)
        if not cases:
            raise TrainingError("At least one complete checkpoint is required.")
        evidence_ids = set()
        verified_cases = []
        for case in cases.values():
            case.trial_index()
            rows = [row.evidence for trials in case.trials.values() for row in trials.values()]
            ids = set(rows)
            if len(ids) != len(rows) or ids & evidence_ids:
                raise TrainingError("A rollout evidence ID was reused.")
            evidence_ids.update(ids)
            if verified_index is not None:
                matching = ids & verified_index
                if matching and matching != ids:
                    raise TrainingError("The verified index includes only part of a checkpoint's actions or trials.")
                if matching:
                    verified_cases.append(case)
        if verified_index is not None:
            if verified_index - evidence_ids:
                raise TrainingError("The verified index points to evidence missing from these rollouts.")
            return verified_cases, complete.hexdigest()
        return list(cases.values()), complete.hexdigest()
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        if isinstance(error, TrainingError):
            raise
        raise TrainingError(f"Cannot read rollout data at {path}.") from error


def policy_row(case: Checkpoint, ranker, continuation: str) -> dict | None:
    trial_indices = case.trial_index()
    if continuation == "fixed":
        trial_indices = {0}
    elif continuation == "exploring":
        trial_indices.remove(0)
    if not trial_indices:
        return None
    outcomes = {}
    day_two = {}
    for action, trials in case.trials.items():
        rows = [trials[i] for i in sorted(trial_indices)]
        outcomes[action] = fmean(row.outcome for row in rows)
        day_two[action] = fmean(row.day_two for row in rows)

    predictions = {action: ranker.score(case.observation, action) for action in outcomes}
    available = all(value is not None for value in predictions.values())
    ranked = max(predictions, key=lambda action: (predictions[action], action == case.baseline)) if available else case.baseline
    oracle = max(outcomes, key=lambda action: (outcomes[action], action == case.baseline))
    return {
        "seed": case.group, "checkpoint": case.identifier, "tick": case.observation.get("tick"),
        "ranked_action": ranked, "baseline_action": case.baseline, "oracle_action": oracle,
        "coverage": available, "oracle_tie": outcomes[ranked] == outcomes[oracle],
        "return": {"ranker": outcomes[ranked], "fixture": outcomes[case.baseline],
                   "uniform": fmean(outcomes.values()), "oracle": outcomes[oracle]},
        "day_two": {"ranker": day_two[ranked], "fixture": day_two[case.baseline],
                    "uniform": fmean(day_two.values()), "oracle": day_two[oracle]},
    }


def interval(seed_deltas: list[float], seed: int = 767) -> list[float] | None:
    if len(seed_deltas) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(fmean(rng.choices(seed_deltas, k=len(seed_deltas))) for _ in range(4096))
    return [means[int(0.025 * len(means))], means[int(0.975 * len(means))]]


def report_rows(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[row["seed"]].append(row)
    by_seed = {
        group: {
            "checkpoints": len(checkpoints),
            "return": {policy: fmean(row["return"][policy] for row in checkpoints) for policy in BASELINES},
            "day_two_rate": {policy: fmean(row["day_two"][policy] for row in checkpoints) for policy in BASELINES},
        }
        for group, checkpoints in sorted(groups.items())
    }
    comparisons = {}
    for baseline in ("fixture", "uniform"):
        deltas = [row["return"]["ranker"] - row["return"][baseline] for row in by_seed.values()]
        comparisons[baseline] = {"return_delta": fmean(deltas), "seed_bootstrap_95": interval(deltas)}
    return {
        "checkpoints": len(rows), "seeds": len(by_seed), "ranker_coverage": fmean(row["coverage"] for row in rows),
        "ranker_oracle_match": fmean(row["oracle_tie"] for row in rows),
        "return": {policy: fmean(row["return"][policy] for row in by_seed.values()) for policy in BASELINES},
        "day_two_rate": {policy: fmean(row["day_two_rate"][policy] for row in by_seed.values()) for policy in BASELINES},
        "paired_comparisons": comparisons, "per_seed": by_seed,
    }


def evaluate_policy(ranker: OutcomeRanker, test_cases: list[Checkpoint]) -> tuple[dict, dict]:
    if not test_cases or ranker.report.get("source") != SOURCE:
        raise TrainingError("Policy evaluation requires a local rollout ranker and held-out checkpoints.")
    reports, decisions = {}, {}
    for continuation in ("mixed", "fixed", "exploring"):
        rows = [row for case in test_cases if (row := policy_row(case, ranker, continuation)) is not None]
        if rows:
            reports[continuation] = report_rows(rows)
            decisions[continuation] = rows
    output = {
        "source": SOURCE, "test_checkpoints": len(test_cases),
        "training_seeds": ranker.report["train_groups"],
        "held_out_seeds": sorted({case.group for case in test_cases}),
        "live_ranker_usable": ranker.usable, "conditions": reports,
        "estimand": "Change the first action in a fixed world checkpoint under these continuation policies.",
        "oracle": "Optimistic ceiling that chooses using the same outcomes used for scoring.",
        "uncertainty": "Percentile bootstrap over held-out seed means with 4,096 draws. Few seeds give coarse intervals.",
    }
    return output, decisions


def fit_and_evaluate(cases: list[Checkpoint]) -> tuple[OutcomeRanker, dict, dict]:
    train_cases, test_cases = stable_split(cases)
    if not train_cases or not test_cases:
        raise TrainingError("At least two distinct scenario seeds are required for held-out evaluation.")
    # fit_ranker uses the same seed split internally. One row per action and
    # checkpoint averages alternate continuation trials without duplicating cases.
    ranker = fit_ranker([row for case in cases for row in case.samples()], source=SOURCE)
    if set(ranker.report["held_out_groups"]) != {case.group for case in test_cases}:
        raise TrainingError("Ranker and policy experiments disagree on the held-out seeds.")
    output, decisions = evaluate_policy(ranker, test_cases)
    output.update(train_checkpoints=len(train_cases), evaluation_type="seed_holdout")
    return ranker, output, decisions


def evaluate_external(ranker: OutcomeRanker, test_cases: list[Checkpoint]) -> tuple[dict, dict]:
    previous_train = ranker.report.get("train_groups")
    previous_test = ranker.report.get("held_out_groups")
    if any(not isinstance(groups, list) or not groups or not all(isinstance(g, str) for g in groups)
           for groups in (previous_train, previous_test)):
        raise TrainingError("The ranker needs auditable training and previous holdout seed groups.")
    if {case.group for case in test_cases} & (set(previous_train) | set(previous_test)):
        raise TrainingError("External evaluation seeds must be new to this model and its previous holdout.")
    output, decisions = evaluate_policy(ranker, test_cases)
    output["evaluation_type"] = "external_seeds"
    return output, decisions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rollouts", type=Path, help="JSONL from python -m loopday.experiments collect.")
    parser.add_argument("--out", type=Path, default=Path("runs/rollout-eval"))
    parser.add_argument("--verified-index", type=Path,
                        help="Bruin-qualified evidence IDs as JSON, JSONL, NDJSON, or CSV.")
    parser.add_argument("--external-check", type=Path,
                        help="Evaluate a fitted rollout ranker on entirely new seeds, without refitting.")
    args = parser.parse_args()
    try:
        allowed, index_digest = read_verified_index(args.verified_index) if args.verified_index else (None, None)
        cases, digest = read_rollouts(args.rollouts, allowed)
        if args.external_check:
            ranker = OutcomeRanker.load(args.external_check)
            report, decisions = evaluate_external(ranker, cases)
            report["ranker_sha256"] = hashlib.sha256(args.external_check.read_bytes()).hexdigest()
        else:
            ranker, report, decisions = fit_and_evaluate(cases)
        report["rollout_sha256"] = digest
        if index_digest is not None:
            report["verified_index_sha256"] = index_digest
            report["verified_evidence_rows"] = len(allowed)
        with exclusive_run(args.out):
            if not args.external_check:
                ranker.save(args.out / "ranker.json")
            write_json(args.out / "evaluation.json", report)
            write_json(args.out / "held-out-decisions.json", decisions)
        print(json.dumps({key: report[key] for key in ("source", "evaluation_type", "test_checkpoints",
                                                       "held_out_seeds", "live_ranker_usable")}
                         | {"mixed_returns": report["conditions"]["mixed"]["return"]}))
    except TrainingError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
