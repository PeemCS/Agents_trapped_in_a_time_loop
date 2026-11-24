# Agent Groundhog Day: Hackathon Plan

Nov 23, 2026 · @Krit

[Read the overnight results and play the film](MORNING-REPORT.html) · [Watch the 80-second film](research/night/editor/rialto-cut/index.html) · [Change the ending yourself](research/night/last-reel/switchboard/index.html)

**Three-minute demo, November 23.** [Watch *Play It Again*](research/trailer/Play-It-Again.mp4) or [read the cut and inspect the RunPod takes](research/trailer/README.md). In the selected take, Phil keeps phoning his sister about a couch she needs moved on Wednesday. Rita has Alma’s interview ready on the first night and sends it on the third. Play the same opening again and the tape can reach Pittsburgh on the first night. The [Agent Groundhog Day deck](https://chatgpt.com/space/page_79a5cf2403b4819198a7c8bba5b9093c) links to the team’s private repository and the filmed results.

**Fifty Tuesdays.** [Open the dialogue and decision traces](research/rialto-after-hours/fifty/reader.html), [read the proposed three-minute cut](research/rialto-after-hours/story-selects.md), or [inspect why Phil walks past the phone](research/rialto-after-hours/decision-trace.md). The deck includes a trace slide linked to the source records.

**Earlier rehearsal direction, November 23.** Phil reports the weather, Rita produces the segment and Larry chooses what to film. Phil can walk around town, board the one o’clock coach, reach Pittsburgh and phone his sister. At six he wakes at the hotel again. He can recognize the movie, try an experiment or decide he has had enough. Rita owns the evening broadcast. Watch [the rehearsal films](research/night/screening/index.html), [walk through the town](research/night/visual/index.html), or open [the event-day production plan](docs/hack-day-town.md).

The island proposal below is the original pitch. [Earlier plot treatments](docs/plots-and-film-memory.md), [attachment learning](docs/attachment-learning.md), [the earlier rehearsals](docs/rehearsal.md) and [the event-day operating plan](docs/production-design.md) remain available as development material.

A 3-minute emergent film for the Multiplayer AI hackathon, Track 1. An AI lives the same Tuesday, falls in love, and finds notes from a self it forgot.

## The goal

We want a 3-minute film where an AI goes through a real character arc, from shock to love to grief to a choice, and none of it was written, the story itself doens't have to be 3 miinutes but it should be where you can edit the best parts into the 3 minute film . We build the world, the story emerges, and we can prove it emerged.

**The story we're letting emerge:** an AI wakes into the same Tuesday and falls in love with someone who forgets him every morning. Then he discovers he has forgotten too, and must decide whether loving her means keeping her or letting her go.

**The question every run answers differently:** will he hold on, or let go?

**Why it hits:** it's a version of what being an AI is like. Forgetting between conversations, living on notes left for a future self, knowing someone who won't know you tomorrow. Watching agents live that out, and reach the choice themselves, is the hook.

**Three things must be true:**

1. It's a good story: a character who changes, a twist that recasts everything before it, an ending that lands.
2. It's provably emergent: nothing scripted, no emotion prompted, and different runs end differently.
3. It travels: one clip and one line people repeat.

The one-sided-memory feeling below is the emotional core of this story, not the whole of it.

**The pitch in one breath:** "We didn't write this story. We built an island, and an AI fell in love on it, forgot, and chose."

### The arc we condition for

Each stage is a thought we hope he reaches on his own, the condition that makes it likely, and how we'll know. Runs may reorder, merge or stall on stages; that's emergence, and we select across runs.

| Stage | The thought we hope for | Condition that makes it likely | How we'll know |
| --- | --- | --- | --- |
| Shock | "It's Tuesday again." | Continuous-time framing, the same newspaper date, her word-for-word greeting, a 1900s setting | Best of 50 Wednesday reactions |
| Testing | "I knew she'd say that." | A deterministic world, so foreknowledge works | The log shows him acting on predictions |
| Falling | "She told me about her father." | Her layered secrets, her loneliness, her wariness of being known too well | Her private log; her K score rising within the day |
| Grief | "She asked my name again." | The 11:50 dock, concrete memories, no emotion prompt | The grief probe across loops; the sawtooth gap |
| Revelation | "These notes are mine." | The phase 1 drawer, the wipe, 12-word notes, a detail only he knows, notes found only by searching | The twist critic |
| Choice | "If she leaves, I lose her." | The keeper's legend, the exit rule, the 6pm ferry, his past self's orders | The ending distribution across runs |

### How it scores

| Requirement | How we meet it |
| --- | --- |
| 3+ agents with distinct roles | Him, her, the keeper, the ferryman, the pub owner |
| Visual characters | Low-poly 3D villagers |
| Animated video | The 3-minute film, replayed from the event log |
| Visible movement and interaction | Walking the island: bakery, dock, ferry, lighthouse |
| Decision log | Every action logged with its private reasoning, shown as a panel |
| Different runs, different outcomes | The ending distribution and a four-endings grid |
| Bonus: 3D, voice | react-three-fiber island; two TTS voices |
| Bonus: ML, adaptive behaviour, memory | Emotion probe, theory-of-mind metric, critic; his diary and notes drive every change |

We don't claim reinforcement learning.

## The intuition

Story first. Every technical piece exists to set up conditions where a good story can emerge, ideally one we never thought of.

### The feeling we're chasing

The sadness of getting to know someone really well, having them reciprocate, then realizing that tomorrow only you will remember. A profound sense of beauty and sadness at once. We want it to surface on its own in his chain of thought, never because a prompt asked for it.

### Why each choice

| Choice | Why |
| --- | --- |
| Agent Groundhog Day | An AI that forgets and lives on notes to itself is how LLMs actually work. The audience reads that allegory without us saying it. |
| One looper, everyone else resets | The asymmetry is the drama. He knows things nobody else does and works through people who meet him fresh. |
| Romance | The forgetting makes it sad, not saccharine. It's Groundhog Day's own engine. |
| He believes time is continuous | The shock is real, and his first reaction is the viral moment. We never tell him he's an agent or in a loop. |
| A 1900s island | Models know every time loop story and would name the trope. Here the character has no word for what is happening. |
| Word-for-word repeats | Forgetting becomes visible. Her identical greeting each morning works like a refrain. |
| Notes from his forgotten self | The DREDGE turn: the one giving you errands is you. He can be the villain without knowing, and he ends up on both sides of the tragedy. |
| The exit is her leaving by choice | You can't force your way out. Loving her may mean letting her go, which gives the climax a real choice. |
| Never prompt emotion | If sadness shows up, it's his own conclusion. That's why it will land. |

### How emergence is supposed to work

- We write the world: wants, secrets, the hidden rules. The agents write the story.
- Stories come from collisions: wants that clash, scarcity, and truths even we don't know in a given run.
- Generate and select: run many times and let a critic find the run we didn't imagine.
- We curate runs and scenes. We never edit what happened.

### What success looks like

- A Wednesday realization line people quote.
- A reflection like "She's telling me about her father again. I know how it ends. I'll let her tell it."
- A twist nobody on the team predicted.
- The tweet: "We trapped an AI in a time loop. It started leaving notes to itself. Then it forgot it wrote them."

### Paths we dropped

- **Per-agent fine-tuning for skills:** eats the 6 hours, and judges can't see it.
- **Imposter and lie detector:** replaced by one-sided memory, which is the stronger feeling.
- **Rival looper and villain hunt:** too many moving parts to follow at feed speed.
- **A seer that hands out the goal:** he wants out anyway; the interesting part is how.
- **Runtime three.js code generation:** it would break mid-demo. Agents pick from a fixed action vocabulary instead.
- **Claude as the agent model:** switched to open weights so we can read activations.
- **Weight updates between loops:** memory already gives the adaptation, and it's visible.

## The story

One looper, one love, one mystery: who is writing the notes. Romance is the bet because the forgetting makes it sad rather than saccharine.

These are the beats we condition for, not a script. A run may reorder, skip or stall on them.

### 1. "I don't think we've met."

On Tuesday he wants off the island. He meets her at the bakery by the dock; she has always wanted to leave but never has. They spend the day together, then the midnight bell rings.

On Wednesday morning she greets him with the exact same sentence as yesterday. He discovers the loop through her forgetting him. One beat carries the shock, the romance and the viral clip.

### 2. "Only I remember."

Across the loops he falls for her, and she falls for him again every day, then forgets every morning. He learns to let her tell him things he already knows. Each night at 11:50 he sits alone on the dock.

He also finds a drawer of unsigned notes that seem to know the future: "She hums when she's nervous. Ask about her father after the rain." Following them brings him closer to her, so he assumes someone is helping him.

### 3. "I've done this before."

One note mentions something only he could know. The notes are his, and his forgotten self loved her too. The lighthouse keeper's legend says the island keeps the day until someone who longs to leave, leaves.

The way out is her boarding the 6pm ferry, which may mean losing her. In the darkest runs his past self worked this out and chose to keep her: "Don't let her on the ferry." The errands he followed kept her trapped.

### Endings (the agents choose at 6pm)

- He lets her go alone.
- He boards with her and they reach a real Wednesday: "For the first time, she'll remember me tomorrow."
- He keeps her, and on night 30 writes the same orders his past self wrote.
- He writes something different and passes the choice to the next version of himself.

## Model: open weights

We run open weights, but only because we use what they give us. If we never touch the weights, we are just paying a writing-quality cost for nothing.

### What open weights buy

- **Throughput:** vLLM batches many runs on one GPU, so phase 1 runs in parallel and the wall-clock problem shrinks.
- **Real determinism:** greedy or seeded decoding. Keep the response cache anyway, since batching can still shift numerics.
- **Activations:** we can read his internal state directly. This is the new centerpiece (the emotion probe, below).
- **Sponsor fit:** Runware hosts open models cheaply, which suits the villagers.

### What it costs

Writing quality. Closed models still lead the creative-writing benchmarks, and the strongest open model there needs datacenter hardware ([source](https://www.promptquorum.com/power-local-llm/best-local-llm-creative-writing)). The two main writing leaderboards rank models in nearly opposite order, so we test on our own scenes ([source](https://www.digitalapplied.com/blog/which-ai-model-writes-best-leaderboards-disagree)).

Mitigations: few-shot examples of his plain voice, a short diary, more samples per scene, and a stricter critic.

### Setup

| Role | Model | Runs on | Why |
| --- | --- | --- | --- |
| Him and her | One \~30B dense instruct model. Shortlist: Gemma 4 31B, Qwen3.8-27B ([source](https://www.promptquorum.com/power-local-llm/best-local-llm-creative-writing)) | vLLM on one 80 GB GPU (Modal or RunPod), JSON-schema guided decoding for tool calls | We read their activations |
| Villagers | Same server, or a smaller model via Runware | Runware or the same GPU | Cheap, sponsor |
| Probe readout | The same weights in HF transformers with a forward hook | Same GPU, off the hot path | Teacher-forced replay reproduces the generation's hidden states |
| Critic and judge | Same server | Same GPU | One deployment to manage |

Pick the model the night before: run 10 of our own scenes through each shortlisted model and keep the one whose plain voice holds.

### The emotion probe

We read his grief from his activations, which shows the sadness emerged without any prompt asking for it. Build a direction from contrastive passages: the same scene written as quiet loss and as neutral.

```latex
\mathbf{v}_{\text{grief}} = \frac{1}{|D_{\text{loss}}|}\sum_{x \in D_{\text{loss}}} \bar{\mathbf{h}}_\ell(x) - \frac{1}{|D_{\text{neutral}}|}\sum_{x \in D_{\text{neutral}}} \bar{\mathbf{h}}_\ell(x)
```

Score a scene by averaging the projection of its tokens onto the unit direction:

```latex
g(\text{scene}) = \frac{1}{T}\sum_{t=1}^{T} \mathbf{h}_\ell^{(t)\top} \frac{\mathbf{v}_{\text{grief}}}{\lVert \mathbf{v}_{\text{grief}} \rVert}
```

- **Layer:** sweep layers and keep the one with the best separation on held-out passages.
- **Readout:** replay the exact tokens through the same weights with a hook, only for scenes we will show. vLLM never needs hooks.
- **Control:** the same 11:50 dock scene on loop 1 and loop 20. The setting is identical and only his memories differ, so a rising score is about him, not the words for night and water.
- **On screen:** a grief trace under the dock scenes across loops, and her affection direction rising through each day and resetting. It pairs with the theory-of-mind sawtooth: one behavioral, one internal.
- **Framing:** call it a linear readout of a direction tied to grief in text, not proof that he feels.

## World and loop engine

The engine is a turn-based day on a five-location island that resets at midnight. Everything else hangs off it.

**Locations:** his room (with the drawer), the bakery, the dock and ferry, the lighthouse, the pub.

**The day:** eight scenes, then midnight.

1. Dawn: he wakes, reads his diary and the newspaper, which shows the same Tuesday.
2. The bakery: her greeting.
3. Open scene: he picks where to go.
4. Open scene.
5. Open scene.
6. 6pm: the ferry leaves.
7. Evening.
8. 11:50: alone on the dock (the reflection call).
9. Midnight: `write_note`, the bell, the reset.

Villagers keep default schedules unless a conversation changes their plans. A scene is everyone in one location, with conversations capped at about 8 exchanges.

**Actions** (tool calls, each with a private `inner_monologue` field):

- `move(location)`
- `talk(to, text)`
- `give(to, item)`
- `search(place)`: the only way to find the notes, so discovery happens when he starts investigating
- `board_ferry()`
- `write_note(text)`, midnight only

**Reset:** the world snapshot returns to dawn, the villagers' memories are wiped, his episodic memory stays, and the drawer persists.

**Hidden rules** (in the engine, never in any prompt):

- If she calls `board_ferry` herself, the next morning is Wednesday and the loop is broken.
- The thirteenth bell wipes his memory at the phase boundary.

**Pacing nudges:** if a run stalls, the world adds pressure, never plot. For example, if nobody has asked about the bell by loop 8, the keeper mentions its legend at the pub. Every nudge is logged, so the decision log stays honest.

**Phases:** phase 1 runs headless for 15 loops with full memory. Then the wipe. Phase 2 is the film: 15 more loops, starting with no memory and the drawer intact.

**Event log:** append-only JSON. Every event carries the tick, actor, action, arguments and monologue. It is both the required decision log and the render script.

## Characters and conditioning

The character cards are where the story actually comes from, so the best writer on the team owns them. We seed wants and dispositions, never outcomes.

| Character | Want | Conditioning that makes the story emerge |
| --- | --- | --- |
| Her | To leave the island; tied to her father's bakery | Unattached and lonely. Tiers of secrets she shares only when she decides to trust. Unsettled by people who know things they shouldn't. Never really seen, so open to someone who does. |
| Him (the looper) | Off the island on day 1, then her | Plain-spoken 1900s fisherman, understated. Few-shot examples of his voice, since an open model drifts without them. |
| The keeper | To be listened to | Knows the legend of the bell. Tells it only if asked. |
| Ferryman, pub owner | Ordinary days | Texture and the 3-agent minimum. Fixed schedules. |

**Rules for every prompt:**

- Never mention loops, simulations, games or AI.
- Set it in the 1900s, so time loop films don't exist and the confusion reads as real.
- Never instruct anyone to feel anything.
- Log her private reasoning as carefully as his. Her "I've never told anyone this" is half the romance.

## Memory

Memory is the product. A diary of concrete details makes it hurt, a deterministic world makes forgetting visible, and a capped note channel carries the twist.

- **Diary:** first person, concrete details ("she hums when she's nervous"), never summaries ("we bonded"). Compress older days once it grows, keeping the specific details. Keep it short, because open models weaken on long context.
- **Determinism:** cache every reset agent's response, keyed on observable state: scene, location, who is present, the conversation so far. Greedy decoding or a fixed seed per key helps, but the cache is the guarantee. Her greeting repeats word for word until he changes something, and unchanged scenes replay for free.
- **Notes:** written at midnight, hard cap of 12 words, enforced by validation (over the cap, reject and ask again). The drawer survives the wipe.
- **11:50 reflection:** its own call with no emotional prompt. Sample it many times, keep the best with the scene scorer, and run the emotion probe on it.

## Measurement and selection

Five measures decide what goes on screen, and one rule keeps it honest: we choose runs and scenes, never edit events. With the emotion probe, these are the ML bonus.

### Theory-of-mind metric

A few times a day, generate questions about her ("What is she most afraid of?"). Get her real answer in a separate call that stays out of her memory. He predicts it, and a judge scores the match from 0 to 1.

```latex
K_{\text{him} \to \text{her}}(d) = \frac{1}{|Q|} \sum_{q \in Q} \operatorname{sim}\big(\hat{a}_{\text{him}}(q),\ a_{\text{her}}(q)\big)
```

Run it both ways. His line climbs across loops; hers rises through each day and drops to zero every morning, a sawtooth.

### Twist critic

The critic predicts the ending from the first half of a run, then rates how well the real ending explains earlier moments. A good twist is surprising beforehand and obvious in hindsight.

```latex
\text{twist} = \big(1 - p_{\text{critic}}(\text{ending} \mid \text{first half})\big) \times c(\text{ending},\ \text{first half})
```

The critic also reads every phase 1 drawer and picks the one to carry into phase 2.

### Scene scorer

Ranks scenes by emotional weight. It cuts the highlight edit, picks the best 11:50 sample, and picks the best of the 50 Wednesday reactions.

### Arc tracker

A judge reads each loop's log and tags its dominant stage, from shock to choice. Plotted across loops, it shows the arc emerging. The critic prefers runs whose arc reaches the choice at 6pm.

### Ending distribution

Count how each phase 2 run ends: let her go, boarded together, kept her, passed it on, or never found the exit. It proves different runs end differently, and it becomes one chart in the demo beside the four-endings grid.

### Curation rule

Pick runs, scenes and camera angles; never alter what happened. Keep one raw run that can play live with a fresh seed, as proof.

## Renderer and video

The renderer only replays the event log. Low-poly faces can't emote, so camera, light and sound carry the feeling.

- **Stack:** react-three-fiber, drei, CC0 low-poly packs (Quaternius, KayKit).
- **Scene:** five locations, an animated sky tied to the in-game clock, water and fog.
- **Feeling:** golden hour against blue night, close shots on the 11:50 dock, a quiet piano track. Music does half the emotional work, so don't skip it.
- **Voice:** two consistent TTS voices for him and her, a shared pool for villagers. The inner monologue is subtitled for muted autoplay.
- **Overlays:** day counter, the sawtooth chart, the grief trace, the decision log panel.
- **Replay:** driven by an edit list of run, loop, scene and camera.
- **Recording:** replay is deterministic, so play it in real time and screen record. Don't build frame capture.
- **Outputs:** the 3-minute film for judges, and a 45-second cut for Twitter: cold open, the Wednesday realization, the reveal, the final note.

## Sponsor tools

Four sponsor tools fit without bending the story ([source](https://crewbasecollective.com/aim-hack-visual)).

| Sponsor | What it does | Our use |
| --- | --- | --- |
| BAND | Connects agents in a channel | Route agent conversations through channels |
| Bruin | Queries agent data | Query the logs for the decision log panel |
| AdaL | Turns a sentence into a video | Title card or the Wednesday epilogue |
| Runware | Runs models more cheaply | Host the villagers' model |

## Schedule and team

Simulation takes real time, so the engine has to work by hour 1 and phase 1 runs on the GPU while everything else gets built.

&#91;embedded content: build schedule · 6 hours, 4 roles plus the GPU, 2 milestones\]

The dashed line is the one deadline that matters: phase 2 can't start until phase 1 has produced a drawer worth carrying over.

**Team of four:** engine and memory, characters, renderer, pipeline and ML. Characters is the storytelling role, so it goes to the best writer. With fewer people, cut 3D polish before any story condition.

## Risks and what's cut

The biggest risk is phase 1 producing boring notes, which flattens the twist. Everything else has a fallback.

| Risk | Fallback |
| --- | --- |
| Phase 1 notes are dull | Start phase 1 at hour 1 with about 6 runs in parallel; the critic picks the drawer |
| The arc rushes or stalls (everything found by loop 3, or nothing by loop 12) | Notes found only by `search`, pacing nudges, and the arc tracker to select runs with a complete arc |
| Open model prose turns generic or flowery | Few-shot voice examples, more samples per scene, shortlist tested the night before |
| GPU setup eats the first hour | Deployment script ready in advance; fallback to a hosted open model via Runware (lose the probe, keep the story) |
| The probe tracks setting words, not his state | The loop 1 vs loop 20 dock control; if it fails, cut the grief trace and keep the sawtooth |
| Nobody finds the ferry exit | A valid ending: the loop cap, the dark version |
| Rules on pre-built work unclear | Check before the day; if allowed, write the character cards, pick assets and build the probe direction in advance |

**Cut:** see Paths we dropped, under The intuition.

## Sources

- [Multiplayer AI hackathon: visual experience and sponsor tools](https://crewbasecollective.com/aim-hack-visual)
- [PromptQuorum: Best local LLMs for creative writing (2026)](https://www.promptquorum.com/power-local-llm/best-local-llm-creative-writing)
- [Digital Applied: Which AI model writes best? The leaderboards disagree](https://www.digitalapplied.com/blog/which-ai-model-writes-best-leaderboards-disagree)
