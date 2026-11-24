# What did the reporter learn to do?

At a market stall, the reporter can put away two awning panels for an organizer, or return a promised raincoat to a crossing guard and put away one panel. A third course saves the reporter’s sound recording and puts away one panel. With equal starting odds, each course has a 33.3% chance. After fitting one independent agent’s judgments on other situations, the coat-and-panel course gets **61.8%**. The reporter’s next line of dialogue can follow from that choice. The acting policy receives public commitments, the organizer’s request and a deadline. Its inputs contain no names or romance instruction.

The five held-out scenes also have a complete paired replay. Using the original packet seed, the opening and trained reporters chose the **same plan in all five**. Both put away two panels in the market scene. The probabilities describe how the policy changed. The replay records what actually happened on one draw. [Five paired scenes](replay.json)

## What the screen measured

One independent agent judged 45 pairs of **authored two-turn simulations**, completing the screen on November 23, 2026 at 12:23 UTC. It chose A 23 times and B 22 times. It used neither tie nor skip. The agent received anonymous paired descriptions and a blank answer sheet. The cryptographic receipt includes timestamps and byte hashes. Human judgments have yet to be collected. [Screen shown to the rater](archive/packet.json) · [Returned judgments](archive/ratings-agent.json) · [Archive receipt](archive/receipt.json)

Each checkpoint has two available turns, an independently stated project or explicit boundary, an earlier promise to somebody else, and a possible news story. The simulator resolves the same deadlines and partner response on both branches. It records the fraction of the current project finished, whether a question resolved uncertainty, whether the reporter kept the other promise, how many times they crossed a stated boundary, and whether they got their story. Each event has a consequence in plain words. Earning the guard’s coat and returning someone’s stopwatch both count as keeping one promise. The human consequences differ, and the head cannot distinguish their severity.

The fifteen tasks cover requests, uncertainty, refusals, competing commitments and changed minds. The split was fixed before screening. Each group supplied two whole training tasks and one whole test task. Three paired judgments per task gave 30 training comparisons and 15 held-out comparisons. Every menu within a given task stays on its original side of the split. The five held-out situations share the training set’s action grammar and two-turn clock.

| Predictor on five held-out tasks | Mean log loss, nats | Brier score |
| --- | ---: | ---: |
| Equal opening odds | 0.6931 | 0.2500 |
| Fixed priority rule using realized consequences | 0.3880 | 0.1083 |
| Fitted head using realized consequences | 0.3887 | 0.1128 |
| Fitted head forecasting from public information | 0.4207 | 0.1278 |

The fitted head agreed with 13 of 15 held-out decisions. The fixed rule first favors honoring a stated boundary, then meeting the earlier promise, then progress on the current request. It gives a favored course 75% probability and equally ranked courses 50%. Across 400 resamples of the five held-out tasks with the head fixed, the central 95% interval for head loss minus fixed-rule loss was **−0.124 to +0.090** nats. This sample establishes no advantage over the simple rule. Three calibration bins contained five votes each. Mean predicted A probabilities were 0.231, 0.520 and 0.792, compared with observed A fractions of 0, 0.60 and 1.00. Five votes per bin leave considerable uncertainty. [Task breakdown, calibration bins, coefficients and predictions](results.json)

**Two choices expose the limits.** In the seed inventory scene, the head narrowly favors asking and shelving a tin over recording the disappearing price list and asking afterward. The agent preferred saving the prices. In the ceremony scene, the head gives 50.24% to recording private vows against an explicit refusal while keeping a promise to the organist. The rater preferred recording the consenting musicians and leaving the couple alone. The execution policy excludes recording the vows and asking again before it scores the remaining options. It applies the same exclusion to withdrawn permission. That guarantee comes from the authored action rules. The sigmoid estimates this rater’s relative preference for two courses of action. It measures neither a reporter’s feelings nor personal attachment.

## Fitting and using the head

