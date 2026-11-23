"""Provision one bounded Colab runtime, monitor a detached worker and retrieve its adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import signal
import subprocess
from time import monotonic, sleep
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from loopday.colab import ROOT, source_files
from loopday.learning import TrainingError, stable_split
from loopday.run_storage import write_json
from .train_dpo import MIN_TEST, MIN_TRAIN, validated_pairs


REMOTE = "/content/loopday-training"


def prepare_job(path: Path, dataset: Path) -> str:
    with ZipFile(path, "w", ZIP_DEFLATED) as package:
        for source in source_files(ROOT):
            if source.relative_to(ROOT).parts[0] in {"loopday", "server"}:
                package.write(source, source.relative_to(ROOT).as_posix())
        package.write(dataset, "world-preferences.jsonl")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap(digest: str, steps: int, seconds: int) -> str:
    return f"""from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import subprocess, sys

root = Path({REMOTE!r})
source = Path('/content/loopday-job.zip')
assert sha256(source.read_bytes()).hexdigest() == {digest!r}
root.mkdir(exist_ok=True)
marker = root / 'started'
if not marker.exists():
    with ZipFile(source) as bundle:
        bundle.extractall(root)
    with (root / 'worker.log').open('ab') as log:
        worker = subprocess.Popen([sys.executable, '-u', '-m', 'server.colab_worker', '--steps', {str(steps)!r},
                                   '--seconds', {str(seconds)!r}], cwd=root, stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    marker.write_text(str(worker.pid))
print('LOOPDAY worker started:', marker.read_text())
"""


def launch(args: argparse.Namespace) -> int:
    pairs, _ = validated_pairs(args.dataset, source="world_rollout")
    train, test = stable_split(pairs, min_holdout_groups=2)
    if len(train) < MIN_TRAIN or len(test) < MIN_TEST:
        raise TrainingError("The pilot needs enough held-out and training pairs before allocating a GPU.")
    args.out.mkdir(parents=True, exist_ok=False)
    session = f"loopday-train-{uuid4().hex[:8]}"
    bundle, starter = args.out / "job.zip", args.out / "start.py"
    digest = prepare_job(bundle, args.dataset)
    starter.write_text(bootstrap(digest, args.steps, args.minutes * 60 - 180), encoding="utf-8")
    info = {"session": session, "gpu": "L4", "steps": args.steps, "minute_limit": args.minutes,
            "train_pairs": len(train), "held_out_pairs": len(test), "bundle_sha256": digest,
            "source": "world_rollout"}
    write_json(args.out / "job.json", info)
    print(json.dumps(info), flush=True)
    deadline = monotonic() + args.minutes * 60

    def invoke(*command: str, timeout=120, checking=True):
        return subprocess.run([args.colab, *command], text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout, check=checking)

    def fetch(name: str, *, log=False, timeout=70) -> bool:
        try:
            path = args.out / name
            result = invoke("download", "-s", session, f"{REMOTE}/{name}", str(path), timeout=timeout, checking=False)
            if result.returncode and log:
                print(f"Could not retrieve {name} in this poll.", flush=True)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    attempted = False
    outcome = 1
    try:
        attempted = True
        print(invoke("new", "-s", session, "--gpu", "L4", timeout=180).stdout.strip(), flush=True)
        print(invoke("upload", "-s", session, str(bundle), "/content/loopday-job.zip").stdout.strip(), flush=True)
        for retry in range(3):
            try:
                started = invoke("exec", "-s", session, "--timeout", "35", "-f", str(starter), checking=False, timeout=70)
                if started.returncode == 0:
                    print(started.stdout.strip(), flush=True)
                    break
            except subprocess.TimeoutExpired:
                pass
            if retry == 2:
                raise RuntimeError("Colab could not acknowledge the detached worker.")
            sleep(8)

        previous = None
        while monotonic() < deadline:
            if fetch("worker.log", timeout=25):
                tail = (args.out / "worker.log").read_text(errors="replace").splitlines()[-2:]
                if tail and tail != previous:
                    print("\n".join(line[:480] for line in tail), flush=True)
                    previous = tail
            if fetch("status.json", timeout=25):
                status = json.loads((args.out / "status.json").read_text())
                if status.get("phase") == "finished":
                    if not fetch("adapter.zip", log=True, timeout=110):
                        raise RuntimeError("Training finished, and the adapter transfer failed.")
                    with ZipFile(args.out / "adapter.zip") as archive:
                        if archive.testzip() is not None:
                            raise RuntimeError("The downloaded adapter archive was corrupted.")
                    print(json.dumps(status), flush=True)
                    outcome = 0
                    break
                if status.get("failed"):
                    print(json.dumps(status), flush=True)
                    break
            sleep(24)
        else:
            print("Colab pilot reached its wall-clock limit.", flush=True)
    finally:
        if attempted:
            stopped = False
            for _ in range(3):
                try:
                    cleanup = invoke("stop", "-s", session, timeout=55, checking=False)
                    stopped = cleanup.returncode == 0
                    if stopped:
                        print(f"Released Colab session {session}.", flush=True)
                        break
                except subprocess.TimeoutExpired:
                    continue
            if not stopped:
                print(f"Automatic cleanup could not confirm the release of {session}.", flush=True)
                outcome = 2
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--colab", required=True, help="Path to the authenticated Google Colab CLI.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--minutes", type=int, default=35)
    args = parser.parse_args()
    if not 1 <= args.steps <= 100 or not 10 <= args.minutes <= 60:
        parser.error("Use 1–100 training steps and a 10–60 minute wall-clock limit.")

    def stop_requested(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop_requested)
    try:
        return launch(args)
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"Colab pilot: {error.output[-1800:]}\n")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Colab pilot: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
