# Rehearsal record · November 23, 2026

These are private pre-event research runs. They used a locally installed, quantized 4B model through Ollama, with no paid inference. The data files contain the actual role and scene prompts, chosen actions, spoken lines, sampling parameters and seed or event identifiers. The temporary harnesses were kept outside the submission project. The model alias was `nemotron-4b-64k:latest`, digest prefix `87a01f0ef133`, Ollama 0.40.16. The experiments used a 2,048-token context, temperature 0.65 and short outputs. The three characters used separate contexts on the same underlying model. A higher-quality model needs its own audition. [Ollama structured output documentation](https://docs.ollama.com/capabilities/structured-outputs)

## Could the actor use a note after the wipe?

Twelve independent seed settings, 101–112, had four road assignments balanced three times each. Only the lighthouse keeper knew which hook he would collect an oven key from. He could talk or return to work. Tomas could write up to twelve words or leave the slip blank. After the wipe he received a fresh context and saw either his actual slip or an empty drawer. Inspection was staged to test *using* a note. No facts from the original encounter went into that fresh prompt except through the slip. The baker received a fresh, independent call with the physical result of the action. The keeper collected only from the correct road. The baker owned the ferry decision whether the key was delivered or not.

Every pair shared the upstream history. The downstream sampling seed and action order were matched across arms. Arm order alternated across roots. Identical downstream requests reused a recorded answer. All twelve roots completed. Of the six keepers who spoke, two named the correct road. Tomas wrote something in every run. Only one slip named the target road. In seed 103 that slip read **“Take key to mill by noon”**. Its author kept the key in both branches. Across twelve pairs **zero** changed hook or sailing decision. The baker boarded in 11/12 in either arm. This is an honest null result from a constrained scene where he had a perfectly legal reason to keep the key. [Paired trials](../research/drawer-pilot.jsonl)

In a follow-up on the same twelve decisions, I held each role, world and seed fixed, varied the action labels and added an explicitly authored positive control. The clear slip named the exact physical operation and correct hook. It was never shown as an agent-authored line or used in the film. The numbers below count correct **committed** key placements.

| Action vocabulary | Empty drawer | Original agent slip | Clear calibration slip |
| --- | ---: | ---: | ---: |
| Road names alone, plus “keep” | 0/12 | 0/12 | 8/12 |
| Full verbs such as “hang key on mill hook” | 3/12 | 5/12 | 11/12 |

With full verbs the original note improved two pairs and worsened none. Only one of those two contained the road name. There are too few pairs to infer a robust two-case benefit from transferred factual knowledge. The clear-slip result shows why both interfaces matter. Make world-backed objects and actions legible. Preserve the writer’s freedom to leave an unhelpful note. Change order and retest on fresh seeds before attributing performance to a specific label. [Interface controls](../research/interface-controls.jsonl)

## Would an unconstrained departure leave enough Tuesdays?

Six starts, seeds 201–206, with a filmable but simplified morning. The baker initiated the day, Tomas chose an activity, the keeper independently chose whether to carry the bread, and the two passengers sealed their boarding decisions before either saw the other’s. Under the original terminal rule, **six of six boarded together on Tuesday one**. Five fishermen spent the morning mending nets. The sixth stayed at the bakery, with an empty spoken line. A critic selecting among these six would have no post-wipe scene to choose. [Original-rule traces](../research/island-pilot.jsonl)

I reran those six seeds with two stored repeats and a stopped watch that Tomas could wind or put away on subsequent evenings. I also moved slip writing to before boarding and added an audible rustle when the closed drawer contained paper. This was a bundled production redesign, so its individual changes cannot be separated statistically. All six reached the wipe by construction. Four put the watch away on the third day and advanced to Wednesday. Two kept winding through a four-day cap. Across twenty simulated days, Tomas wrote twenty slips. One fisherman searched before the wipe. **None searched afterward.** One told the keeper that the drawer had opened itself when the only witnessed fact was a rustle. The results establish that this pacing rule creates time and multiple clock outcomes. They leave recognition, sacrifice and a credible romance unobserved. [Revised-clock traces](../research/clock-pilot.jsonl)

| Rehearsal | Fresh local calls | Sum of measured request times | Scope |
| --- | ---: | ---: | --- |
| Paired drawer | 60 | 83.5 s | 72 decision slots including 12 exact response reuses |
| Original departure | 31 | 48.6 s | 6 starts × one day |
| Interface controls | 48 | 85.5 s | Four additional conditions per original root |
| Revised clock | 108 | 184.4 s | 148 decision slots over 20 days |

Timings describe the client request workload and machine at the time. They exclude asset creation, editor review, audio, speculative critic work and a production model. Cache hits have zero new request time. There were no invalid recorded decisions in the drawer or either clock cohort. Syntactic success still admitted physically false dialogue.

## Can a relationship form through actions?

I ran six fresh roots, seeds 301–306, with three distinct joint-work opportunities per partner. Opportunity order was shuffled per root. Mara and Kit separately chose whether to invite Tomas. Upon an invitation, he independently chose whether to spend a work slot. Only a mutually chosen and physically completed activity updated the relationship record. These are linked single-scene choices with an external ledger. The role actors did not carry dialogue histories between work opportunities, and the schedule supplied the tasks.

- **Island.** Alone, either partner had time to complete a job. Across 36 opportunities both chose to work alone every time. No relationships updated. [Island work decisions](../research/joint-work.jsonl)
- **Radio station.** Two people could finish before going on air. Working alone would finish after. The engineer had an audition slot to lose. Out of 36 opportunities there were three invitations, one from the recordist and two from the host. Only the host’s invitation in seed 301 produced a joint act. Two spoken acceptances accompanied actions that kept the actor’s own audition slot. The change of setting, roles, tasks and timing was bundled. This comparison cannot isolate setting as the cause. [Radio work decisions](../research/radio-work.jsonl)
- **Cost-only follow-up.** I replayed all three radio invitations with the same seed and menu. A thirty-second favor would now finish before the audition. One of the two previous declines became an acceptance, again for the host. The recordist still heard a verbal acceptance while the engineer chose his own work. These were diagnostic forks. [Paired cost changes](../research/radio-cost-forks.json)

I also passed the actual physical histories into the separately fitted synthetic action head. At a personal cost of one unit, that head’s predicted willingness to support a final request was **26.1% for the host and 14.3% for the recordist** in seed 301. All ten partner histories in the other five roots stayed at the 14.3% prior. These are computed policy probabilities on a common terminal test. The dialogue model never enacted that terminal choice, and one shared act carries little evidence about an enduring relationship. The separate **52.1%** figure in the learning brief uses a deliberately assigned richer history. [Learning objective and cost sweep](attachment-learning.md)

## Did the actors recognize the movie?

Six independent sampling seeds, 401–406, answered the same unprimed title-identification question, one question that explicitly supplied the title, and three in-character situations. All calls used fresh contexts. No film title or reminder to avoid movies appeared in the actor cards. The title-identification question produced six wrong answers. When explicitly primed, six answers proposed a rule explaining the end of the loop. In the eighteen spontaneous continuations I counted explicit movie-title or film-character references by reading the generated responses and found zero. One strongest-cue reply supplied the real Pennsylvania town. The prompts in that condition supplied the state, reporter, groundhog, date and repeated mornings. Treat these results as an audition for this model and these prompts. Naming mistakes cannot establish erased model knowledge. [Probe prompts and replies](../research/film-prior.jsonl) · [Plot treatments and proposed unlearning evaluation](plots-and-film-memory.md)

## What a full pilot still has to earn

Run the chosen setting on a stronger dialogue model with short, observable, low-cost joint acts available before giving the players expensive decisions. Include opportunities for him to invite and her to decline. Keep the same options open with the host. Show at least one single-lineage sequence of **voluntary cooperation, later changed behavior, a fact wipe and an independently chosen consequence** before claiming a character arc. If the camera crew only has evidence for a broken promise or a bond with a different person, that can be the subject of the film. None of these experiments produced a verified love story.
