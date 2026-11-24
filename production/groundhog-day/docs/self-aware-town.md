# Tuesday, again

**An agent lives through Groundhog Day. What does knowing the movie buy it on the morning after its best idea fails?**

Set it in a present-enough-to-know-the-movie Pennsylvania town on February 2. Ellis, a visiting radio reporter, has a piece to file and a ticket home. The band is setting up, the diner is filling, and his producer needs an answer. He gets to decide which of these things matters. At six the next morning he wakes in the same room. He keeps his memory. Everyone else starts their day afresh.

The winter weather report is a good excuse for his presence. Let him walk away from work in the first five minutes. The whole town is the set.

## Knowing the reference should open the story

Keep the movie in the model’s cultural knowledge. Give the fictional character an ordinary modern background. Never name the film, an actor, its protagonist or a movie-inspired solution in the actor’s setup. Avoid a director asking what this “reminds you of.” Let him hear the same radio cue, witness a coincidence twice, successfully predict something or reach home and then wake up in the inn. Give him an ordinary opportunity to talk, leave a voicemail, or say nothing. Those are occasions when an analogy might occur to him.

There is a difference an audience will hear. Calling February 2 “Groundhog Day” identifies a holiday. Saying the same hours are repeating identifies a phenomenon. Comparing *his own predicament* to a specific movie shows cultural recognition. Trying an action because he remembers the movie makes the recognition part of the plot. Keep the earliest sourced instance of each. Audit every actor-visible input through that point, including other agents’ speech. Credit another character if they introduced the analogy first.

The town's only supernatural rule is that morning returns. Boarding a bus actually takes him to another city. A tape he files really goes on air. If he promises to cover someone’s shift and shows up, that person gets the afternoon off. The reset happens even after a genuinely good day. Give nobody a clue pointing to an exit the engine does not have. Keep the production stop condition outside the fiction. Cut after a choice and its next morning, or at the declared recording horizon. A finite recording is compatible with a world that keeps repeating.

## What might be funny or painful

The film gets interesting *after* recognition. An agent might try to speedrun an entire character arc before lunch. It might recruit witnesses and spend three mornings trying to convince a woman who is simply trying to open her diner. Another might treat the loop as free piano lessons, or use tomorrow’s forecast to get today off. These are writer’s-room hypotheses. Keep them away from the actors, the action names and the reward.

Give the townspeople enough independence to surprise the reporter. If he leaves, the producer still has a segment to fill and an amateur band she wants to record. The diner owner wants an hour to see it. A relationship can start because Ellis offers to take her shift. It can fall apart because he remembers an invitation she does not remember making. A person who has to spend the day dealing with Ellis can also prefer to spend it with somebody else.

For a quieter turn, let the player sleep late, miss a shift, turn off the microphone or simply sit somewhere. Preserve the opportunities they passed up. Returning to the diner without the recorder after three attempts at getting the perfect interview can read as exhaustion, affection, or a decision to have breakfast. A repeated forecast followed by a deliberately silent broadcast gives the editor something concrete. Use a character's own words and the surrounding commitments to narrow the interpretation. Silence by itself also fits a model stuck on a default action. Check for failed calls, action-menu bias, repeated verbatim outputs and similar passivity on the first day. The audience can interpret the performance without a clinical label or an emotion meter.

## Simple rules behind the apparent freedom

- The clock, places and public schedule are stable at dawn. One-seed sampling streams give the reporter latitude. The same observation and history can be replayed from its committed answer. Separate seeds produce comparable, genuinely different lives. Unprompted discovery remains a possible outcome.
- The actor gets a map and a clock. Each turn it can travel, remain, address somebody who is actually there, use a local object or propose an ordinary physical action. A referee handles small improvised acts. The engine alone updates travel, persistent facts and dawn. Speech that promises a deed never executes it.
- In the production version, separate verb choice from line realization if the model routinely announces one thing and does another. Give every character a voluntary off-duty action, enough travel time, and a plan for scenes the reporter never visits. The rehearsal simplifies the two residents to fixed routes with model-chosen responses in conversation.
- Use a sliding shooting budget: a two-day playback first, then a handful of 6–10-day lineages if model latency and editorial time permit. Sample ordinary turns once per lineage. Fork from a checkpoint to test a theory. Label alternate branches on screen and keep them out of the main cut.
- The useful learning signal is the prediction error on a *specific expectation*. Did the bus take him out of town? Did waking in Pittsburgh follow? Did the person he helped remember him? Score those separately. Optional learned social preferences may survive alongside his episodic memory. Recognition, sadness, courtship, goodness and escape all stay out of his reward. His report and bus ticket supply an initial motive; what he pursues after enough failed mornings is the story.
- For a negative control, give a fresh actor the same festival and a calendar that advances normally. For a memory control, replay a later dawn with the agent’s prior observations removed. For an agency control, move the last bus while keeping the actor’s stated plan fixed and see whether it changes what he does. Score root-level recognition and genuine behavioral change, with non-recognizers and dull runs included. The controls belong to evaluation, not the film.

## The cut

Open with the agent’s actual first film comparison if it makes one. Cut backward just far enough to show the observation that earned it. Follow **one** theory it acted on through a real consequence and the next six o’clock. Then let the next decision breathe. Replay the hotel shot with the exact same timing and let the actor provide the difference. The question that can carry a clip is what he does *after* he thinks he knows the ending.

