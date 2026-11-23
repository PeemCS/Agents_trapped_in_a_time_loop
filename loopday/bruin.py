"""Stage an audited dataset and run the Bruin/DuckDB assets on that snapshot."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess

from .audit import audit_run, read_run
from .provenance import signal_report
from .run_storage import exclusive_run, write_json, write_text


ROOT = Path(__file__).resolve().parents[1]
VERSION = 1
MODEL_FIELDS = frozenset({"provider", "model", "model_revision", "adapter", "precision", "prompt_version",
                          "alias_names", "cache_hit", "tokens", "projection_z", "persona_bank", "selection"})


def as_rows(rows: list[dict]) -> str:
    # Typed DuckDB readers can load an empty logical table from one all-null row.
    return "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows or [{}])


def run_id(path: Path, meta: dict) -> str:
    inherited = meta.get("run_id")
    name = inherited if isinstance(inherited, str) else path.parent.name + ("-" + path.stem if path.stem != "run" else "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", name):
        raise ValueError(f"Run identifier must be alphanumeric and use hyphens or underscores: {name!r}.")
    return name


def event_row(name: str, event: dict) -> dict:
    retained = {key: value for key, value in event.items() if key not in {"completion", "model_metadata"}}
    metadata = event.get("model_metadata")
    if isinstance(metadata, dict):
        retained["model_metadata"] = {key: metadata[key] for key in MODEL_FIELDS if key in metadata}
    retained["run_id"] = name
    return retained


def prepare(paths: list[Path], rollout_path: Path | None, output: Path) -> tuple[Path, dict]:
    event_rows, meta_rows, signals, rollouts = [], [], [], []
    hashed = {}
    names = set()
    for path in paths:
        path = path / "run.json" if path.is_dir() else path
        artifact = read_run(path)
        audit = audit_run(artifact)
        metadata, events = artifact.get("meta", {}), artifact["events"]
        name = run_id(path, metadata)
        if name in names:
            raise ValueError(f"Duplicate run identifier: {name}.")
        names.add(name)
        hashed[name] = sha256(json.dumps(artifact, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        event_rows.extend(event_row(name, event) for event in events)
        signals.extend({**signal, "run_id": name} for signal in signal_report(events)["signals"])
        meta_rows.append({"run_id": name, "mode": audit["mode"], "complete": audit["complete"],
                          "ending": audit["ending"], "seed": metadata.get("seed"),
                          "condition": metadata.get("condition"), "config": metadata.get("config"),
                          "provider_calls": metadata.get("provider_calls", 0),
                          "provider_cache_hits": metadata.get("provider_cache_hits", 0),
                          "provider_usage": metadata.get("provider_usage", {})})
    if rollout_path:
        with rollout_path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                row = json.loads(line)
                if not isinstance(row, dict) or row.get("source") != "world_rollout":
                    raise ValueError(f"Expected a local action rollout at {rollout_path.name}:{number}.")
                rollouts.append({key: value for key, value in row.items() if key != "completion"})
    sources = {"runs": hashed, "local_rollout_file": sha256(as_rows(rollouts).encode()).hexdigest() if rollouts else None}
    revision = sha256(json.dumps([VERSION, sources], sort_keys=True).encode()).hexdigest()[:16]
    dataset = output / revision
    report = {"version": VERSION, "revision": revision, **sources, "events": len(event_rows),
              "runs_count": len(meta_rows), "provenance_signals": len(signals), "local_rollouts": len(rollouts)}
    with exclusive_run(dataset):
        for name, rows in (("events", event_rows), ("metadata", meta_rows), ("signals", signals), ("rollouts", rollouts)):
            write_text(dataset / f"{name}.ndjson", as_rows(rows))
        write_json(dataset / "manifest.json", report)
    return dataset, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+", help="Run directories or run artifacts.")
    parser.add_argument("--rollouts", type=Path, help="Optional output from loopday.experiments collect.")
    parser.add_argument("--out", type=Path, default=Path("runs/.bruin-inputs"))
    parser.add_argument("--execute", action="store_true", help="Run the installed Bruin CLI after staging.")
    args = parser.parse_args()
    try:
        dataset, report = prepare(args.runs, args.rollouts, args.out)
        print(json.dumps({**report, "dataset": str(dataset.resolve())}), flush=True)
        if args.execute:
            binary = shutil.which("bruin")
            if not binary:
                raise ValueError("Install the Bruin CLI before passing --execute.")
            if not (ROOT / ".bruin.yml").is_file():
                raise ValueError("Copy .bruin.yml.example to .bruin.yml before executing Bruin.")
            path = str(dataset.resolve()).replace("'", "''")
            variable = json.dumps({"dataset": path})
            common = [str(ROOT / "pipeline"), "--var", variable, "--config-file", str(ROOT / ".bruin.yml")]
            subprocess.run([binary, "validate", *common], cwd=ROOT, check=True)
            subprocess.run([binary, "run", *common, "--workers", "1"], cwd=ROOT, check=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Bruin dataset: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
