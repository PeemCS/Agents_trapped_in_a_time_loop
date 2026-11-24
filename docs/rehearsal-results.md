# LOOPDAY results and limitations

LOOPDAY evaluates memory use and decision-making in a 36-tick town. The results below separate rule-based local policies, models evaluated on simulator-derived preferences, and full model-driven trajectories.

## Local-policy experiments

| Experiment | Result |
| --- | --- |
| Matched memory ablation | Removing the verified pencil result from policy input changed the next route at the shared dawn checkpoint. Five tested local-policy seeds showed the same switch with exploration disabled. |
| Shifted lesson | Four policies attended each of nine shifted lesson times after learning the schedule from a notice. When a rescue conflicted with the last departure for the lesson, all four helped the child. |
| Ending variation | Forty policy draws at world seed 7 produced 24 community-recognition endings and 16 endings where Rita stayed. Policy seeds 0 and 7 reproduce those endings. |
| Rollout qualification | The SQL audit qualified 4,344 rollouts across 216 checkpoints and produced 173 matched-action preference pairs and four verified experiment records. An injected illegal action caused qualification to fail. |
| First-action ranker | On the initial 27 held-out checkpoints, both ranker and fixture averaged 1.671. On 108 checkpoints from 12 fresh seeds, the frozen ranker averaged 1.250 and the fixture averaged 1.187. |
| Stress and recovery | The audit passed 160 world and policy combinations. Sixteen mid-episode resumes matched uninterrupted ledgers. Seven sampled schedules without the rescue conflict reached piano practice in all 140 runs. The conflicting schedule reached it in 2 of 20. |

The [local policy notes](local-agent-policies.md) describe the authored decision rules and the per-seed schedule tests. The [analysis protocol](analysis-and-training.md) explains the continuation policies, return metric, and seed split.

## Model evidence

- **Preference learning.** A LoRA adapter trained for 20 steps on 127 simulator-derived preference pairs. It ranked 45 of 46 held-out pairs correctly, compared with 20 for the base model. The held-out pairs came from six town seeds. These labels reflect the simulator's reward and continuation policy. The [training manifest](../showcase/phil-training/training_manifest.json) records the exact base revision, split, precision, and checksums.
- **20-loop continuation.** The live cast reached the configured cap on February 2. Phil waited when a late-night invitation was available. A separate reconstruction supplied an authored invitation and sampled Rita's response. She declined. [Run and fork](../showcase/live-run/)
- **Rialto performances.** In a separate town scenario, Phil called his sister on all 18 sampled evenings and Rita transmitted the interview on 13. In six resamples of one evening, with the other actors' choices fixed, Rita transmitted in all six. She had taken the night off in the original. [Takes, source traces, and replay](../showcase/rialto/)

## Scope of the evidence

The matched memory test isolates the effect of an available clue at one choice point. Later choices may compound that change. Ending frequencies describe the sampled configuration and its authored goal and relationship rules. The first-action ranker is evaluated with specified local continuations, and preference accuracy measures the ordering of held-out action completions. End-to-end improvement from the adapter would require matched runs with and without it.

The ledger records stated reasons alongside independent world evidence. Optional model-emitted traces and activation probes are measurements with separate provenance. The [experiment protocol](loopday-setup-and-experiments.md) describes how to vary model-facing aliases and world facts when testing for familiarity with the scenario.
