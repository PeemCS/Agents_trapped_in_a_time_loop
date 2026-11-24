"""Run a LOOPDAY simulation and save its output for replay."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import file_digest, sha256
import json
from pathlib import Path
import re

from .audit import ArtifactError, audit_run
from .band import BandTransport
from .learning import OutcomeRanker, TrainingError
from .metrics import summarize_days
from .providers import (LiveDirector, MUSE_MODEL, NPC_PROMPT_VERSION, ModelError, PHIL_MODEL, PROMPT_VERSION,
                        PhilOptions, load_settings)
from .provenance import signal_report
from .run_storage import CallJournal, RunStorageError, exclusive_run, read_json, write_json, write_text
from .simulation import FixtureDirector, Simulation
from .town import CAST, PLACES
from .film import build_film


def passed_canary(path: Path) -> bool:
    try:
        run = json.loads(path.read_text())
        meta = run["meta"]
        events = run["events"]
        if meta["mode"] != "live" or not meta["complete"] or not 0 < meta["provider_calls"] <= 24:
            return False
        if any(event["type"] == "rejected" for event in events):
            return False
        actors = {event.get("actor") for event in events if event["type"] == "decision" and event.get("mode") == "live"}
        if not set(CAST).issubset(actors):
            return False
        if meta.get("schema_version") != 2:
            return True  # Compatibility for a prior completed canary artifact.
        if (meta.get("completed_loops") != 1 or not 1 <= meta["config"]["ticks"] <= 8
                or meta.get("failure") is not None or audit_run(run)["event_count"] != len(events)):
            return False
        live = [event for event in events if event["type"] == "decision" and event.get("mode") == "live"]
        for actor in CAST:
            expected_model, expected_provider = (PHIL_MODEL, "colab") if actor == "phil" else (MUSE_MODEL, "meta")
            prompt_version = PROMPT_VERSION if actor == "phil" else NPC_PROMPT_VERSION
            if not any(event["actor"] == actor and event.get("action") in event.get("available_actions", [])
                       and event.get("model_metadata", {}).get("model") == expected_model
                       and event.get("model_metadata", {}).get("provider") == expected_provider
                       and event.get("model_metadata", {}).get("prompt_version") == prompt_version for event in live):
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def verified_runtime(path: Path, configuration: dict) -> dict:
    if not passed_canary(path):
        raise RunStorageError("This live run needs a completed all-agent canary.")
    run = read_json(path)
    canary = run["meta"].get("config", {})
    options = ("alias_names", "ranker_digest", "phil_backend")
    left = {key: value for key, value in (canary.get("generation") or {}).items() if key != "seed"}
    right = {key: value for key, value in (configuration.get("generation") or {}).items() if key != "seed"}
    if left != right or any(canary.get(key) != configuration.get(key) for key in options):
        raise RunStorageError("Run a new canary with the same model, alias and generation settings.")

    fields = ("model_revision", "precision", "adapter", "persona_bank")
    phil = [row.get("model_metadata", {}) for row in run["events"]
            if row["type"] == "decision" and row.get("actor") == "phil" and row.get("mode") == "live"]
    runtime = {key: phil[0].get(key) for key in fields}
    if any({key: row.get(key) for key in fields} != runtime for row in phil):
        raise RunStorageError("The canary switched Phil's model configuration during the run.")
    if not (isinstance(runtime["model_revision"], str) and re.fullmatch(r"[a-f0-9]{40}", runtime["model_revision"])
            and isinstance(runtime["precision"], str) and isinstance(runtime["adapter"], str)):
        raise RunStorageError("The canary did not record Phil's exact runtime identity.")
    return runtime


def needs_canary(args: argparse.Namespace) -> bool:
    return args.live and (args.loops > 1 or args.ticks > 8 or args.max_calls > 24)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loops", type=int, default=2)
    parser.add_argument("--ticks", type=int, default=36)
    parser.add_argument("--lesson-tick", type=int, default=16)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--policy-seed", type=int, help="Change only the autonomous local agents' random choices.")
    parser.add_argument("--no-memory", action="store_true")
    parser.add_argument("--pencil-stays-broken", action="store_true", help="Change the pencil reset rule for an experiment.")
    parser.add_argument("--alias-names", action="store_true", help="Use alternative names in prompts and preserve canonical names in the film.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--local", action="store_true", help="Use autonomous rule policies without provider calls.")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--muse-canary", action="store_true")
    parser.add_argument("--max-calls", type=int, default=40)
    parser.add_argument("--no-persistent-cache", action="store_true")
    parser.add_argument("--phil-candidates", type=int, default=1)
    parser.add_argument("--phil-seed", type=int, help="Vary Qwen generation independently of the world seed.")
    parser.add_argument("--phil-thinking", action="store_true")
    parser.add_argument("--phil-capture-trace", action="store_true")
    parser.add_argument("--phil-monitor", action="store_true")
    parser.add_argument("--phil-steer", type=Path, help="JSON object of coefficients for the loaded persona bank.")
    parser.add_argument("--phil-ranker", type=Path, help="Validated live outcome ranker JSON.")
    parser.add_argument("--phil-in-process", action="store_true", help="Run Qwen in this CUDA Python process.")
    parser.add_argument("--phil-revision", help="Exact base Qwen commit for an in-process run.")
    parser.add_argument("--phil-4bit", action="store_true", help="Load the in-process Qwen in NF4 precision.")
    parser.add_argument("--phil-persona-bank", type=Path)
    parser.add_argument("--phil-adapter", type=Path)
    parser.add_argument("--band-config", type=Path, help="Send selected in-character dialogue to the configured Band room.")
    parser.add_argument("--band-message-limit", type=int, default=4)
    parser.add_argument("--verified-canary", type=Path, default=Path("runs/live-canary/run.json"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("runs/preflight"))
    args = parser.parse_args()
    if not 1 <= args.loops <= 40 or not 1 <= args.ticks <= 36 or not 0 <= args.lesson_tick < 36:
        parser.error("loops must be 1–40, ticks 1–36, and lesson-tick 0–35.")
    if args.max_calls < 1:
        parser.error("max-calls must be positive.")
    if not 0 <= args.seed < 2**31 or (args.policy_seed is not None and not 0 <= args.policy_seed < 2**31):
        parser.error("Seeds must be non-negative 31-bit integers.")
    if args.policy_seed is not None and not args.local:
        parser.error("--policy-seed requires --local.")
    if not args.live and (args.phil_candidates != 1 or args.phil_seed is not None or args.phil_thinking or args.phil_capture_trace
                          or args.phil_monitor or args.phil_steer or args.phil_ranker or args.phil_in_process):
        parser.error("Phil generation settings require --live.")
    if not args.phil_in_process and (args.phil_revision or args.phil_4bit or args.phil_persona_bank or args.phil_adapter):
        parser.error("Phil weight-loading options require --phil-in-process.")
    if args.phil_in_process:
        from server.model import REVISION

        if not args.phil_revision or not REVISION.fullmatch(args.phil_revision):
            parser.error("--phil-in-process requires the exact 40-character --phil-revision.")
    if args.band_config and not (args.live or args.muse_canary or args.local):
        parser.error("Band transport requires an autonomous policy or live model.")
    if args.alias_names and not (args.live or args.muse_canary):
        parser.error("The model-facing alias condition requires live inference.")
    if args.muse_canary and (args.loops != 1 or args.ticks > 8 or args.max_calls > 24):
        parser.error("A Muse canary runs one short day of at most eight ticks and 24 provider calls.")
    if needs_canary(args) and not passed_canary(args.verified_canary):
        parser.error("This live run needs a completed all-agent canary. Run the short check first.")

    try:
        with exclusive_run(args.out):
            return execute(args)
    except (ModelError, RunStorageError, TrainingError, OSError, ValueError) as error:
        parser.exit(2, f"LOOPDAY: {error}\n")


def phil_backend(args: argparse.Namespace) -> tuple[dict | None, object]:
    if not args.phil_in_process:
        return None, None
    from server.model import QwenModel

    assets = {"persona_bank": args.phil_persona_bank} if args.phil_persona_bank else {}
    if args.phil_adapter:
        assets.update({name: args.phil_adapter / name for name in (
            "training_manifest.json", "adapter_config.json", "adapter_model.safetensors"
        )})
    digests = {}
    for name, path in assets.items():
        with path.open("rb") as stream:
            digests[name] = file_digest(stream, "sha256").hexdigest()
    configuration = {"model": PHIL_MODEL, "revision": args.phil_revision, "quantize_4bit": args.phil_4bit,
                     "asset_digests": digests}
    model = None

    def generate(payload: dict) -> dict:
        nonlocal model
        if model is None:
            model = QwenModel(revision=args.phil_revision, quantize=args.phil_4bit,
                              persona_bank=args.phil_persona_bank, adapter=args.phil_adapter)
        return model.generate(payload)

    return configuration, generate


def execute(args: argparse.Namespace) -> int:
    options = PhilOptions(candidates=args.phil_candidates, thinking=args.phil_thinking,
                          capture_trace=args.phil_capture_trace, monitor=args.phil_monitor,
                          steering=read_json(args.phil_steer) if args.phil_steer else None,
                          seed=(args.phil_seed if args.phil_seed is not None else args.seed) if args.live else None)
    ranker = None
    ranker_digest = None
    if args.phil_ranker:
        ranker_bytes = args.phil_ranker.read_bytes()
        ranker = OutcomeRanker.load(args.phil_ranker)
        if not ranker.usable or args.phil_candidates < 2:
            raise RunStorageError("Ranking needs a supported live ranker and at least two candidates.")
        ranker_digest = sha256(ranker_bytes).hexdigest()

    cache = None if args.no_persistent_cache else Path("runs/.cache/models.sqlite3")
    backend_config, generate = phil_backend(args)
    fixture = FixtureDirector()
    policy_seed = None
    policy_version = None
    if args.local:
        from .local_agents import POLICY_VERSION, LocalDirector

        policy_seed = args.policy_seed if args.policy_seed is not None else args.seed
        policy_version = POLICY_VERSION
        director = LocalDirector(seed=policy_seed)
    elif args.live or args.muse_canary:
        director = LiveDirector(load_settings(), args.max_calls, cache, fixture if args.muse_canary else None,
                                phil_options=options, ranker=ranker, alias_names=args.alias_names, phil_backend=generate)
    else:
        director = fixture
    band = (BandTransport.configured(args.band_config, args.out / ".band.json", args.band_message_limit)
            if args.band_config else None)
    simulation = Simulation(director, keep_memory=not args.no_memory, lesson_tick=args.lesson_tick,
                            seed=args.seed, reset_pencil=not args.pencil_stays_broken,
                            **({"transport": band} if band else {}))
    checkpoint_path = args.out / "checkpoint.json"
    journal = CallJournal(args.out / ".calls.json")
    configuration = {
        "mode": director.mode, "ticks": args.ticks, "lesson_tick": args.lesson_tick,
        "keep_memory": not args.no_memory, "seed": args.seed, "reset_pencil": not args.pencil_stays_broken,
        "generation": asdict(options) if args.live else None, "ranker_digest": ranker_digest,
        "phil_backend": backend_config,
        "policy_seed": policy_seed, "policy_version": policy_version,
        "band": band.config_fingerprint if band else None, "alias_names": args.alias_names,
    }
    if needs_canary(args):
        director.expected_phil_runtime = verified_runtime(args.verified_canary, configuration)
        configuration["verified_phil_runtime"] = director.expected_phil_runtime
    if args.resume:
        state = read_json(checkpoint_path)
        previous = state.get("config")
        if state.get("format") == 1 and director.mode == "fixture" and args.seed == 7 and not args.pencil_stays_broken:
            matches = isinstance(previous, dict) and all(previous.get(key) == configuration[key]
                for key in ("mode", "ticks", "lesson_tick", "keep_memory"))
        else:
            matches = state.get("format") == 2 and previous == configuration
        if not matches:
            raise RunStorageError("The checkpoint and run settings differ.")
        try:
            simulation.restore(state["world"])
        except (KeyError, TypeError, ValueError) as error:
            raise RunStorageError("The checkpoint has invalid world state.") from error
        if args.loops < simulation.loop:
            raise RunStorageError("loops must include the saved world day.")
        if isinstance(director, LiveDirector):
            journal.restore(director, state)
            if simulation.completed_loops < args.loops and simulation.ending != "day_two" and director.calls >= args.max_calls:
                raise RunStorageError("The run has already reserved its total provider call limit.")
    elif any(path.exists() for path in (checkpoint_path, journal.path, args.out / "run.json")):
        raise RunStorageError("Output already contains a run. Pass --resume or choose a new --out directory.")

    def save_checkpoint(world: dict) -> None:
        write_json(checkpoint_path, {
            "format": 2, "config": configuration, "world": world, "provider": journal.counters(director),
        })
        if band:
            receipts = {item["receipt"] for event in simulation.events
                        if isinstance(item := event.get("transport"), dict)
                        and item.get("verified_recipients") and item.get("receipt")}
            band.acknowledge(receipts)

    if not args.resume or band:
        save_checkpoint(simulation.checkpoint())
    if isinstance(director, LiveDirector):
        director.on_attempt = lambda count: journal.reserve(director, count)
    failure = None
    try:
        while simulation.completed_loops < args.loops and simulation.ending != "day_two":
            simulation.advance_tick(args.ticks)
            save_checkpoint(simulation.checkpoint())
    except ModelError as error:
        failure = str(error)

    report = {
        "schema_version": 2, "mode": director.mode, "complete": failure is None, "failure": failure,
        "run_id": args.out.resolve().name, "seed": args.seed,
        "ending": simulation.ending, "ending_reason": simulation.ending_reason, "loops": simulation.loop,
        "completed_loops": simulation.completed_loops, "last_tick": simulation.tick,
        "decisions": simulation.live_decisions, "replayed": simulation.replayed_decisions,
        "provider_calls": getattr(director, "calls", 0),
        "provider_cache_hits": getattr(director, "cache_hits", 0),
        "provider_usage": dict(getattr(director, "usage", {})),
        "band": band.summary() if band else None,
        "event_count": len(simulation.events),
        "config": configuration,
    }
    artifact = {"meta": report, "cast": CAST, "locations": PLACES, "events": simulation.events}
    try:
        artifact["audit"] = audit_run(artifact)
        artifact["provenance"] = signal_report(simulation.events)
        artifact["days"] = summarize_days(simulation.events)
        if simulation.events:
            artifact["film"] = build_film(artifact)
    except (ArtifactError, ValueError) as error:
        report.update(complete=False, failure=f"Artifact verification failed: {error}")
    write_json(args.out / "memory.json", simulation.memory.records)
    if "film" in artifact:
        write_json(args.out / "film.json", artifact["film"])
    for day in artifact.get("days", []):
        if day["complete"]:
            write_json(args.out / f"night_{day['loop']:02d}.json", day)
    write_text(
        args.out / "events.jsonl",
        "".join(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n" for event in simulation.events),
    )
    write_json(args.out / "run.json", artifact)
    print(json.dumps(report))
    return int(not report["complete"])


if __name__ == "__main__":
    raise SystemExit(main())
