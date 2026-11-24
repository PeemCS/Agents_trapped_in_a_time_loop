"""Build a secret-free source bundle and a Colab notebook for LOOPDAY."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .run_storage import write_json


ROOT = Path(__file__).resolve().parents[1]
QWEN_REVISION = "cc5442c03a5c0bff0bd4c6888d9a40029c637733"
SOURCE_NAME = "loopday-colab-source.zip"


def source_files(root: Path):
    extension_by_directory = {"loopday": {".py", ".c"}, "server": {".py", ".txt"},
                              "web": {".html", ".js", ".css"}}
    for folder, extensions in extension_by_directory.items():
        for path in sorted((root / folder).iterdir()):
            if (path.is_file() and not path.is_symlink() and not path.name.startswith(".")
                    and path.suffix in extensions):
                yield path


def make_zip(root: Path, destination: Path) -> str:
    with ZipFile(destination, "w") as output:
        for path in source_files(root):
            entry = ZipInfo(path.relative_to(root).as_posix())
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, path.read_bytes())
    return sha256(destination.read_bytes()).hexdigest()


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.strip().splitlines(keepends=True)}


def code(source: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": source.strip().splitlines(keepends=True)}


def notebook(bundle_digest: str) -> dict:
    cells = [
        md("""
# LOOPDAY on Colab

Run Phil’s Qwen3.5-9B in the notebook’s CUDA runtime and Muse Spark Contributor 1.3 for Rita, Ned, and Larry. The town, checkpoints, and memory run in the same notebook process as Phil. Add `MODEL_API_KEY` in Colab’s Secrets panel and grant this notebook access before running the model check.

Use a GPU runtime. Full weights need at least 22 GiB of free VRAM. The NF4 option needs at least 11 GiB. Upload the matching source ZIP when prompted. The setup and model sections are separate so you can decide when to begin using compute.
"""),
        code(f"""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import os
import sys
import zipfile

from google.colab import files

PROJECT = Path('/content/loopday')
BUNDLE = '{SOURCE_NAME}'
EXPECTED_SHA256 = '{bundle_digest}'
QWEN_REVISION = '{QWEN_REVISION}'

bundle = Path('/content') / BUNDLE
if not bundle.exists():
    uploaded = files.upload()
    if set(uploaded) != {{BUNDLE}}:
        raise ValueError('Upload the matching LOOPDAY source ZIP.')
    bundle.write_bytes(uploaded.pop(BUNDLE))
if sha256(bundle.read_bytes()).hexdigest() != EXPECTED_SHA256:
    raise ValueError('The notebook and ZIP must come from the same export.')
PROJECT.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(bundle) as archive:
    for name in archive.namelist():
        parts = PurePosixPath(name).parts
        if len(parts) != 2 or parts[0] not in ('loopday', 'server', 'web') or parts[1].startswith('.'):
            raise ValueError('Unexpected source path in the LOOPDAY bundle.')
    archive.extractall(PROJECT)
os.chdir(PROJECT)
print('LOOPDAY source verified.')
"""),
        code("""
import subprocess

INSTALL_DEPS = False
if INSTALL_DEPS:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'server/requirements-colab.txt'], check=True)
else:
    print('Set INSTALL_DEPS to True once for a new GPU runtime.')
"""),
        code("""
import torch

if not torch.cuda.is_available():
    raise RuntimeError('Select a CUDA GPU runtime first.')
free, total = torch.cuda.mem_get_info()
QUANTIZE = free < 22 * 1024**3
if free < 11 * 1024**3:
    raise RuntimeError('Choose a runtime with at least 11 GiB free GPU memory.')
print({'gpu': torch.cuda.get_device_name(), 'free_gib': round(free / 1024**3, 2), 'use_nf4': QUANTIZE})
"""),
        code("""
PROBE_QWEN = False
if PROBE_QWEN:
    flags = ['--quantize-4bit'] if QUANTIZE else []
    subprocess.run([sys.executable, '-m', 'loopday.preflight', 'phil-gpu', '--revision', QWEN_REVISION,
                    *flags], check=True)
