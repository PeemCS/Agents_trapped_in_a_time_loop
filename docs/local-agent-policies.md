# Local agents

The local controller runs Phil, Rita, Larry, and Ned without provider calls. Each character scores the legal actions supplied by the town using their own observations, goals, and schedule. The decision ledger records the score for each option, the reasons for that score, the exploration adjustment, and any cited evidence.

| Character | What affects their choices |
| --- | --- |
| Phil | His reporting assignment, the forecast on the road, remembered experiences, available lessons, and immediate chances to help. |
| Rita | The station's reporting schedule, firsthand observations, and whether she wants to stay after the party. |
| Larry | Opportunities to film an event he actually witnessed, plus the crew and party schedule. |
| Ned | The chance to show a sample insurance policy, meet people, and recognize what neighbors have done. |

Exploration is a bounded, reproducible adjustment to action scores. It is keyed to the policy seed, actor, clock, location, exchange, and visible scene. Exact score ties use action ID order. The policy can therefore resume from a saved world checkpoint with the same seed.

Phil learns at three levels. His memory can retain evidence from a physical experiment and retrieve it during a later decision. Practice grants piano skill in the town and can unlock a performance at the party. The world also records outcomes for actions Phil attempted in similar contexts. The next day's policy can use those estimates to adjust scores, with smaller adjustments when the estimate comes from only a few attempts.

## Reproduce both endings

```sh
python3 -m loopday.run --local --seed 7 --policy-seed 0 --loops 2 --out runs/local-community
python3 -m loopday.run --local --seed 7 --policy-seed 7 --loops 2 --out runs/local-rita
```

Both commands begin with the same town. Policy seed 0 reached February 3 through recognition from the crew. Policy seed 7 reached February 3 after Rita chose to stay. A check across 40 policy seeds with the same world seed produced 24 community endings and 16 Rita endings. The seeds affect choices throughout each run, so the observed outcome frequencies describe this policy and town configuration.

In the memory test, Phil first predicts what will happen to a pencil he breaks. The next morning he observes its state. The test restores that checkpoint twice and withholds the verified result from one policy input. The underlying state and available actions are the same. Across policy seeds 0 through 4, Phil followed the dry route with the result and stepped into the puddle when it was withheld.

## Planning around a new timetable

Phil learns the lesson window when he passes the Main Street notice or the teacher’s door. He can recall that same notice the next morning. The ledger links a route choice to the actual notice he saw and estimates the first lesson turn reachable if he leaves now or waits. A separate skill event records attendance.

With policy seeds 0, 2, 7, and 13, Phil attended all four times at each tested opening tick 6, 8, 10, 12, 18, 20, 22, 28, and 34. At tick 11, he projected that he could attend at tick 12 if he left immediately. All four runs prioritized helping the child on Main Street at that last departure turn and missed the lesson. In an exact-checkpoint control with exploration disabled, withholding a recalled camera scene kept the route and timing estimate the same.

The role priorities and dialogue phrases are authored. The world enforces travel, opportunity deadlines, skill requirements, and Rita's ability to decide. These runs exercise observation-driven choices and persistent learning in the simulation. The local controller uses neither a language model nor fine-tuning.
