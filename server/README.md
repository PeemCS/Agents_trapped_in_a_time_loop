# Phil on Colab

Run the service from the repository root on Python 3.11 or newer with an NVIDIA CUDA runtime. The default loads the text portion of Qwen3.5-9B in BF16 or FP16 and checks for 22 GiB of available GPU memory. For a smaller GPU, add `--quantize-4bit` and install `bitsandbytes`. The 4-bit server checks for 11 GiB. Take the measured latency from the authenticated canary before choosing a candidate count for a full run. [Qwen3.5 Transformers integration](https://huggingface.co/docs/transformers/model_doc/qwen3_5) · [NF4 hardware requirements](https://huggingface.co/docs/bitsandbytes/installation)

```sh
python -m pip install -U "transformers>=5.10.3,<6" accelerate
# Only for --quantize-4bit
python -m pip install -U bitsandbytes
# Only for LoRA training or serving
python -m pip install -U peft

python -m server.app --quantize-4bit
```

Supply a high-entropy `PHIL_TOKEN` through Colab secrets in the process environment. The service binds to Colab loopback. Its public readiness endpoint `/health` reports the model name. The inference endpoint `/generate` requires the token. Use an authorized HTTPS connection to reach the service from another machine. To reproduce a run, pin the full Hugging Face revision with `--revision` and retain the logged precision. The service rejects incomplete text-weight loads.

## Inference and evidence

Each request has its own prompt, answer token limits, optional thinking token limit, at most four candidates, and a soft wall-clock budget of 72 seconds. If thinking is enabled, Qwen first generates up to the reasoning cap, then completes the answer from that bounded prefix. A seed makes sampling repeatable on the same software and hardware stack. Budgeting and greedy defaults keep the first canary small.

The returned `answer` is validated against the current legal action list. A character's short stated reason is visible in the decision ledger, and world consequences carry event IDs independent of what the model said. With explicit opt-in, Qwen's emitted reasoning text can also be inspected. Treat it as a model output that can omit information and rationalize a choice. Compare memory claims against the ledger and use matched state interventions to test whether access to a clue changes behavior. [Reasoning Models Don’t Always Say What They Think](https://arxiv.org/abs/2505.05410)

## Persona calibration

```sh
# Print the GPU work plan without loading the model.
python -m server.calibrate_persona --output runs/persona-longing.json --quantize-4bit
# Run on the pinned revision and GPU used for serving.
python -m server.calibrate_persona --output runs/persona-longing.json --quantize-4bit --calibrate
python -m server.app --quantize-4bit --persona-bank runs/persona-longing.json
```

The calibration uses the difference between mean decoder activations over positive and negative trait responses. Independent scene prompts select a decoder layer. A separate set of forced-choice scenes selects the smallest signed strength that moves relative choice probability in both directions while preserving enough probability on the answer labels. The held-out scenes use different situations and both orderings of the A/B labels. Five axes are supported through `--traits longing warmth cynicism vanity despair`. The default fits one axis in 24 generations of at most 72 tokens and at most 96 additional forward passes. [Persona Vectors](https://arxiv.org/abs/2507.21509)

The bank records model revision, precision, adapter, layer selection results, and the held-out scores. A direction that fails transfer can be monitored with a zero steering coefficient. To apply a validated coefficient by default, start the server with `--default-longing` or supply an explicit request-level `steer` map. Projections pool residual outputs over the completed answer tokens in a teacher-forced pass. Their standardized units are relative to generated calibration responses. When steering is active and projections are requested, the server also measures projections for those same answer tokens with the hooks off. This isolates a residual activation comparison and holds the generated answer fixed. The authored probes measure choice preferences in these scenes.

## Outcome learning

```sh
# Read verified complete live runs and fit a small reward predictor.
python -m loopday.learning --ranker runs/live-ranker.json --preferences runs/preferences.jsonl runs/live-branch-a runs/live-branch-b
# Validate the preference dataset, exact revision, and seed split on CPU.
python -m server.train_dpo runs/preferences.jsonl --output runs/phil-lora --quantize-4bit
# Run the same plan on CUDA. The default trains for 20 optimizer steps.
python -m server.train_dpo runs/preferences.jsonl --output runs/phil-lora --quantize-4bit --train
```

The outcome ranker learns a structured action score where an executed action gives a training signal. A live deployment requires strong enough held-out prediction, support for all the candidates being compared, and live training provenance. For a local experiment, use `python -m loopday.rollout_eval runs/rollouts/rollouts.jsonl`. The evaluator measures matched legal action forks on held-out seeds and reports fixture, uniform, and oracle baselines. Use `--verified-index` to include complete checkpoints qualified by Bruin. Use `--external-check runs/rollout-eval/ranker.json` with fresh rollout seeds to retest a frozen ranker. Both paths produce local-rollout evidence.

DPO uses chosen and rejected completions from actually executed, distinct Qwen actions at the same checkpoint and observation. Each comparison carries the IDs of its outcome evidence. It requires at least 12 train and 8 test comparisons, each split containing at least two seed groups. The trainer filters to the exact base model and current prompt version, with thinking and steering disabled. It works on bounded text sequences and checks for 36 GiB available in 16-bit mode or 15 GiB with `--quantize-4bit`. [Direct Preference Optimization](https://arxiv.org/abs/2305.18290)

The trainer saves a local LoRA and evaluates completion preferences and valid action generation against base Qwen on the held-out seeds. Serving via `--adapter runs/phil-lora` requires a passing manifest, matched revision and precision, and the measured weights checksum. Re-run the authorized all-agent canary after changing the model, persona bank, or adapter.