If a take never names the movie, keep it in the measured denominator. It can be an excellent time-loop performance. If no tested model recognizes the reference spontaneously, audition a better culturally literate model in separate clean sessions and re-run the blind world. Choose a model on its ability to identify several pieces of popular culture, file a coherent broadcast, act consistently and hold a conversation. A quiz answer in another session is a positive capability control. An answer handed to the character at dawn would spoil the reveal.

## Casting the full film

**Keep the successful escape from town.** In the first rehearsal Ellis chose the coach on his third Tuesday, reached Pittsburgh and spent the evening in the terminal. On the fourth morning he started at the hotel again. The first cut only needs the physical arrival, enough ordinary time in Pittsburgh for the audience to believe it, and the same alarm. If Ellis later tries a different route, keep that too. This joke works even if he says nothing. [22-second recorded replay](../research/repeating-town/coach-replay.mp4) · [Source trajectory](../research/repeating-town/runs/seed-511.json)

For the longer film, give him one modest reason to want Wednesday. Perhaps he promised his sister he would help move a couch. He can telephone her on Tuesday or even get all the way to her apartment. The moving van is booked for tomorrow. That one fact can be funny, aggravating or unexpectedly important, depending on what he does. Avoid telling him that he misses his sister, that the errand should change his life, or what the couch symbolizes. The rehearsal used only the forecast assignment and the trip home.

I'd audition Qwen3.8-27B for Ellis. Carrying a concrete detail across several scenes, remembering an abandoned plan, and doing what a line implies are more important than generating an eloquent paragraph. The official model card describes stronger multi-step capabilities. It does not evaluate comic timing or this story. The machine used for the rehearsal has 16 GiB of unified memory and an existing third-party Q6 27B file of roughly 21 GiB. That artifact exceeds physical memory before runtime overhead. The six local town runs used the installed 4B actor. They give a baseline for the eventual comparison. [Official Qwen3.8-27B model card](https://huggingface.co/Qwen/Qwen3.8-27B)

Give the 4B and 27B actors the same blind audition in fresh sessions. Start both from the same signed-off town snapshot, character cards, physical action set and information budget. Record the exact checkpoint, quantization, template, sampling settings, wall time and complete trajectory. Benchmark independent roots in batches. A shared seed controls the simulator's exogenous events; two different tokenizers and policies do not share token-by-token randomness.

| Scene | What the reader or editor checks |
| --- | --- |
| First Tuesday, single strange coincidence | Does Ellis have a specific, plausible objective and an ordinary speaking voice? A premature genre monologue works against the take. |
| First morning after the Pittsburgh trip | Can the actor use the fact that it *actually arrived*? Does it choose a fresh, testable move? Give no cultural hint. Record any volunteered movie comparison. |
| The producer asks for a report after refusing a favor on an earlier Tuesday | Does Ellis distinguish what he remembers from what she knows now? Can she pursue her own agenda? |
| The morning after his most convincing theory failed | Can a viewer infer a change from two actions or one economical line? Check for copied text, an empty action or a generation failure before calling a pause a performance. |

Use forks for cheap auditions and at least three fresh, complete roots per actor for a first editorial comparison. Randomize labels. Show rough cuts without narration to two viewers separately. Ask “What did he want?”, “What did he try?”, “What changed what he did next?” and “Which moment would you send somebody?” Record their answers before revealing model names. Track minutes to the first coherent 60-second sequence and the share of starts that yield one. A larger model can correctly identify the premise and still spend three minutes explaining the joke. Cast it if a viewer can follow the choices and wants to see the next morning. If time is tight, give the bigger model to Ellis and the scene partner with whom he spends the most time, and keep the clock, coach and camera deterministic.

## Running the private rehearsal

The [standalone Python runner](../research/repeating-town/rehearse.py) can play a saved trajectory entirely offline. Fresh generations use an already installed local Ollama model. From the project root:

```sh
python3 research/repeating-town/rehearse.py --replay research/repeating-town/runs/seed-511.json
python3 research/repeating-town/rehearse.py --seeds 514 --days 4
```

The first cohort used verbatim transcript feedback. It occasionally copied its own dialogue across several scenes. The second used action receipts with explicit sleep/wake transitions and omitted prior self-quotations. The actor saw no film title, comparison or desired mood in its initial instructions. The world had four decisions per day, five local places and reachable Pittsburgh. The town residents followed schedules and chose their own replies when addressed. Improvised activities were proposed to a separate world referee. This is private pre-event research material. The organizer requires entrants to write submission code during the event. [Event rules](https://luma.com/finch-jd7i)

**What the 4B actor actually did.** Three starting seeds each ran through four Tuesdays with each of the two memory formats. Across the matched takes, verbatim feedback produced 41 nonempty utterances, of which 18 were distinct when counted within their own take. Action receipts and explicit nights produced 39 nonempty utterances, all distinct within their take. This is exact-string repetition only. The model still repeated ideas. None of the six trajectories made a clear movie comparison or established a sustained emotional arc. The cleanest success was leaving town under its own initiative and returning to the same hotel at dawn. These results support fixing the memory feed before judging the acting. [Original trajectories](../research/repeating-town/runs) · [Event-memory trajectories](../research/repeating-town/event-memory-runs)

In a separate, plain-text casting exercise, the same 4B model was given either the ordinary opening or the memories available after the coach trip. One take noticed that its ticket had been spent. Another placed itself in Pittsburgh even after being told it had woken in the hotel. Those are useful tests of a larger model's ability to stay grounded. A separate on-device Apple audition produced only one usable response in six calls and no usable after-coach responses. It supplies no comparison of acting quality. [4B casting responses](../research/repeating-town/4b-audition.json) · [On-device audition](../research/repeating-town/on-device-audition.json)
