# Agent Groundhog Day · Director’s and engineer’s brief

The [current creative brief](self-aware-town.md) supersedes the island and clock ending below. The schedule, replay controls and operating estimates still apply to the free-roaming town.

The island is the tested reference design for the engine below. For the film I would now use [the 8:12 broadcast](plots-and-film-memory.md). The baker’s last delivery becomes the recordist’s live cross-town cue, the fisherman’s ticket becomes the engineer’s audition slot, and the watch becomes the recorder’s rewind control. The finite resource, autonomy, reset and production budget carry across. In the studio, the recordist’s release controls her tape and the host controls the station’s rundown. The engineer can offer his own time and operate only an authorized channel.

The shot worth building the island for is the baker asking the same question twice and the fisherman doing something different the second time. If he gives up his own passage to finish a delivery she *asked* him to make, the audience can read the cost in an unused ticket. If he takes the ticket and leaves, the camera can respect that ending too. Both are examples of what the engine should let happen. Neither belongs in a character prompt.

**Greenlight the repeated Tuesday, the handwritten notes and three autonomous characters. Put the thirty-day run and the grief graph off the critical path.** Six free-start rehearsals on a local 4B model ended with both passengers boarding the first ferry. Twelve separate memory trials produced twelve notes and zero changes in physical action when the notes were removed. Once the action names described physical acts, two additional deliveries succeeded with agent-written notes. These are results from a small rehearsal on one model. They are the reason to change the design before buying GPU hours. [Rehearsal and underlying traces](rehearsal.md)

## Give the baker a life on the other side

Mara letters nautical charts on waste flour sacks. Her sister has offered her paid work on the mainland. Mara also owns an oven that three island households rely on. Let her recruit the keeper, refuse a stranger’s knowledge about her, arrange cover herself, change her mind and catch the boat alone. Her morning should still work if the fisherman spends it mending his nets. Give her at least one scene with the keeper while Tomas is somewhere else. Keep that exchange out of his observations.

Kit has a good reason to disappoint both of them. A fouled lighthouse wick and the bread round both need the same hour. Carrying the loaves frees up Mara's evening and leaves the wick for somebody else. Show the tray in a character’s hands, the lamp going dark or a passenger folding a ticket. These are legible on mute. Each expensive decision should move an object, change a schedule or cost somebody an opportunity.

For Tomas, start with a broken boat, a paid ticket and a disposition toward mending things. Remove “then her” from his goal. The baker can become important through shared work. The keeper can become important instead. A run where Tomas learns to stop offering unwelcome help can be a better short than a string of declarations of love. In the original farewell, take care with who owns the verb. The ending ledger can establish that **she boarded and he stayed**. Establishing that he sacrificed his passage for her takes a recorded opportunity, cost and choice.

## Separate the ferry from the clock

The original terminal condition lets her first rational departure erase the entire premise. A hypothetical independent 20% departure probability per Tuesday leaves only 3.5% of lineages alive after fifteen Tuesdays. Even six independent starts would give only about a 19% chance of one survivor. The local rehearsal was harsher still. Waiting for a good drawer is an expensive production dependency.

**My proposed change to the fiction** is that Mara controls her passage and Tomas carries the mechanism that can repeat the day. A brass watch starts with two turns in its spring. Each of the first two midnights consumes a turn and returns the island to dawn. On the second, Tomas also loses his diary and episodic recollection. On the next evening he can wind the stopped watch or put it away. Winding buys one further Tuesday. Putting it away lets Wednesday come for everyone, whoever boarded. He has the watch on either side of the gangplank. End the shoot at four to six Tuesdays and record an unresolved cap as its own outcome.

| State | Ordinary Tuesday reset | Second toll | True Wednesday |
| --- | --- | --- | --- |
| Island, ferry, villagers’ episodic memories | Restore the same morning | Restore the same morning | Advance normally |
| His recollection and pocket diary | Carry observed facts forward | Clear both, including summaries and retrieval indexes | Carry current experiences forward |
| Loose slips in his desk | Retain each authored slip | Retain slips and their original event IDs | Retain |
| Spring reserve | Spend one stored turn | Spend the second turn | Stop repeating |
| His learned disposition, if enabled | Carry the learned state | Retain only the declared procedural component | Carry it forward |

The two guaranteed repetitions are authored world mechanics. His interpretation of them, any note he writes, her career choice and the eventual winding decision are open. Make the handoff physically possible by letting him slip paper into the desk **before** the ferry. A sticking drawer is a visible reason to examine it. Searching remains his choice. At the reveal, match cut from his actual writing hand to the recovered slip with the same event ID. If only the viewer identifies the hand, that is the reveal. Attribute recognition to Tomas only if he expresses it.

