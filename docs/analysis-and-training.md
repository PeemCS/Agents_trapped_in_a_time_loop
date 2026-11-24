# Rollout evaluation and preference learning

## Generate and evaluate matched action rollouts

From the repository root, run the collector and evaluator with Python 3.11 or newer.

```sh
python3 -m loopday.experiments collect --seed-start 11 --seed-count 12 --trials 3
python3 -m loopday.rollout_eval runs/rollouts/rollouts.jsonl

python3 -m loopday.experiments collect --seed-start 101 --seed-count 12 --trials 3 \
  --out runs/fresh-rollouts
python3 -m loopday.rollout_eval runs/fresh-rollouts/rollouts.jsonl \
  --external-check runs/rollout-eval/ranker.json --out runs/fresh-rollout-eval
```

The collector restores each checkpoint for every legal first action and trial, using one fixed continuation and two seeded exploratory continuations in the commands above. It checks that the policy observation and checkpoint fingerprint match before the intervention. Each row stores the action, trial, prefix and suffix hashes, realized return, and evidence ID. All of these rows carry `world_rollout` provenance.

The evaluator checks every legal action against the same complete trial set. It holds out whole town seeds and reports fixture, uniform, learned-ranker, and outcome-oracle scores. The external check evaluates the saved ranker on fresh world seeds without refitting. The reports include per-seed results and a paired bootstrap interval across seeds. The oracle sees the returns used for scoring and represents an optimistic ceiling.

## Inspect the data lineage

- [Experiment verification SQL](../pipeline/assets/experiments.sql) links a prediction, the physical test, and the next observation by event ID.
- [Qualification SQL](../pipeline/assets/qualified_rollouts.sql) checks legal choices, checkpoint identity, and complete matched trials. The Python evaluator also validates the dataset directly. Use its optional `--verified-index` with an export of `evidence_id` values if an external audit has already qualified the checkpoints.
- [Preference SQL](../pipeline/assets/action_preferences.sql) pairs the best and worst observed mean returns at each qualified checkpoint when the gap is at least 0.15. [Checkpoint diagnostics](../pipeline/assets/checkpoint_diagnostics.sql) compare the baseline action to the best observed alternative.
- [Decision diagnostics](../pipeline/assets/agent_loop_diagnostics.sql) group recalled and cited evidence, rejected decisions, cache hits, and reported tokens by actor and loop.

## Reproduce the adapter data split

The [published training bundle](../showcase/phil-training/) includes source rollouts, the derived preference dataset, and the trained weights. Validate its data plan without loading the GPU model.

```sh
python3 -m server.train_dpo showcase/phil-training/world-preferences.jsonl \
  --source world_rollout --output runs/phil-reproduction --quantize-4bit
```

Use the base revision, precision, and training seed in the [training manifest](../showcase/phil-training/training_manifest.json) when reproducing the GPU run. The [model server guide](../server/README.md) covers dependencies, training, and inference. The published adapter learns preferences derived from local world rollouts. The separate [model-candidate fork runner](../loopday/live_forks.py) samples candidate actions from a model before executing each with a fixed local continuation.
