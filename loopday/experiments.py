"""Run paired memory interventions and collect exact-checkpoint, local policy rollouts."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
from typing import Iterator

from .audit import audit_run, compare_runs
from .run_storage import exclusive_run, write_json, write_text
from .simulation import FixtureDirector, Simulation
from .town import CAST, PLACES


LABEL = "world_rollout"
WINDOWS = (1, 6, 11, 14, 16, 24, 26, 30, 32)


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def decisions(simulation: Simulation, first: int = 0):
    return (row for row in simulation.events[first:] if row["type"] == "decision" and row["actor"] == "phil")


def observed_history(events: list[dict]) -> list[dict]:
    # Rewards for earlier decisions can depend on the future, and are filled in at night.
    derived = {"reward", "return_to_go", "r_t", "G_t"}
    return [{key: value for key, value in event.items() if key not in derived} for event in events]


def artifact(simulation: Simulation, condition: str) -> dict:
    meta = {"mode": "fixture", "complete": True, "condition": condition, "seed": simulation.seed,
            "event_count": len(simulation.events), "ending": simulation.ending,
            "ending_reason": simulation.ending_reason, "provider_calls": 0}
    run = {"meta": meta, "events": simulation.events, "cast": CAST, "locations": PLACES}
    run["audit"] = audit_run(run)
    return run


def ablate_memory(seed: int) -> tuple[dict, dict[str, dict]]:
    original = Simulation(FixtureDirector(), seed=seed)
    original.run(1)
    original.advance_tick()  # Both arms observe the dawn before either makes the tested choice.
    checkpoint = original.checkpoint()
    prefix_length = len(checkpoint["events"])
    prefix = observed_history(checkpoint["events"])
    proof = next(row["id"] for row in reversed(original.events) if row["type"] == "test_result")
    puddle = next(row["id"] for row in original.events if row["type"] == "puddle")
    controls = {"intact": (), "hide_result": (proof,), "hide_puddle": (puddle,)}
    arms, choices = {}, {}
    fingerprints = set()
    for condition, withheld in controls.items():
        branch = Simulation.from_checkpoint(checkpoint, FixtureDirector(), withheld_memory=withheld)
        branch.run(2)
        first = next(decisions(branch, prefix_length))
        fingerprints.add(first["checkpoint_fingerprint"])
        if observed_history(branch.events[:prefix_length]) != prefix:
            raise ValueError("The memory condition changed history before the intervention.")
        arms[condition] = artifact(branch, condition)
        choices[condition] = {field: first[field] for field in (
            "id", "action", "tick", "recalled", "stated_support", "current_evidence", "checkpoint_fingerprint"
        )}
    if len(fingerprints) != 1:
        raise ValueError("Memory conditions did not share a physical decision checkpoint.")
    comparison = {condition: compare_runs(arms["intact"], arm) for condition, arm in arms.items()
                  if condition != "intact"}
    report = {"seed": seed, "source": "fixture", "shared_checkpoint": fingerprints.pop(),
              "prefix_events": prefix_length, "experiment_result_id": proof, "puddle_id": puddle,
              "choices": choices, "comparisons": comparison}
    return report, arms


class ForkDirector(FixtureDirector):
    def __init__(self, action: str, trial: int, seed: int):
        super().__init__(choose_community=bool(seed % 2))
        self.action, self.trial, self.seed = action, trial, seed
        self.selected = False

    def choose(self, actor: str, obs: dict) -> str:
        if actor != "phil":
            return super().choose(actor, obs)
        if not self.selected:
            self.selected = True
            if self.action not in obs["actions"]:
                raise ValueError("The forced action is unavailable at this checkpoint.")
            return json.dumps({"action": self.action, "reason": "Action reserved by a local experiment."})
        if self.trial:
            seed = f"{self.seed}:{self.trial}:{obs['tick']}:{obs['exchange']}"
            generator = random.Random(seed)
            # Common random numbers across action arms keep exploration comparable.
            if generator.random() < 0.30:
                actions = sorted(obs["actions"])
                action = actions[generator.randrange(len(actions))]
                return json.dumps({"action": action, "reason": "Sampled from the legal local actions."})
        return super().choose(actor, obs)


def day_checkpoints(seed: int, windows: tuple[int, ...] = WINDOWS) -> Iterator[tuple[dict, dict]]:
    director = FixtureDirector(choose_community=bool(seed % 2))
    simulation = Simulation(director, seed=seed, lesson_tick=(14, 16, 18)[seed % 3])
    simulation.run(1)
    for tick in range(max(windows) + 1):
        selected = tick in windows
        before = simulation.checkpoint() if selected else None
        start = len(simulation.events)
        simulation.advance_tick()
        if selected:
            first = next(decisions(simulation, start), None)
            if first is not None and first["exchange"] == 0 and len(first["available_actions"]) >= 2:
                yield before, first


def collect_rollouts(seeds: range, trials: int, windows: tuple[int, ...] = WINDOWS) -> Iterator[dict]:
    for seed in seeds:
        for checkpoint, reference in day_checkpoints(seed, windows):
            start = len(checkpoint["events"])
            expected = reference["checkpoint_fingerprint"]
            for action in sorted(reference["available_actions"]):
                for trial in range(trials):
                    director = ForkDirector(action, trial, seed)
                    simulation = Simulation.from_checkpoint(checkpoint, director)
                    simulation.run(2)
                    selected = next(decisions(simulation, start))
                    if (selected["checkpoint_fingerprint"] != expected or selected["action"] != action
                            or selected["policy_observation"] != reference["policy_observation"]):
                        raise ValueError("Decision or observation changed before the action intervention.")
                    suffix = simulation.events[start:]
                    consequences = [{"id": row["id"], "type": row["type"], "text": row["text"]}
                                    for row in suffix if row["type"] in {"kindness", "performance", "ending_decision"}]
                    yield {
                        "source": LABEL, "group": f"seed:{seed}", "seed": seed, "trial": trial,
                        "condition": "fixed_policy" if trial == 0 else "exploring_continuation",
                        "checkpoint": expected, "prefix_hash": digest(checkpoint),
                        "loop": selected["loop"], "tick": selected["tick"], "action": selected["action"],
                        "baseline_action": reference["action"], "observation": selected["policy_observation"],
                        "completion": selected["completion"], "outcome": selected["return_to_go"],
                        "immediate_reward": selected["reward"], "ending": simulation.ending,
                        "ending_reason": simulation.ending_reason,
                        "evidence_id": digest([expected, action, trial]), "consequences": consequences,
                        "suffix_hash": digest(suffix),
                    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    memory = subcommands.add_parser("memory", help="Fork from the same dawn with an individual clue withheld.")
    memory.add_argument("--seed", type=int, default=7)
    memory.add_argument("--out", type=Path, default=Path("runs/memory-forks"))
    collect = subcommands.add_parser("collect", help="Collect legal action interventions under bounded local policies.")
    collect.add_argument("--seed-start", type=int, default=11)
    collect.add_argument("--seed-count", type=int, default=12)
    collect.add_argument("--trials", type=int, default=3)
    collect.add_argument("--out", type=Path, default=Path("runs/rollouts"))
    args = parser.parse_args()
    with exclusive_run(args.out):
        if args.command == "memory":
            report, arms = ablate_memory(args.seed)
            for condition, arm in arms.items():
                write_json(args.out / f"{condition}.json", arm)
            write_json(args.out / "summary.json", report)
            print(json.dumps({"source": "fixture", "actions": {name: row["action"] for name, row in report["choices"].items()}}))
        else:
            if (not 1 <= args.seed_count <= 64 or not 1 <= args.trials <= 8
                    or not 0 <= args.seed_start <= 2**31 - args.seed_count):
                parser.error("Use 1–64 world seeds, 1–8 trials and non-negative 31-bit seeds.")
            seeds = range(args.seed_start, args.seed_start + args.seed_count)
            rows = list(collect_rollouts(seeds, args.trials))
            write_text(args.out / "rollouts.jsonl", "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"
                                                            for row in rows))
            report = {"source": LABEL, "seeds": list(seeds), "trials": args.trials, "rows": len(rows),
                      "checkpoints": len({row["checkpoint"] for row in rows}), "provider_calls": 0}
            write_json(args.out / "summary.json", report)
            print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
