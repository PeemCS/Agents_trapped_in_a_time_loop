# LOOPDAY experiment protocol

Run commands from the repository root with Python 3.11 or newer. The fixture is a deterministic reference policy for world and renderer checks. Local mode uses independent rule-based actors. Live mode replaces the decision makers with language models while the simulator still controls time, legal actions, observations, and consequences.

## Reproduce two local-policy trajectories

```sh
python3 -m loopday.run --local --loops 2 --seed 7 --policy-seed 0 --out runs/local-community
python3 -m loopday.run --local --loops 2 --seed 7 --policy-seed 7 --out runs/local-rita
python3 -m loopday.audit runs/local-community/run.json runs/local-rita/run.json
```

The world seed fixes town conditions. The policy seed changes reproducible exploration in the actors' scoring. Both runs save a ledger, checkpoint, memory file, and film edit. [Local policy rules and schedule tests](local-agent-policies.md)

## Isolate the effect of memory

```sh
python3 -m loopday.experiments memory --seed 7 --out runs/memory-forks
```

Phil predicts an outcome, breaks a pencil, and inspects its state at the next dawn. The runner forks that dawn before his next choice. The three arms start from the same physical state and pre-intervention event prefix.

| Arm | Policy input at the fork |
| --- | --- |
| `intact` | Full memory |
| `hide_result` | Verified pencil result withheld |
| `hide_puddle` | Remembered puddle encounter withheld |

Compare the first action and evidence IDs in `summary.json`. Inspect the recorded prediction, action, and measured result before interpreting any downstream ending. The [analysis guide](analysis-and-training.md) applies a different intervention by forcing each legal first action and measuring its return.

The simulator stores Phil's memory as observations, beliefs, and skills linked to world events. Other actors receive current-day observations and conversations. Use `--lesson-tick` to change the lesson schedule and `--pencil-stays-broken` to change a physical reset rule in a separate cohort. `--alias-names` changes the names seen by the models while preserving canonical names in the replay. Compare evidence use and expressed familiarity across conditions with matched seeds.

## Run a bounded model canary

Live mode uses Qwen3.5-9B for Phil and Muse Spark 1.3 Contributor for the supporting cast. Set `MODEL_API_KEY` for the supporting cast's chat-completions endpoint. See the [provider configuration](../loopday/providers.py) for the endpoint and model identifier. For separate GPU serving, configure `PHIL_URL` and `PHIL_TOKEN` as described in the [model server guide](../server/README.md). Keep credentials in the process environment or the ignored `.env`.

```sh
python3 -m loopday.preflight status
python3 -m loopday.preflight muse
python3 -m loopday.run --muse-canary --loops 1 --ticks 5 --max-calls 12 --out runs/muse-canary
python3 -m loopday.preflight phil
python3 -m loopday.run --live --loops 1 --ticks 5 --max-calls 24 \
  --no-persistent-cache --out runs/live-canary
```

The optional `python3 -m loopday.colab` exporter produces a GPU notebook and matching source archive for in-process inference. Run the bounded canary before enabling the longer notebook run. For a laptop-led run, retain the successful four-actor canary and supply its path with `--verified-canary` if it differs from `runs/live-canary/run.json`.

For comparisons, record the base revision, precision, adapter, and steering settings. Keep `--seed` fixed and vary `--phil-seed` to sample Phil under the same town conditions. Each completed tick saves a checkpoint. Use `--resume` with the same settings and output directory to continue a partial run. The call cap includes failed attempts and persists across resumes.

## Related research

- Generative Agents studies memory, reflection, and planning in a simulated town. [Paper](https://arxiv.org/abs/2304.03442)
- DiscoveryWorld evaluates hypothesis formation and testing in an interactive environment. [Paper](https://arxiv.org/abs/2406.06769)
- Persona Vectors studies activation directions for behavioral traits. [Paper](https://arxiv.org/abs/2507.21509)
- Work on reasoning faithfulness motivates comparing emitted explanations with observed evidence and controlled interventions. [Paper](https://arxiv.org/abs/2505.05410)