else:
    print('Enable PROBE_QWEN for one GPU-only action before connecting Muse.')
"""),
        code("""
from google.colab import userdata

RUN_CANARY = False
CAPTURE_PHIL_REASONING = False
BAND_CONFIG = None  # Optional path to an uploaded BAND room configuration JSON.
PHIL_ADAPTER = None  # Optional path to a validated LoRA directory.
PHIL_PERSONA_BANK = None  # Optional path to a matching persona bank.
PHIL_STEER = None  # Optional path to a JSON object mapping traits to strengths.
env = os.environ.copy()
runtime = ['--live', '--phil-in-process', '--phil-revision', QWEN_REVISION, '--alias-names']
if QUANTIZE:
    runtime.append('--phil-4bit')
if CAPTURE_PHIL_REASONING:
    runtime.extend(['--phil-thinking', '--phil-capture-trace'])
if PHIL_ADAPTER:
    runtime.extend(['--phil-adapter', PHIL_ADAPTER])
if PHIL_PERSONA_BANK:
    runtime.extend(['--phil-persona-bank', PHIL_PERSONA_BANK, '--phil-monitor'])
if PHIL_STEER:
    runtime.extend(['--phil-steer', PHIL_STEER])

def run_story(extra):
    import json

    run_env = {**env, 'MODEL_API_KEY': userdata.get('MODEL_API_KEY')}
    band = []
    if BAND_CONFIG:
        config = json.loads(Path(BAND_CONFIG).read_text())
        for actor in config['actors']:
            key = f'BAND_{actor.upper()}_API_KEY'
            run_env[key] = userdata.get(key)
        band = ['--band-config', BAND_CONFIG]
    subprocess.run([sys.executable, '-m', 'loopday.run', *runtime, *band, *extra], env=run_env, check=True)

if RUN_CANARY:
    run_story(['--loops', '1', '--ticks', '5', '--max-calls', '24', '--no-persistent-cache', '--out', 'runs/live-canary'])
else:
    print('Set RUN_CANARY to True for the bounded all-agent check. A first run downloads the Qwen weights.')
"""),
        code("""
RUN_FULL = False
RESUME = False
MAX_CALLS = 124
WORLD_SEED = 7
PHIL_SEED = 7

if RUN_FULL:
    output = 'runs/live-story'
    options = ['--loops', '2', '--ticks', '36', '--max-calls', str(MAX_CALLS),
               '--out', output, '--seed', str(WORLD_SEED), '--phil-seed', str(PHIL_SEED)]
    if RESUME:
        options.append('--resume')
    run_story(options)
else:
    print('Enable RUN_FULL after reviewing the canary and choosing a total call limit.')
"""),
        code("""
EXPORT = False
RUN = PROJECT / 'runs/live-story'

if EXPORT:
    replay = PROJECT / 'loopday-replay.zip'
    with zipfile.ZipFile(replay, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ('run.json', 'events.jsonl', 'film.json', 'memory.json', 'checkpoint.json', '.calls.json'):
            path = RUN / name
            if path.is_file():
                archive.write(path, 'live-story/' + name)
    files.download(str(replay))
else:
    print('Enable EXPORT to download the selected run for local rendering and evaluation.')
"""),
    ]
    for index, cell in enumerate(cells):
        cell["id"] = f"loopday-{index + 1}"
    return {"nbformat": 4, "nbformat_minor": 5, "metadata": {
        "colab": {"provenance": []}, "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"}, "accelerator": "GPU",
    }, "cells": cells}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("runs/colab"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    digest = make_zip(ROOT, args.out / SOURCE_NAME)
    write_json(args.out / "loopday-colab.ipynb", notebook(digest))
    print(f"{args.out / 'loopday-colab.ipynb'}\n{args.out / SOURCE_NAME}\nSHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
