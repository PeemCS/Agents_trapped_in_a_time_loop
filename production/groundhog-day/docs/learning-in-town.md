# What Phil can learn

Phil can learn that leaving town works, that waking in the hotel is predictable, that somebody prefers to work alone, or that he is willing to miss his own appointment for a person he has worked with. These outcomes need different evidence. The overnight rehearsal kept the actual film, the learned world model and the social-policy experiment separately inspectable.

## Learn which mornings deserve attention

A reporter observes where he ended Tuesday, where he woke up next, and the date he heard on the radio. The online forecaster begins with an ordinary expectation that the date will advance and the reporter will wake in the last evening’s location. It updates simple counts after he observes each morning. It scores each *before* updating as the negative log base two of the predicted calendar and location probabilities. That makes the first Pittsburgh-to-hotel wake unusually informative and later repetitions cheaper to predict.

Across the initial 16 large-model worlds, the predictor saw 80 actual overnight boundaries. Mean predictive loss fell from **5.85 bits per wake** with the fixed ordinary prior to **3.00 bits** with online updates evaluated before each new observation. Calendar and location are modeled independently conditional on the last location; this approximates the real state process. The environment always repeats, which makes this a favorable test for the learner. The separate ordinary-calendar fixture exercises the other direction. [Results and control sequences](../research/night/learning/forecast-grid.json)

A second casting treatment retrieves the two most surprising distinct observed overnight routes and shows only those pairs of witnessed places and dates to Phil. The actor can conclude what they mean. A renderer can use the source event IDs for a matched cut. The evening location, morning location and alarm can carry the entire joke even when Phil stays silent. [Treatment frozen before sampling](../research/night/audition/surprise-protocol.md)

## Learn what consideration looks like

Hide names and attractive dialogue while comparing consequences of two actions from the same checkpoint. The labeler sees what the person requested, what was unknown, which prior commitments existed, and what each action cost. They can choose either alternative, declare a tie or skip. A regularized Bradley–Terry head fits the probability that segment A is preferred.

```text
p(A ≻ B) = sigmoid(w · (F_A − F_B))
loss = mean[−y log p − (1 − y) log(1 − p)] + λ ||w||² / 2
```

One independent agent rated 45 paired, authored scenes. Thirty pairs from ten tasks trained the head. On 15 pairs from five unseen tasks it matched the rater 13 times and scored 0.389 log loss. A hand-written rule scored 0.388 and equal odds scored 0.693. Using only predicted, publicly available consequences at decision time scored 0.421. The trained model narrowly preferred recording a couple’s explicitly refused vows to fulfill another obligation; the execution rule removed that action. The inquiry feature had only three informative comparisons. The rater was an agent. Event-day human judgments and more examples where asking one question is valuable would change what the team can claim. [Packet, training and independent ratings](../research/night/preferences/README.md)

The difference between a probability and a scene matters. At an unseen awning job, the trained policy put 61.8% on delivering a promised raincoat first, up from 33.3%. Across the five held-out menus, the paired random draws selected the same actual actions before and after training. A distribution shift can be real while the resulting film is identical. [Actual paired draws](../research/night/preferences/replay.json)

## Give a reward that his actions can affect

At each of the **384** recorded slots in the original 27B grid, we replayed every legal reporter action through the resolver. We kept Rita, Larry and the simultaneous resolution order fixed. This produced **3,413 one-step forks**. Give each original slot equal weight and each legal act within that slot equal probability. In this controlled comparison the resolver is deterministic, so conditional mutual information equals the average binary entropy of the reward over legal reporter choices at that slot. The other actors’ realized choices are held fixed for the analysis. Phil does not see them ahead of time.

| Binary reward at the next committed tick | Observed positive slots | Slots where changing Phil’s act could change it | Conditional action signal, bits |
| --- | ---: | ---: | ---: |
| Board the intercity coach | 26 | 96 | 0.1174 |
| First confirmed sister call that day | 11 | 26 | 0.0549 |
| First band recording that day | 1 | 4 | 0.0044 |
| First filed weather reel | 5 | 4 | 0.0050 |
| Larry spends his camera battery | 89 | 0 | 0.0000 |

