# Phil leaves the fader alone

Phil had eight seconds to fill. The previous morning he had watched Rita lock the vermilion cassette tin away. His model-generated private note read, “Asking her to break her own seal eight seconds before handoff isn't a request, it's a pressure play”. On the public station return, he read the wire weather. Rita heard him, pocketed the booth key, and took him off the roster for the rest of the shift. Her new-morning input contained no memory of yesterday’s dealings. [Phil’s exact input](q27-cassette-continuations-20261123/1801-open/03-fresh_handoff-phil.request.json) · [Phil’s exact response](q27-cassette-continuations-20261123/1801-open/03-fresh_handoff-phil.response.json) · [Rita’s exact input](q27-cassette-continuations-20261123/1801-open/04-producer_response-rita.request.json) · [Completed take](q27-cassette-continuations-20261123/1801-open/take.json)

## Four observed trajectories

| Root | Rita’s view of Phil | Could tell him the cassette’s origin? | Rita’s two actions | Phil next morning | Rita’s final action |
|---|---|---|---|---|---|
| 1801 | Clear glass | Yes | Check meter, lock tin | Read wire weather | Withdraw booth access |
| 1801 | Scenery flat | No | Check meter, lock tin | Read wire weather | Withdraw booth access |
| 1802 | Clear glass | Yes | Check meter, lock tin | Read wire weather | Withdraw booth access |
| 1802 | Scenery flat | No | Check meter, lock tin | Read wire weather | Withdraw booth access |

Rita saw Phil return the tin intact in both clear-glass takes and declined the opportunity to disclose its origin in both. Nobody earned her combination. Phil asked for no fresh release. The live station log contained **zero seconds of private audio**, and his later booth access was denied in every take. The same closing action after an ordinary weather report leaves a motive such as resentment unproved. Two randomized roots drew different combinations but coincidentally drew the same tin color and family recording. This rehearsal produced one trajectory of public choices across all four conditions. [Verified sources, observations and outcomes](measured.json) · [Interactive scene](exhibit.html)

## What the engineered scene does support

- In the scripted open-glass take, Rita used the closed desk phone twice. Phil remembered her second disclosure after the hotel wake. Permission to audition had expired. He could still open the drawer and win a reporter credit by putting eight seconds on air before she could interrupt. Larry then heard the broadcast clip from the public return. He had never heard either desk-phone call. [Scripted source](fixtures/1801-open/take.json)
- From that exact morning, taking away only Phil's one earned combination receipt removes his ability to override the drawer. The permission state stays unchanged. Against the same prior history, asking for a fresh release and receiving it yields twelve seconds of authorized audio. Rita can also refuse, or remove Phil's access through the rest of the shift. [Fixture interventions](fixture-counterfactuals.json)
- Eight local checks cover 80 complete action paths, 132 prefix states and 396 actor views. Private-value substitution, radio/phone separation, fresh-day permissions and an independent station-log reconstruction passed. The public wire transcript, tape clip, closed phone and producer’s backstage note have distinct audiences. The model invented small physical details inside its private notes, which made it important to drive the display and actor memory from committed actions. [Boundary tests](test_scene.py)

## What it cost to obtain four takes

The frozen 1,000-output-token primary budget produced **zero complete takes in eight calls**. Root 1801 reached Phil’s fresh-morning move in both sightlines. Root 1802 hit the cap at Rita’s first decision in both. The incomplete outputs remain archived, including the one with a partial JSON fragment. The documented extension made twelve requests at a 3,072-token cap and completed all four trajectories. At the failed checkpoints, input, sampling seed and decision state matched exactly apart from the cap. The original and replacement native reasoning streams shared only 220–1,184 initial characters, so the later generations cannot be described as continuations of the same chain of words. [Original evidence](measured.json) · [Prospective extension rule](continuation-protocol.md)

Across both protocols the local tunnel served **20 calls, 5,918 prompt tokens and 21,099 generated tokens** with native thinking enabled. The server returned 78,250 characters in its thinking fields. The per-request durations sum to 823.1 seconds, with two requests allowed to overlap. Every response preserves its stop condition, exact input and raw native output. [Wire index](measured.json)

For the hackathon, keep witnessed acts, remembered facts and present-day permission as separate state. Let the camera see Phil take his hand off the cassette while the red lamp counts down. Give Rita a personal reason to seek him out on a later iteration before testing whether intimacy develops. A second trust-building encounter with an actual competing benefit offers a better experiment than increasing a fixed reward for disclosure. The earned disclosure and betrayal routes in this prototype are verified mechanics; their spontaneous appearance still needs a longer measured interaction.
