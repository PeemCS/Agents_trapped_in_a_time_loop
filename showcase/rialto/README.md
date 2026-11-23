# Play It Again

[Watch the three-minute trailer](Play-It-Again.mp4) · [Captions](Play-It-Again.srt) · [All six takes](results.json) · [Timecoded edit sources](cut.json) · [Demo deck](https://chatgpt.com/space/page_79a5cf2403b4819198a7c8bba5b9093c)

Follow the later fifty-Tuesday performance in [the dialogue log and decision traces](after-hours/README.md). The new [paper cut](after-hours/story-selects.md) follows Phil and his sister Jo.

Phil’s sister needs him in Pittsburgh on Wednesday morning. She has a van booked and a couch to move. Phil reaches the payphone three nights in a row and keeps promising to be there. Across town, Alma has worked the Rialto projectors for 42 winters. She wants her daughter in Pittsburgh to hear her voice before the cinema closes. Rita has both a recording and a way to send it. On the first night she says, “I’m going to sit in the dark for a while.”

The main story follows **take 841**. On the second Tuesday, Rita puts the transfer off again. On the third, she sends it. Phil wakes to the same radio. An envelope has arrived from Pittsburgh.

## The cut

| Time | On screen |
| --- | --- |
| 0:00–0:21 | Phil calls his sister. The next hotel alarm establishes what stands between him and his promise. |
| 0:21–1:03 | Rewind to the first Tuesday. Meet Alma, hear Larry commit his camera charge, then stay with the unsent recording after Rita takes the night off. |
| 1:03–1:30 | Second Tuesday. Return to the same payphone and the same station. Listen to what changes in the two promises. |
| 1:30–2:06 | Try a different take. In 842 Rita sends the interview on the first evening. A separately labelled earlier Rialto take pairs Rita dancing with Phil at an empty depot. The editing-room beat connects the alternatives to writing and games. |
| 2:06–2:47 | Return to the third Tuesday of 841. Larry delivers his reel, Phil calls his sister and Rita puts the interview on the wire. |
| 2:47–3:00 | The hotel clock resets. Read the daughter's reply, then hold the title. |

## What the crew actually chose

Six fresh RunPod H100 takes used Qwen 27B, the same three role cards, the same physical choices and the same prior coach-trip memory. Each take ran three days and the next dawn, for 19 actor decisions. Takes 841–844 shared an opening theory about reenacting the movie. Takes 845–846 used the ordinary reporter card. Within each condition, each role's first observation matched exactly across takes. Actor sampling varied across takes.

Phil called his sister on all 18 evenings. Rita transmitted a deliverable interview on 13. Take 841 supplied the two delays and the third-night payoff. Five of six crews sent the first interview on their first night. These are six performances of one designed situation. The camera follows Phil through the next dawn, while the move itself lies beyond the observed days.

For a closer test, we replayed the first evening of 841 with Larry’s and Phil’s actions fixed and the recorded interview already available. The original Rita took the night off. All six fresh draws of exactly her observation chose transmission and delivered the recording. Changing her action at that moment was enough to change what reached Pittsburgh. Each replay covers that one evening. [Matched replays](runpod/evening-replay.json)

The writers supplied the cast, goals, available actions, clock, and the daughter’s conditional written reply. The performances supplied the character lines and selected actions. The film uses exact excerpts from their dialogue, newly voiced for the trailer, with editorial narration and score. Its pictures restage verified events with the project’s own sets and character graphics. The signal indicators illustrate the delivery state in the log. The evening resolver records delivery when a usable recording is available and Rita transmits. It leaves open which copy played when both were available.

[Earlier Rialto take at the depot and ballroom](earlier-721.json) · [First night off](runpod/rialto-841/day-1-evening-producer.json) · [Second night off](runpod/rialto-841/day-2-evening-producer.json) · [Third-night transmission](runpod/rialto-841/day-3-evening-producer.json) · [The reply in Phil’s dawn observation](runpod/rialto-841/day-4-alarm-reporter.json) · [First-night transmission in 842](runpod/rialto-842/day-1-evening-producer.json)

Run `python3 check.py` from this directory to verify the recorded decisions, nightly outcomes, controlled replays and dialogue excerpts against the source logs. [Film specifications and checksums](release.json)