Larry’s battery has **0.781 bits of marginal reward entropy** under the recorded actors. Every possible reporter action in every visited slot had the same immediate battery outcome. Rewarding Phil for Larry spending it would generate a varied-looking score while attributing someone else’s choice to him. A band reward that Phil can influence in only four visited slots gives very little immediate feedback. More varied job opportunities and a separately owned contribution/acceptance are more direct fixes. Longer-horizon effects require new rollouts with residents responding to changed observations. [Counterfactual results and generator](../research/night/learning/large-grid-channels.json)

For event-day labeling, separate reward entropy from policy entropy. Low policy entropy is appropriate after a clearly declined offer. Train the head on difficult choices rather than paying for repeated ratings of easy refusals. Bootstrap the fitted heads and prioritize cases where they individually disagree about which action is preferable. Save a block of entire tasks before active selection so the evaluation remains independent. [Preference-learning precedent](https://arxiv.org/abs/1706.03741)

## Let a relationship have a cost

The portable-recorder side experiment gives Rita and Larry independent ways to invite Phil, work alone or shelve their own take. Phil can keep his appointment. Only mutually chosen, distinct projects become trials. The placement of the one faulty recorder is matched across partners; a declined invitation leaves the person’s record unchanged. Display names never enter the value function. Wiping the diary, retaining the hidden partner record, swapping partner records and replaying a request at several costs make the proposed effect inspectable. [Frozen social experiment](../research/night/learning/social-protocol.md)

The final choice policy values progress on a currently requested project, with a bounded extra value from that partner’s learned record. The bounded value is zero after a refusal. Its coefficient and prior are authored choices with an earlier synthetic calibration. A change in costly assistance is observable. Romance is one possible audience reading of voluntary concern, and the recipient is free to want something quite different. Whether any character has an experience it cannot verbalize lies outside these measurements.

## The objectives behind the numbers

For a paired preference, let Δφ be the difference between the features of two simulated outcomes for the same starting situation. The feature vector carries the partner’s stated request, progress on that request, other promises, cost and boundary crossings. The label is 1 for the first outcome, 0 for the second and ½ for a tie. The fitted head uses

$$
p_i=\sigma(w^\mathsf{T}\Delta\phi_i),\qquad
L(w)=-\frac{1}{n}\sum_i[y_i\log p_i+(1-y_i)\log(1-p_i)]+\frac{\lambda}{2}\lVert w\rVert_2^2 .
$$

The side experiment with genuine collaborative encounters keeps a separate small state for a *person’s identity*. Given $s$ successful recorded collaborations out of $n$ voluntarily joined attempts, it uses $z=\max(0,2(2+s)/(4+n)-1)$, a clipped transform of the mean of a Beta(2,2) posterior. Both people have to participate before there is a collaboration to update. Swapping the person record or keeping it after diary erasure tests exactly what that mechanism contributes. Prior history projects the probability of joining a costly future take from 20.4% to 30.5% in the first Rita history. Retaining her display name with an erased record leaves the projected policy at 20.4%. The reference implementation deliberately keeps refusal handling independent of this state. [Actual encounters and state-swap projections](../research/night/learning/social-qwen3.8-27b/results.json)

For a deterministic world transition, start with the same state and hold the other actors’ decisions fixed. Give each legal reporter action equal probability. For a binary reward, its conditional entropy over those actions equals the conditional mutual information $I(A_{Phil}; R\mid s,a_{Rita},a_{Larry})$, because a known joint action fixes the outcome. Average over the recorded world states. The measured information was 0.0000 bits for spending Larry’s camera battery, 0.1174 for catching the coach, and 0.0549 for reaching the sister. A potential action’s entropy is useful only alongside its payoffs and which character can alter them. An actor can also rationally repeat a good choice, so action variety belongs in editorial auditioning as a separate criterion. [Executed interventions](../research/night/learning/large-grid-channels.json)

The language-model adapters use another objective, teacher-forced token cross-entropy on the demonstration with frozen base weights and low-rank trainable adapters. A matched opportunity is necessary to evaluate whether a learned change reaches a physical decision. At a new departure, Rita and Mara traded places as the person who had previously waited with Phil. Across the four actor treatments, all 13 executable assignments gave Phil his own seat. The three invalid draws are reported in the full denominator of 16. [Costly-seat transfer](../research/night/persona/scarce-seat/findings.md)
