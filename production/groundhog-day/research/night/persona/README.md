# Phil’s attachment to Rita

The initial experiment fits one low-rank adapter to a frozen Qwen3-1.7B, then places the base, an explicitly cued base and the adapter into the same fictional scenes. The adapter condition uses an ordinary actor card throughout evaluation.

Start with [the findings and transfer checks](findings.md), [the offline four-actor monitor](viewer.html#greenhouse-0-0), or [the unedited branching film](story-takes.md). The repaired adapter loads from `results/v2/adapter`.

Read [the intervention and held-out comparisons](protocol.md). [The training record](results/training.json) identifies the frozen checkpoint, weight checksum, optimizer, peak allocator use and duration. [The teaching records](results/teaching.jsonl) contain every demonstration. [The optimizer log](results/losses.jsonl) records every update.

## Reuse the saved actor

Install [the pinned packages](requirements.txt) into a private environment with PyTorch 2.8.0. The code below loads the saved adapter in a Python process on a CUDA machine. It expects this folder as its working directory. To run the original checkpoints from a previously downloaded snapshot, replace the first argument to the base loader and tokenizer with its local path.

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "Qwen/Qwen3-1.7B"
revision = "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
base = AutoModelForCausalLM.from_pretrained(
    model_id, revision=revision, torch_dtype=torch.bfloat16
).to("cuda")
actor = PeftModel.from_pretrained(base, "results/adapter").eval()
```

Reproduction uses a fresh directory with the Python files, the pinned requirements and the exact checkpoint downloaded into `base/`. The scripts preserve an existing training run. In that fresh directory, run the following commands.

```sh
python -B run.py train
python -B run.py eval
python -B score.py
python -B shoot.py
python -B analyze.py
```

The three main generation files each store one JSON object per call, including the exact messages, final dialogue, raw generated token IDs, text between thinking delimiters, declared token budget and finish status. The three branching shot files additionally retain the action the simulator executed and its consequence. Model-generated reasoning is an observable output for this local model.

## Reproduce the repair and transfer checks

From that same fresh remote working directory, after the original training and generation commands above, run the following. Use the same frozen base snapshot for both adapters.

```sh
python -B recovery/recover.py rescue
python -B recovery/recover.py train-v2
python -B recovery/recover.py native-v2
python -B shoot.py --v2
python -B recovery/fresh.py
python -B scarce-seat/seat.py
python -B recovery/analyze_recovery.py
python -B scarce-seat/analyze_seats.py
python -B render_takes.py
python -B build_viewer.py
```

To obtain the original base on the training machine, the pinned Hub package can fetch the exact revision into the expected folder. The two portable adapters are the only weights retained in this project.

```python
from huggingface_hub import snapshot_download

snapshot_download(
    "Qwen/Qwen3-1.7B",
    revision="70d244cc86ccca08cf5af4e1e306ecf908b1ad5e",
    allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja"],
    local_dir="base",
)
```

[Recovery protocol](recovery/protocol.md) · [Scarce-seat protocol](scarce-seat/protocol.md) · [Browser verification](viewer-check.json)