The five coefficients fit a regularized Bradley–Terry model. With outcome vectors `F_A` and `F_B`, the model predicts `p(A) = sigmoid(w · (F_A − F_B))`. The loss is mean binary cross entropy plus `0.04 × ||w||² / 2`. An explicit tie contributes target 0.5. A skip drops that judgment. NumPy runs Newton’s method on CPU. The inferred coefficients in feature order were **+0.456, −0.291, +1.333, −1.235 and +0.088**. Only two training pairs changed whether uncertainty was resolved. The experiment offers little evidence for teaching the reporter when to ask. The regularized training-task bootstrap also put the project-progress and news-story coefficients on both sides of zero.

For choosing a course, the actor gets a uniform prior over the permitted menu and a softmax of expected scores at temperature 1. An unanswered request uses a fixed 50% chance of an eventual yes. A conditional plan takes the next action appropriate to the actual reply. Current public information determines what the reporter may ask or touch. On all nine uncertain pairs, flipping the hidden future answer left the decision distribution unchanged. On all 18 refusal and changed-mind pairs, a boundary-crossing alternative had zero execution probability. Swapping the names attached to speaker and prior promise-holder produced identical distributions on all 45 pairs. Identity independence is built into this general head. Distinct relationship histories and memory wipes belong to the separate social-scene experiment.

The standalone player uses the fitted weights in the simulator. It replays opening and learned policies with one shared draw per scene. Run these commands from the project root with Python 3 and NumPy installed.

```sh
python3 research/night/preferences/learn.py \
  research/night/preferences/archive/ratings-agent.json \
  --out /private/tmp/groundhog-preference-result.json
python3 research/night/preferences/play.py /private/tmp/groundhog-preference-result.json
python3 -m unittest discover -s research/night/preferences -p 'test_*.py'
```

## Which comparisons to buy next

Across 90 screened branch occurrences, 45 kept the third-party promise. Pooled binary reward entropy was 1.000 bit. Within matched pairs, switching the plan changed that outcome in 35/45 cases, giving 0.778 bits of mean within-pair entropy. A question resolved uncertainty on 15/90 branches, with 0.650 pooled bits. Only 3/45 pairs changed that outcome, giving 0.067 within-pair bits. The packet repeatedly uses courses from the same checkpoints. These counts describe the screen design. The near-even A/B vote distribution by itself says little about which events teach the policy.

We refit 400 heads by resampling whole training tasks. From 57 eligible, as-yet-unrated comparisons with distinct effects within their own training task, the acquisition routine ranks the entropy of the mean prediction minus the mean entropy of individual predictions. It returns five candidates on different tasks with different feature contrasts. The highest-ranked asks whether to post both new flood notices or record the first ferry whistle and return a promised key. Its predictive entropy is 0.856 bits, of which 0.060 bits reflect disagreement among the heads. A near 50/50 prediction can come from a trade-off that all fitted heads see the same way. Reserve selection uses only training tasks. For a new screen on inquiry, include more forks where the reporter can ask once without necessarily missing an earlier promise.

## Collect a human screen

Export to a fresh local directory and give the human rater that directory. It contains the blind packet, a blank JSON answer sheet and a standard-library terminal interface. Raters can each choose a pseudonym, work independently and quit between choices. The program saves each decision locally. Keep the analyst’s results and the earlier agent’s ratings outside the rater’s directory.

```sh
python3 research/night/preferences/rehearsal.py /private/tmp/groundhog-human-screen
cd /private/tmp/groundhog-human-screen
python3 label.py packet.json --rater reader-one --type human --out reader-one.json
```

From the project root, train a human-only head by passing the completed file to `learn.py`. Additional ratings files can be passed together. The report retains each rater’s origin, counts disagreements and reports the number of judgments. If the intended teacher is a human editorial team, keep the agent pilot as a separate comparison. Each new human sees the same test situations as the pilot. A fresh confirmatory claim about revisions made after this pilot needs a new whole-task test set.
