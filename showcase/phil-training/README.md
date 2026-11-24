# Phil’s Qwen3.5-9B adapter

This directory contains the trained LoRA adapter, the 173 simulator-derived preference pairs, the source world rollouts, and the independent longing-vector calibration. The adapter was trained in NF4 precision for 20 steps on 127 pairs. Six unseen town seeds provided 46 held-out pairs. Base Qwen ranked 20 correctly, and the adapter ranked 45 correctly. See [training_manifest.json](training_manifest.json) for the model revision and checksums.

The [base model](https://huggingface.co/Qwen/Qwen3.5-9B) is downloaded separately. See [Qwen’s Apache 2.0 license](https://huggingface.co/Qwen/Qwen3.5-9B/blob/cc5442c03a5c0bff0bd4c6888d9a40029c637733/LICENSE) and the [server instructions](../../server/README.md) for runtime requirements.

From the repo root, validate the data split without loading the GPU model.

```bash
python3 -m server.train_dpo showcase/phil-training/world-preferences.jsonl \
  --source world_rollout --output runs/phil-reproduction --quantize-4bit
```

Add `--train` to run the actual CUDA training. To load the published adapter in the existing server with an exact base revision:

```bash
python3 -m server.app --revision cc5442c03a5c0bff0bd4c6888d9a40029c637733 \
  --quantize-4bit --adapter showcase/phil-training
```

The optional `longing-vector.json` belongs to this adapter and can be provided with `--persona-bank`. The live story ran with steering off.
