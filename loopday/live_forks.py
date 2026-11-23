"""Sample one Qwen decision and compare its legal actions under a fixed local continuation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_run
from .experiments import day_checkpoints, decisions, digest
from .providers import LiveDirector, ModelError, PhilOptions, load_settings
from .run import phil_backend
from .run_storage import CallJournal, exclusive_run, read_json, write_json
from .simulation import Choice, FixtureDirector, Simulation
from .town import CAST, PLACES


MODE = "live_candidate_local_continuation"
ENVIRONMENT = "local_continuation"


class BranchDirector(FixtureDirector):
    def __init__(self, shot, candidate, *, fixture_community: bool):
        super().__init__(choose_community=fixture_community)
        self.batch = shot
        self.candidate = candidate
        self.has_selected = False
        self.selected_model_candidate = False

    def is_live(self, actor: str) -> bool:
        return actor == "phil" and not self.has_selected

    def choose(self, actor: str, observation: dict) -> str:
        self.selected_model_candidate = False
        if self.is_live(actor):
            self.selected_model_candidate = True
            self.has_selected = True
            return self.candidate.completion
        return super().choose(actor, observation)

    def decision_metadata(self) -> dict:
        if self.selected_model_candidate:
            info = self.batch.metadata_for(self.candidate, selection="paired_intervention")
            return {**info, "environment": ENVIRONMENT}
        return {}


def inspect_checkpoint(state: dict) -> tuple[dict, int]:
    seed = state["config"]["seed"]
    control = Simulation.from_checkpoint(state, FixtureDirector(choose_community=bool(seed % 2)))
    if control.ending == "day_two":
        raise ValueError("Use a checkpoint before the episode has ended.")
    cursor = len(control.events)
    ticks = control.day_ticks or 36
    control.advance_tick(ticks)
    reference = next(decisions(control, cursor), None)
    if reference is None or reference["exchange"] != 0 or len(reference["available_actions"]) < 2:
        raise ValueError("Choose a checkpoint immediately before a scheduled Phil decision with multiple actions.")
    return reference, ticks


def evaluate_batch(state: dict, reference: dict, ticks: int, batch) -> list[dict]:
    seed = state["config"]["seed"]
    start = len(state["events"])
    starting_observation = reference["policy_observation"]
    checkpoint_hash = reference["checkpoint_fingerprint"]
    branches = []
    for candidate in batch.legal_candidates:
        if not Choice.read(candidate.completion, starting_observation["actions"]):
            continue
        director = BranchDirector(batch, candidate, fixture_community=bool(seed % 2))
        simulation = Simulation.from_checkpoint(state, director)
        simulation.run(reference["loop"], ticks)
        event = next(decisions(simulation, start))
        if event["policy_observation"] != starting_observation or event["checkpoint_fingerprint"] != checkpoint_hash:
            raise ValueError("The interventions did not share the same initial decision checkpoint.")
        if event.get("completion") != candidate.completion or event["action"] != candidate.action:
            continue
        metadata = {
            "mode": MODE, "complete": True, "seed": seed, "condition": ENVIRONMENT,
            "run_id": f"fork-{batch.batch_id[:16]}-{checkpoint_hash[:8]}-{candidate.index}",
            "ending": simulation.ending, "ending_reason": simulation.ending_reason, "event_count": len(simulation.events),
            "intervention": {"target_event_id": event["id"], "batch_id": batch.batch_id,
                             "environment": ENVIRONMENT, "checkpoint": checkpoint_hash},
        }
        arm = {"meta": metadata, "events": simulation.events, "cast": CAST, "locations": PLACES}
        arm["audit"] = audit_run(arm)
        branches.append(arm)
    return branches


def save_branches(out: Path, plan: dict, batch, arms: list[dict], director) -> None:
    results = []
    for arm in arms:
        meta = arm["meta"]
        destination = out / meta["run_id"]
        destination.mkdir(exist_ok=False)
        write_json(destination / "run.json", arm)
        target = next(event for event in arm["events"] if event["id"] == meta["intervention"]["target_event_id"])
        results.append({"artifact": str(destination / "run.json"), "decision_id": target["id"],
                        "action": target["action"], "observed_return": target["return_to_go"],
                        "ending_reason": meta["ending_reason"]})
    write_json(out / "result.json", {**plan, "batch_id": batch.batch_id, "branches": results,
                                      "has_distinct_legal_choices": len(results) >= 2,
                                      "model_calls": director.calls, "usage": director.usage})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--tick", type=int, default=26)
    parser.add_argument("--checkpoint", type=Path, help="Optional previously saved world checkpoint before a Phil turn.")
    parser.add_argument("--candidates", type=int, default=3)
    parser.add_argument("--phil-in-process", action="store_true")
    parser.add_argument("--phil-revision")
    parser.add_argument("--phil-4bit", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("runs/live-fork"))
    parser.add_argument("--execute", action="store_true", help="Spend one bounded Qwen call on the alternatives.")
    parser.set_defaults(phil_adapter=None, phil_persona_bank=None)
    args = parser.parse_args()
    if not (0 <= args.seed < 2**31 and 0 <= args.tick < 36 and 2 <= args.candidates <= 4):
        parser.error("Choose a valid seed, a tick from 0–35, and 2–4 candidates.")
    if args.phil_in_process and not args.phil_revision:
        parser.error("The in-process backend needs its exact model commit.")
    try:
        with exclusive_run(args.out):
            if args.checkpoint:
                snapshot = read_json(args.checkpoint)
                snapshot = snapshot["world"] if "world" in snapshot else snapshot
            else:
                snapshot, _ = next(day_checkpoints(args.seed, (args.tick,)))
            reference, ticks = inspect_checkpoint(snapshot)
            plan = {"mode": MODE, "checkpoint_fingerprint": reference["checkpoint_fingerprint"],
                    "world_snapshot_sha256": digest(snapshot), "loop": reference["loop"], "tick": reference["tick"],
                    "seed": snapshot["config"]["seed"], "actions": reference["available_actions"],
                    "max_candidates": args.candidates, "max_model_calls": 1, "max_muse_calls": 0}
            write_json(args.out / "plan.json", plan)
            if args.execute:
                _, backend = phil_backend(args)
                journal = CallJournal(args.out / ".calls.json")
                if journal.path.exists() or (args.out / "result.json").exists():
                    raise ValueError("This directory already reserved its Qwen call. Choose a new trial output.")
                options = PhilOptions(candidates=args.candidates, seed=plan["seed"])
                director = LiveDirector(load_settings(), 1, phil_only=True, alias_names=True,
                                        phil_options=options, phil_backend=backend)
                director.on_attempt = lambda count: journal.reserve(director, count)
                batch = director.sample_phil(reference["policy_observation"])
                arms = evaluate_batch(snapshot, reference, ticks, batch)
                save_branches(args.out, plan, batch, arms, director)
            print(json.dumps({**plan, "executed": args.execute}))
    except StopIteration:
        parser.exit(1, "No eligible Phil decision was found at that tick. Try tick 26.\n")
    except (KeyError, TypeError, ValueError, OSError, ModelError) as error:
        parser.exit(1, f"Qwen fork: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
