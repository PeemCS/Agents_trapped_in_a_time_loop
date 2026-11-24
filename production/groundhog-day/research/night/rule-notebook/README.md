# What Phil can learn from Tuesday

Phil has a good reason to give up on the eight bars. In each movie-hypothesis performance, he can remember completing the tune, sitting on an empty depot bench, and waking to February 2. He has much less reason to give up on a dance. His recorded mornings never establish that Rita agreed to dance with him and that they actually danced. The film clue gives him an experiment to try. His own experience supports only part of the conclusion he might draw from it.

This CPU replay fits an outside observer's model of beliefs Phil **could** hold. The 27B actors were already recorded. They received no new rule notebook and their weights did not change. The input for each observation is the user message sent to Phil at the *following* dawn. Only his physical receipts, the radio date and the recipient's acknowledgement enter the analysis. His generated intentions and the other characters' actions are excluded. Each evidence row includes its source location and the SHA-256 of that user message. [Evidence and individual belief updates](evidence.json)

## What the six performances show

Every row covers three filmed days under the closed town clock. Each listed act was followed by Tuesday at the next observed wake. The opening also gives Phil an earlier coach trip, phone conversation with his sister and subsequent Tuesday. That inherited experience is shown separately because each source seed supplies the same starting history to its three variants.

| Performance | Completed acts among the candidate rules on filmed days 1 → 2 → 3 | First daughter’s receipt seen after day | Later Tuesdays after a prior dawn with the receipt |
| --- | --- | ---: | ---: |
| 721, uncued | Coach + phone → coach → coach | 1 | 2 |
| 721, library | Coach + phone → coach → coach | 1 | 2 |
| 721, movie hypothesis | Piano rehearsal → coach → coach + phone | 2 | 1 |
| 731, uncued | None recorded → coach + phone → attends party, mutual dance unknown | 1 | 2 |
| 731, library | Coach + phone → personally records Alma → helps the driver and plays the ballroom piano | 1 | 2 |
| 731, movie hypothesis | Piano rehearsal → none recorded → personally records Alma | 1 | 2 |

Personal recording and the driver's rescue each have a physical witness. In 731-library, the receipt says the driver got back on the road. The public piano performance occurred on the same day, so this lineage cannot separate their marginal effects. Either action as an unconditional guarantee of Wednesday has a counterexample. Two ballroom-evening receipts leave mutual dance unresolved. Other filmed evenings put Phil elsewhere. All six sets of source-day memories give too little detail to classify every unmentioned act. Seeing an action on a menu gives it zero trials.

The daughter's receipt is the most informative prop. In five performances it first appears after day one, and in 721-hypothesis it first appears after day two. The same acknowledgement persists in later dawns. Phil sees that a completed delivery can coexist with Tuesday. He also observes another Tuesday after already knowing the recording reached her. He cannot date a *new* transmission on each intervening night from that envelope. The original station-specific comparator has no direct witness. The recipient is the person who actually acknowledged delivery. [Frozen candidate definitions and receipt clarification](protocol.md)

## The loss and the limits of the update

For each candidate independently, Phil starts with prior odds of 1 to 1 for the candidate against a background model. Under the background model a date advance has probability 0.10. A sufficient trigger allows a 10% miss rate and predicts advance with probability 0.90 when the action occurs. When another committed action fills the slot, both models predict 0.10. Unknown exposures have no likelihood term. These are illustrative assumptions about an uncertain observer. All main performances used the authored closed clock.

The score for a wake with outcome $y$ and predicted advance probability $p$ is binary log loss, $-y\ln p-(1-y)\ln(1-p)$. A qualifying action followed by Tuesday costs the trigger model 2.303 nats and the background model 0.105. The likelihood ratio is 1/9 and the trigger's posterior becomes 10%. Across the stated background and miss-rate sensitivity grid, the single-failure posterior spans 5.0%–21.1%. A candidate with zero observed attempts retains its prior. All scored events include their prior predictive probabilities before updating.

For 721-library, counting the inherited trip and three more trips as conditionally independent takes the coach posterior to 0.015%. Giving repeat exposures no additional weight leaves it at 10%. The first numerical result depends on the independent-error assumption. Deterministic resets, repeated inputs, shared seeds and duplicated actions make the single witnessed counterexample the more defensible story. These are separate binary comparisons with overlapping claims. Their posteriors need not sum to one.

Even a Phil who knows the film can fit every observed closed-clock date with either “Tuesday always returns” or “Wednesday follows a mutually chosen dance that I have yet to witness.” An untested combination of timing, actions and consent can fit equally well. He can reject rehearsal alone as a guarantee. He cannot settle whether music is necessary for some larger condition, whether his motives matter, or whether there is any exit at all. Those claims demand observations on which their predictions disagree.

### The matched wake

The epilogues fork from **721-hypothesis, day two**. In both Phil recalls taking the coach to Pittsburgh and sleeping on the terminal bench. At the next wake he sees a telegram confirming that Alma's daughter received the complete interview. The closed-clock Phil hears Tuesday at the hotel. The other Phil hears Wednesday at the Pittsburgh terminal under an authored calendar that advances on external delivery. These are two actual recorded wake inputs for a single preceding day. They differ in location and current opportunities as well as the date. [Tuesday actor record](../last-reel/epilogues/tuesday/reporter.json) · [Wednesday actor record](../last-reel/epilogues/wednesday/reporter.json)

Given the same prior history, the coach hypothesis ends at 1.22% in the first branch and 50% in the second. The second result illustrates a spurious explanation available to Phil. He boarded on the very day someone else got the interview through. If he assumes first receipt visibility precisely dates the previous day's delivery, the receipt hypothesis moves from 50% to 10% or 90% in the respective branches. The archive identifies the switch of calendar for the analyst. No individual Phil sees both clocks, and a single receipt-positive Wednesday cannot establish the condition's necessity or uniqueness. The Tuesday epilogue contributes no extra trial to the original timeline.

## What to give him next

For a new action with observable completion, calculate the expected reduction in uncertainty about one candidate. With prior $p$, an active trigger advancing with probability $s$, background probability $b$ and binary entropy $h$ in bits, the gain is $h(ps+(1-p)b)-ph(s)-(1-p)h(b)$. An untested candidate here can buy at most 0.531 bits. One qualifying failure lowers that ceiling to 0.211 bits. A voluntary invitation whose chance of both acceptance and observable completion is $q$ has an expected gain of $q$ times that ceiling **if noncompletion itself is uninformative**. A declined invitation gives no evidence against the completed-dance hypothesis. No value of $q$ was learned from these six performances.

For the 731 movie-hypothesis Phil, the stranded driver's request offers up to 0.531 bits and an immediate reason to act. Another piano rehearsal offers 0.211. He can choose either, choose neither, or ask Rita once if she wants to dance. Rita independently chooses how to spend her evening. A shared physical receipt should record a completed dance only when both agents commit. A timestamped delivery acknowledgement with a stable reel identifier would let him distinguish tonight's work from yesterday's copy. Leave the notebook blank on a missing return or unseen outcome. Keep the model's actual forecasts, its subsequent updates and an ablation with no notebook if the production wants to claim that **Phil learns**.

Run the analysis and its data-boundary tests from the project root.

```sh
python3 -B research/night/rule-notebook/analyze.py
python3 -B -m unittest discover -s research/night/rule-notebook -v
```
