"""Run the bounded LOOPDAY GPU probe and adapter pilot inside a Colab VM."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from time import monotonic
from zipfile import ZIP_STORED, ZipFile

from loopday.colab import QWEN_REVISION
from loopday.run_storage import write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--seconds", type=int, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    deadline = monotonic() + args.seconds
    phase = "gpu_setup"

    def run(command: list[str], limit: float | None = None) -> None:
        remaining = max(1, deadline - monotonic())
        subprocess.run(command, cwd=root, check=True, timeout=min(remaining, limit) if limit else remaining)

    def progress(**fields):
        write_json(root / "status.json", {"phase": phase, **fields})

    try:
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("This Colab job requires a CUDA GPU.")
        free_gib = torch.cuda.mem_get_info()[0] / 2**30
        hardware = {"gpu": torch.cuda.get_device_name(), "free_gib": round(free_gib, 2)}
        print(json.dumps(hardware), flush=True)
        if free_gib < 15:
            raise RuntimeError("This NF4 trainer needs at least 15 GiB free VRAM.")
        env = root / "runtime"
        run([sys.executable, "-m", "venv", "--without-pip", "--system-site-packages", str(env)], 40)
        python = str(env / "bin" / "python")
        run([sys.executable, "-m", "pip", "--python", python, "install", "--disable-pip-version-check",
             "--quiet", "-r", "server/requirements-colab.txt"], 210)

        phase = "qwen_probe"
        progress(**hardware)
        run([python, "-u", "-m", "loopday.preflight", "phil-gpu", "--revision", QWEN_REVISION,
             "--quantize-4bit", "--backend-only"], 850)
        phase = "training"
        progress(backend_ready=True, **hardware)
        run([python, "-u", "-m", "server.train_dpo", "world-preferences.jsonl", "--source", "world_rollout",
             "--output", "adapter", "--max-steps", str(args.steps), "--quantize-4bit", "--train"])

        manifest = json.loads((root / "adapter/training_manifest.json").read_text())
        with ZipFile(root / "adapter.zip", "w", ZIP_STORED) as package:
            for name in ("adapter_config.json", "adapter_model.safetensors", "training_manifest.json"):
                package.write(root / "adapter" / name, name)
        phase = "finished"
        progress(backend_ready=True, evaluation=manifest["evaluation"], **hardware)
        return 0
    except (OSError, ValueError, RuntimeError, ImportError, subprocess.SubprocessError) as error:
        print(f"{phase} failed: {error}", flush=True)
        progress(failed=True, error=f"{type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
