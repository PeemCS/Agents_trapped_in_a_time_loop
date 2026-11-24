# LOOPDAY

**A time-loop testbed for memory, decision-making, and coordination in multi-agent simulations.**

Four agents share a town that resets every morning. Only Phil retains evidence across days. The other agents have their own goals and act on what they witness. LOOPDAY asks which experiences change a later choice, whether a policy can exploit a changed timetable, and how much an individual action matters when other agents act independently.

The simulator gives each actor a legal action set based on location, time, and available objects. Committed actions, witnesses, and consequences enter an event ledger. The same ledger supports checkpoint interventions, policy evaluation, and an inspectable 3D replay.

## Selected findings

| Experiment | Observed result |
| --- | --- |
| **Memory ablation** | Starting from the same dawn, withholding the verified pencil-reset result changed Phil's route from dry pavement to the puddle across five tested local-policy seeds. |
| **Schedule adaptation** | Four local policies attended the piano lesson in each of nine changed time windows. All four prioritized a child rescue when it conflicted with the last viable departure. |
| **First-action ranking** | A learned ranker tied the fixture policy on the initial held-out split. On 108 checkpoints from 12 fresh town seeds, mean return was **1.250 vs. 1.187** under the tested local continuations. |
| **Preference learning** | A LoRA adapter ranked **45 of 46** held-out simulator-derived preferences correctly, compared with **20 of 46** for the base model. The split held out entire town seeds. |
| **Long-horizon model run** | A model-driven cast ran for 20 loops and reached the configured cap on February 2. In a separately reconstructed exchange, Rita declined a human-authored invitation at a point where Phil had chosen to wait in the original run. |

The memory and scheduling results characterize the authored local policies. The ranker estimates the value of the first action under specified continuations. Held-out preference accuracy measures agreement with simulator-derived labels. The live run records one trajectory. [Results and limitations](docs/rehearsal-results.md)

## Reproduce the memory intervention

Run from the repository root with Python 3.11 or newer. The fixture, audit, and browser export run locally without model weights or API credentials.

```sh
python3 -m loopday.experiments memory --seed 7 --out runs/memory-forks
python3 -m loopday.audit runs/memory-forks/intact.json runs/memory-forks/hide_result.json
python3 -m loopday.viewer \
  --run runs/memory-forks/intact.json --compare-run runs/memory-forks/hide_result.json \
  --label 'Evidence intact' --compare-label 'Reset result withheld' \
  --compare-tick 1 --export-html runs/memory-forks/compare.html
```

Read `runs/memory-forks/summary.json` for the shared checkpoint fingerprint, the evidence IDs, and the first action in each of three arms. Open `runs/memory-forks/compare.html` to compare the two main arms. The third arm withholds the remembered puddle encounter and also changes the fixture's route. [Experiment protocol](docs/loopday-setup-and-experiments.md)

## How it works

- **World and observations.** The simulator resolves travel, appointments, physical tests, and interactions. The decision record preserves the actor's allowed actions, observations, and evidence citations. [Simulation](loopday/simulation.py) · [Town rules](loopday/town.py)
- **Selective memory and matched interventions.** Phil retrieves prior experience by relevance, strength, recency, mood, and location. The experiment runner restores a checkpoint and varies one memory input or first action. [Memory](loopday/memory.py) · [Experiment runner](loopday/experiments.py)
- **Evaluation and training.** The rollout evaluator requires complete, matched legal-action trials. It splits by town seed and compares the ranker against fixture, uniform, and oracle baselines. Logged returns also supply preference pairs for fine-tuning. [Analysis and training](docs/analysis-and-training.md) · [Dataset and adapter](showcase/phil-training/)
- **Replay and provenance.** A shot opens its source event. Synchronized playback lets readers compare choices at the same world time. The ledger distinguishes committed actions and observed consequences from an actor's stated reason. [Replay guide](docs/film-replay.md)

## Explore the artifacts

| Artifact | What to inspect |
| --- | --- |
| [Memory comparison](showcase/compare-memory.html) | Download and open this standalone replay for the paired dawn and its decision ledger. |
| [Ending comparison](showcase/compare-endings.html) | Compare two local-policy draws in the same town. |
| [20-loop run and invitation fork](showcase/live-run/) | Inspect the archived decisions, the reconstructed exchange, and an independent SQL check of memory retrieval. |
| [Rialto study](showcase/rialto/) | Explore six model-driven performances, a matched evening replay, and a film sourced from the recorded choices. |

For the simulation test suite, run `python3 -m unittest discover -s tests -v`. For model runs and seed controls, see the [experiment protocol](docs/loopday-setup-and-experiments.md) and [model server setup](server/README.md).
