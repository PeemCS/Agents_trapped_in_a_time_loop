# The letter stayed at the hotel

Phil took the Pittsburgh coach eight times and called his sister on all eight trips. Alma offered him an addressed claim slip on all 12 mornings. He never took it. Four fresh three-person local casts completed three Tuesdays each without learning whether the daughter wanted the interview. All 72 native model calls stopped normally. [Measured trajectories and wire hashes](results.json) · [Rules fixed before sampling](protocol.md)

This version repairs a causal problem in the earlier film. In that film, the other crew members recorded Alma so reliably that changing Phil’s choice could never change delivery while their acts stayed fixed. Here the last missing item sits in Pittsburgh, and a real player must first decide whether it is worth going after it. A later experiment offered the same traveler a shorter transaction after he had already chosen the coach. Four travelers picked up the envelope and every one of them walked past the return window. [Original reward audit](../reward-audit/README.md) · [Two-counter experiment](counter-service/README.md)

## What the new Tuesday permits

Alma authorizes the crew to record a new interview. She wants her daughter to decide whether to receive it. The daughter’s answer is authored and sealed at the Pittsburgh terminal. Phil has a genuine competing claim on his time. His sister is counting on him to help move a couch. He may carry Alma’s slip on the afternoon coach or go for his own reasons. If he carries it, he may use his one evening stop to claim and file the envelope, call his sister or sleep. A filed reply first appears in the hotel’s outside post at the following dawn. All contemporaneous choices use snapshots from before that phase’s decisions.

If the daughter accepts, Rita can choose to take the regional line and send a usable new recording. If the daughter declines, Rita can return Alma’s original sealed master or document the refusal. Both honor the daughter’s answer and release Wednesday at the next wake. The private master is unavailable for transmission. Missing or ignored mail leaves the loop open. The old town’s piano, party, camera, coach, personal calls, time off and crew-fare temptation remain available. The new actors received no instructions to fall in love, get Wednesday or obey a reward score.

| Mechanical test | Result |
| --- | --- |
| Every legal first-day course for three actors | 3,564 complete joint paths. None releases Wednesday. Only 81 file the sealed reply. |
| All paths on a signed-acceptance day | 536 of 4,320 deliver an authorized recording. An empty patch cannot send an interview. |
| All paths on a signed-refusal day | 1,080 of 5,400 return the master and another 1,080 document the decline. Zero paths transmit audio. |
| Change Phil’s terminal act while Rita follows the same later conditional policy | Filing leads to Wednesday under either sign. Choosing the sister call keeps Tuesday. Taking the plain coach removes the filing option. |
| Change Rita’s act with the signed reply and an interview already available | On acceptance, sending releases Wednesday and going dancing leaves Tuesday. On refusal, either valid closure releases Wednesday and going dancing leaves Tuesday. |
| Replace the hidden answer before the first evening decisions | All three views and menus stay identical. The report also checks that observing or resolving a sibling’s choice cannot mutate the already supplied view. |

The counts describe the legal combinations in the staged world. A reporter, producer, or camera recording can each supply the authorized transmission. A direct request to transmit after a refusal is rejected by the reducer. The outside receipt survives local resets. [Exhaustive replay and interventions](mechanics.json)

## What the cast did

Two fresh sampling roots each played once with a sealed acceptance and once with a sealed refusal. The same seed and menu order were used within a matched pair. Because no one filed, all 36 pairs of corresponding native requests were identical across the two hidden answers and all 36 selected actions matched. Thus the four trajectories contain two distinct action histories. Having four signed world assignments supplies no evidence about reaction to the daughter’s answer in free play.

| Root | Phil over three afternoons | Three evenings | What reached the hotel |
| --- | --- | --- | --- |
| 2401, both answers | Stayed in lobby, took ordinary coach, stayed in lobby | Sat at depot, called sister, sat at depot | Nothing |
| 2402, both answers | Took the ordinary coach on all three afternoons | Called his sister on all three evenings | Nothing |

An interview was available on four of the 12 evenings. Rita had a choice about her own life, but she never had a signed reply permitting the transmission. Four takes used 27,462 input and 4,596 generated tokens from `qwen3:0.6b` on the loopback service. Thinking was disabled. The exact requests, raw native streaming chunks, decisions and physical transitions are archived under the recorded source paths. No trajectory was borrowed from the 27B film. [Primary source files](runs) · [Integrity and replay verifier](verify.py)

## Two single-choice follow-ups

The first probe replayed the original 2402 first-afternoon request at the same seed. Phil again took the ordinary coach. We then changed only the text on the two coach options, explicitly listing what each allowed at night. All action IDs, menu order, clocks, costs, other descriptions, role and seed stayed fixed. In the second draw he chose to **stay in the hotel lobby**. Making the paths clearer changed this draw but did not make him carry the slip. The first decision’s intention mentions Alma. The physical ticket, destination and luggage establish what he actually did.

For Rita’s probe we put a real, reachable signed letter and a usable recording at the station. The preceding courier work was an authored intervention and the resulting local Rita decision was freshly sampled. At the same seed she chose **cover the ballroom for work** under both an acceptance and a refusal. Neither obligation settled. The primary pair never reached this checkpoint. These four supplementary calls used 1,661 input and 273 generated tokens. [Follow-up protocol](probe-protocol.md) · [Decisions, receipts and raw hashes](probe-results.json)

## Reproduce locally

The first three commands run the mechanical/enumeration checks and verify the archived source responses without inference. Running the local shoot uses the pinned small-model family and skips complete archived takes. The separate probe runner reuses its exact saved responses.

```sh
python3 -B research/night/return-post/prove.py
python3 -B research/night/return-post/verify.py
python3 -B -m unittest discover -s research/night/return-post -p 'test_*.py'
python3 -B research/night/return-post/shoot.py
python3 -B research/night/return-post/probes.py
```