Give the watch readable feedback. For example, let him see its two notches diminish and hear it tick through the return to morning. Before calling a winding decision an *informed* sacrifice, require an earlier observation or a prediction he made that the ending confirms. Habitually winding a watch also makes a valid, different ending. For a cut that must retain the original ferry-exit rule, start at the inn **after yesterday’s last ferry**, let a real agent decide what to leave behind, and wipe at dawn. This preserves note ancestry and her power to end the loop on day one. It yields less time to build a relationship.

## Make the film auditable in a few seconds

1. **One world reducer owns facts.** A tick freezes public physical state and builds each actor’s view from co-presence, private observations and allowed memory. Each actor chooses among legal verbs with actor-specific arguments. Resolve the two boarding decisions simultaneously, then advance the boat once. Resolve scarce items atomically. Speech cannot fix a boat, deliver bread, move another character or cancel their ticket. Only committed verbs change those facts.
2. **Use a decision record that explains a visible choice.** Capture scene ID, actor, visible evidence IDs, legal choices, chosen act, a short stated intention, object changes and who witnessed them. Intentions can be inaccurate. For the audience, show the receipt for the warm loaf or the unused ticket beside the quoted line. The replay needs no access to private model reasoning.
3. **Keep three distinct kinds of history.** Diegetic memory goes back to the actors. The append-only event ledger goes to the renderer and judges. Evaluation questions and alternate branches go to a separate experiment store. Canonical notes are immutable agent text with writer and event provenance. A transferred paper tag can carry a grounded fact, with its printed and handwritten portions marked separately. Give actors the option to file it, ignore it or disagree. Count guesses and failed handoffs too.
4. **Branch at a genuine decision.** Save the world, actor memories, model revision, action-policy revision, RNG streams and ledger head. Compare the same next decision with the original slip present and with its ink masked. For a stronger control, use a matched irrelevant slip. Keep action order, sampling uniforms and available alternatives fixed. Label the branch as an experiment. It never becomes the missing middle of the film. A fork identifies what changed *in that situation*. More start states are needed to generalize.
5. **Make replay cheaper than inference.** The authoritative recording is the committed action and its exact text. Index an edit by lineage and event range. A verifier rejects missing ancestors, changed dialogue, reversed chronology within the main narrative or an uncommitted take. The film uses one lineage. A separately captioned comparison may show alternatives. Content hashes detect accidental edits when checked against a manifest saved before editing. They cannot certify what a producer did before that manifest existed.

