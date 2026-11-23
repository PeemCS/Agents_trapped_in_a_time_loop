# LOOPDAY rehearsal results

Four characters act in a 36-tick town. Morning anchors specify the clock, a greeting, and the ceremony. The road and opportunity rules constrain movement throughout the day. The renderer selects and animates recorded events. The ledger links each edited shot to its source, and the checkpoint witness can show new committed events during a run.

## What to show

1. Play the 16-second portrait cut to establish the loop. Both cuts use original geometry, score, effects, and dialogue.
2. Open `runs/showcase/compare-memory.html`, select **Compare loops**, and play both at 06:30. An experiment log records Phil’s prediction, the broken pencil, and the next morning’s inspection. Both branches begin the comparison at the same world checkpoint.
3. Open the 06:30 action in each branch. With the test result available, Phil avoids the puddle. With that one result withheld, Phil steps into it. The intact local policy run reaches February 3 through community recognition. The other branch is still on February 2 at the end of its horizon.
4. Open `runs/showcase/compare-endings.html` for the same town with different policy draws. Follow each ending to a choice made by one of the characters. The February 3 epilogues are the simulator’s consequences of those choices.

## Measured results

| Check | Result |
| --- | --- |
| Same town, different local policy draws | Across 40 draws, 24 endings through community recognition and 16 where Rita chose to stay. Policy seeds 0 and 7 reproduce those endings with world seed 7. |
| Paired memory test | Hiding the verified pencil result changes the next route at the same checkpoint. Across five tested policy seeds, this remains true with exploration disabled. |
| Shifted lesson | Four policies attend each of nine shifted lesson times after seeing a town notice. When the lesson conflicts with a child rescue, all four infer the departure deadline and choose to help. |
| Bruin pipeline | Eight assets and all seven checks passed against the final data. Bruin qualified 4,344 rollouts across 216 checkpoints and materialized 173 matched-action preference pairs and four verified experiment records. |
| Local outcome ranker | On the first 27 held-out checkpoints, it tied the fixture at a mean expected return of 1.671. On 108 checkpoints from 12 entirely new seeds, the frozen ranker scored 1.250 versus 1.187 for the fixture. The effect measures a first action under specified local continuations. |
| Stress and recovery | The audit passed 160 world and policy combinations. Sixteen mid-episode resumes matched uninterrupted ledgers. The seven sampled schedules without the rescue conflict reached piano practice in all 140 runs. The conflicting schedule reached it in 2 of 20. |

A separate Bruin run injected an action outside the legal list. The qualification check rejected the row and blocked preference materialization. The `runs/showcase/bruin-summary.json` and `bruin-lineage.json` files contain the validated counts and dependency chain.

The local policy scores actions with authored goals and can adjust them using retained evidence and observed rewards. The policy ranker fits those observed rollout outcomes. The training dataset labels those outcomes `world_rollout`. A separate bounded runner can sample real Qwen candidates at a single checkpoint and execute them with fixed local continuation policies. Its data path was tested with a stand-in backend. Qwen CUDA, activated persona calibration and DPO weight updates still need live execution.

## Archive choices and research

- **World and memory.** The archive supplied the four-character setup, timed town, repeated openings, semantic replay, Phil-only persistent memory, relationship gates, model diagnostics, and training idea. The implementation uses auditable text and world-state comparisons. It preserves evidence IDs through memory retrieval and gossip. The two dawn branches follow exact checkpoint matching so a comparison can isolate the missing clue. [Generative Agents](https://arxiv.org/abs/2304.03442), [DiscoveryWorld](https://arxiv.org/abs/2406.06769), [WorldTest](https://proceedings.mlr.press/v306/warrier26a.html)
- **Models.** The archive selected Qwen3.5-9B for Phil and an earlier Muse contributor model via a gateway. This version uses the requested Muse Spark Contributor 1.3 directly. The Colab bundle can run Qwen and the simulator together. The model-facing alias condition and phrase audit test for expressed familiarity with the film when live generations are available. [Qwen model card](https://huggingface.co/Qwen/Qwen3.5-9B), [Meta Model API](https://dev.meta.ai/docs/quickstart)
- **Interpretation.** The ledger keeps action, stated reason, observed events and optional Qwen measurements visible. The activation monitor compares a calibrated direction against held-out behavior. The system labels model-emitted trace text as one model output. [Persona Vectors](https://arxiv.org/abs/2507.21509), [Reasoning Models Don't Always Say What They Think](https://www.anthropic.com/research/reasoning-models-dont-say-think)
- **Sponsors.** Bruin imports the world evidence and qualifies the offline training rows. BAND has a tested adapter for addressed dialogue, recipient inbox read-back, and a receipt the recipient sees. A sponsor room and agent keys are needed for the live handoff. The presentation plan is ready to assemble in AdaL. [Sponsor instructions](sponsor-setup.md)

The event’s build rule governs the submission. These artifacts document the pre-event rehearsal. [Event rules](https://luma.com/stxaoop0)