For reset NPCs, cache a canonical serialization of the **entire actor-visible request**, legal action set and order, template, model revision, decoding settings, actor policy revision and actor-visible procedural state. Include a world-specific sampling salt for independent starts. A hidden loop number in the greeting key breaks the refrain. Omitting a recently observed conversation leaks old answers. Store separate full-response and prefix caches. A serving engine’s prefix reuse saves prefill work, while exact response reuse can skip generation. vLLM documents qualifications on reproducibility across configurations and hardware. [vLLM reproducibility](https://docs.vllm.ai/en/stable/usage/reproducibility/) · [Prefix caching](https://docs.vllm.ai/en/stable/features/automatic_prefix_caching/)

A failed request gets one bounded repair for schema or length. After that, commit a visible missed turn with an infrastructure flag. A retry uses the same decision slot. Commit the event, next state and checkpoint cursor together under a unique lineage/tick/actor/slot key, so a crash cannot make two boats leave. Delayed voice, a critic and the Bruin projection can all catch up from the log. Keep a local rendered take available while running fresh inference.

## How to spend the compute

Start with three active characters, a desk, an oven and a quay in one camera-traversable set. Give each day a morning exchange, one piece of work, two sealed ferry choices and an evening decision. A finicky five-location island can consume the afternoon before anyone sees the baker walk.

| Planning assumption | Lean shoot | Original-scale illustration |
| --- | ---: | ---: |
| Independent starts × days × model decisions/day | 8 × 4 × 6 | 6 × 30 × 16 |
| Decision slots | 192 | 2,880 |
| Uncached input at an assumed 700 tokens per slot | 134,400 | 2,016,000 |
| Generated output at an assumed 60 tokens per slot | 11,520 | 172,800 |
| At an illustrative 3 s per decision, serial, before overhead | 9.6 min | 144 min |

These are assumptions for planning, excluding scoring, repairs, TTS and extra trials. The key rehearsal used much shorter outputs and took **83.5 seconds for 60 uncached calls**. That timing says little about a 30B model or eight simultaneous worlds. On the event machine, time twenty representative requests at concurrency one and four independent worlds, including load, queueing, JSON validation, input length, output length and p95 latency. Simulated scenes within one world still depend on their predecessors. Wall time has both a longest-dependent-lineage floor and a total-work/aggregate-throughput floor. A world that arrives late cannot be edited sooner because another world generated faster. [vLLM serving benchmarks](https://docs.vllm.ai/en/stable/benchmarking/cli/)

For a concrete GPU budget, a 30B dense BF16 weight array alone is about 60 GB decimal. A second resident copy for activation hooks would put the weights alone at roughly 120 GB before KV cache, activations or serving overhead. Start with one inference server. Measure the memory high-water mark at the actual context and concurrency. Queue any hook pass after the shoot or run it on another machine. Pick a provider on measured usable decisions per dollar. Multiply its quoted hourly rate by billed startup, idle and generation hours, and add any separate voice or token fees. A smaller model with convincing ordinary dialogue and reliable physical choices is eligible to win the audition.

**Audition by yield.** Run the same short scenes on candidates and blind the reader to model names. Count legal physical actions, lines consistent with committed events, repeated facts wrongly presented as new, independently intelligible sacrifices, time to a reviewable minute and useful seconds per minute of inference. In the rehearsal one fisherman announced that his boat was fixed while the ledger still had it broken. A schema alone cannot protect the script supervisor from that.

## The six-hour production decision

The organizer lists hacking from 11:30–1 and 2–6, or **5½ scheduled hacking hours**, with a public repo and demo due before 6 PM Pacific. The listing requires Bruin, directs entrants to create their demo video with AdaL, and requires event-written code. The visual brief calls for a 1–3 minute agent film and a visible decision log. Check Teamily for changes on arrival. The research traces in this project are pre-event experiments. Build submission code during the event. [Organizer rules and schedule](https://luma.com/finch-jd7i) · [Visual brief](https://crewbasecollective.com/aim-hack-visual)

| Pacific time | Deliverable and person responsible | Decision if behind |
| --- | --- | --- |
| 11:30–12:15 | Engine owner commits one complete Tuesday. Writer owns three independent cards and the physical conflict. Visual owner animates a walk and handoff. Data/editor owner connects Bruin to a local DuckDB event asset and checks AdaL export. | Use one set and subtitles. Keep all three actors’ decisions visible. |
| 12:15–1:00 | Capture a 60-second animatic from one real lineage. Bruin projects events into a decision ledger and checks duplicate slots, note ancestry and missing receipts. Export one test video through AdaL. | If the model fails the clear-note control, change the action interface or model. If the service stalls, use the tested local backend. |
| 2:00–3:00 | Shoot short independent lineages and review complete trajectories. Learning owner, shared with data, fits the small behavior head only if paired choices are available. | If no lineage carries a relationship, broaden the film to a promise, a friendship or a failure to recognize someone. Preserve all attempted lineages in the denominator. |
| 3:00–4:00 | Lock one lineage, record an unbroken replay, run its drawer or learned-state counterfactual, check the edit against event IDs. | A coherent 75–120 second film already meets the length requirement. Stop generating when editing becomes the bottleneck. |
| 4:00–5:00 | AdaL assembly, captions, two voice tracks if ready, levels and export. Inspect once muted and once with audio on a second device. | Drop the optional probe, elaborate scenery and extra sponsor integrations. Keep the bell, movement, decision log and audible final line. |
| 5:00–5:40 | Produce final file, public-repo package, description and sponsor-use summary. Test playback from the submission link. Human team submits with buffer. | Use the previously exported valid cut if the late export fails. |

Bruin can produce something the judges will want to click. Selecting a line in the decision ledger should reveal the object transfer that makes it true, the note’s original authoring event and the alternate branch in a separate view. The raw log remains readable during a projection failure. Bruin supports local DuckDB. Its integration and the AdaL export are event-day work, still to be verified on the team’s accounts. [Bruin DuckDB support](https://getbruin.com/docs/bruin/platforms/duckdb.html)

## What goes in the cut

- **0–25 s.** Same lens, shutter and greeting on two mornings. Let the audience notice the repetition a moment before Tomas. Use the actual diary, action or hesitation to reveal what changed.
- **25–70 s.** Follow the baker’s work and one act that costs another character something. At least one commitment must change what is physically possible. Give her enough screen time for the audience to understand the mainland offer.
- **70–105 s.** Bell, blank diary, drawer. Match the slip to its actual writing event. A legible fraction of a second of matching handwriting does more here than a probability overlay.
- **105–145 s.** Hold on the gangplank for her decision. Hold separately on his hand for his. End on the first morning that follows, or on a genuinely unresolved Tuesday. Only show Wednesday if the reducer advanced the date.
- **Optional final 15 s.** Put two identical pre-choice frames side by side and identify the one changed input. Show a difference only when the measurement found one. Keep the exact full replay available.

For the relationship system, see the [learning design](attachment-learning.md). For a people-reading metric, use a few concrete private facts with independent answers, conceal role-only clues, and compare with a fresh-character baseline. A fresh actor can guess correctly. Award credit only for predictions made before disclosure. For the optional grief readout, split evaluation by scene family, compare to a word-count baseline, swap memories on identical text, keep layer selection separate from final testing, and measure on pre-answer representations as well as generated words. A trace over selected eloquent lines is highly vulnerable to measuring prose style. The action-level fork is the stronger demo. [Probe controls](https://aclanthology.org/D19-1275/) · [Generative Agents and behavioral ablations](https://arxiv.org/abs/2304.03442)
