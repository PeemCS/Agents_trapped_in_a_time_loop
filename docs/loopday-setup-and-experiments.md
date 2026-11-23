# LOOPDAY setup and experiments

The simulation can run on the laptop or in the same Colab process as Phil’s Qwen3.5-9B. Muse Spark 1.3 Contributor (`muse-spark-1.3-contributor`) handles Rita, Ned, and Larry through the Meta Model API. The simulation owns the town, clock, action validation, and run files. The log replays the film and connects an observation to Phil’s next decision. [Qwen model card](https://huggingface.co/Qwen/Qwen3.5-9B), [Muse models](https://dev.meta.ai/docs/muse-spark)

## Connection checks

1. Create a Model API key in Meta’s developer dashboard and store it locally as `MODEL_API_KEY`. Keep the key outside the public repository. Verify one successful request to `https://api.meta.ai/v1/chat/completions`. [Meta Model API quickstart](https://dev.meta.ai/docs/quickstart)
2. Export the Phil notebook with `python3 -m loopday.colab` and select a GPU runtime. Run the single Qwen-only probe before the four-agent canary. The optional laptop-led server uses `PHIL_URL` and `PHIL_TOKEN` for its HTTPS endpoint. A notebook share link provides access to notebook content. Its runtime belongs to the account that started it. [Qwen setup](https://huggingface.co/Qwen/Qwen3.5-9B), [Colab runtimes](https://research.google.com/colaboratory/faq.html)
3. Keep the notebook and model setup reproducible. Save run files and checkpoints outside the temporary Colab VM when they’re needed across sessions. The event allows existing libraries and APIs and places project coding within the event window. [Colab file transfer](https://colab.research.google.com/notebooks/io.ipynb), [Event rules](https://luma.com/finch-jd7i)

Google’s Colab CLI can list active runtimes and execute a notebook or a Python script remotely. Run `colab sessions` to authenticate and check existing runtimes. Enter any one-time authorization code directly in the terminal running the CLI. [Colab CLI](https://github.com/googlecolab/google-colab-cli)

Use short standalone inputs for the first two checks. For Muse, give Rita a location, an upcoming appointment, and two allowed actions. Ask her to choose one as JSON. For Qwen, give Phil a fictional 06:00 observation and the available actions. Ask him to select one. Record the model, response, and token usage where available.

Meta currently lists Muse Spark 1.3 Contributor at $0.10 per million uncached input tokens and $0.20 per million output tokens. For scale, 100 calls with 1,500 input and 240 output tokens each would cost about $0.02 before any credits. Run artifacts record observed use. Colab GPU use is billed separately under the runtime’s plan. Contributor requests may be used for training future Meta models. The Muse requests in LOOPDAY contain scripted town context and simulated character observations. [Meta Model API pricing](https://dev.meta.ai/docs/pricing-rate-limits), [Colab compute limits](https://research.google.com/colaboratory/faq.html)

## Phil’s memory file

Keep one `runs/<run_id>/memory.json` on the simulation side, as in the archive. The laptop loads it, selects the few entries relevant to Phil’s current scene, and includes them in his next Qwen request. Qwen can propose a new belief or reflection. The simulation writes the record and attaches any relevant world event IDs. GitHub can hold the schema and a synthetic example. Keep active run state and credentials local.

| Record | What to store |
| --- | --- |
| Observation | The measured result, loop, time, location, and world event ID. |
| Belief | Phil’s hypothesis and the observation IDs that support or weaken it. |
| Skill | The situation, actions, and observed outcomes across attempts. |

Example observation: “The pencil was whole at 06:00 in loop 3,” linked to the world’s pencil inspection event. Example belief: “Changes to objects in the room may reset at dawn,” linked to the inspection and the previous night’s pencil-breaking event. Rita, Ned, and Larry receive their own observations and conversations from the current day.

## Phil chooses an experiment

Make his realization something viewers can see. Give Phil a reusable option to state a prediction, take an ordinary world action, and inspect the result later. The world records both actions and results. For example, if Phil suspects the radio is playing yesterday’s tape, he could break a pencil before bed and see what happens to it at 06:00. The pencil’s state provides information beyond the repeated broadcast. Leave which object he tests, what he predicts, and how he acts afterward to Phil. [DiscoveryWorld](https://arxiv.org/abs/2406.06769), [CausalGame](https://proceedings.mlr.press/v306/chen26l.html)

Use a critic at the end of the loop or immediately after an experiment. Give it the prediction and the world’s event IDs. Check whether Phil performed the test, whether the result distinguishes the explanations, and whether he uses the result in a later decision. Store those separately so a correct guess and a well-supported conclusion are visible in the ledger. [LUCA](https://arxiv.org/abs/2611.03100)

## Comparison for judging

- **Same checkpoint, evidence present or withheld.** Keep the time, actors, valid actions, model settings, and world state fixed. Change only whether Phil’s prompt includes the previous result. Log his next action and what the town does. Report both outcomes.
- **One fact the movie could never have told him.** In an evaluation run, choose a new time or location for a routine event. Let Phil encounter it, then check whether he uses the learned detail to arrive early on the next loop. The public film can keep the original town and its recognizable anchors. [WorldTest](https://proceedings.mlr.press/v306/warrier26a.html)
- **One film beat from the real run.** Match the framing at 06:00, reveal the object state, then cut to the first thing Phil does differently. Build a Bruin comparison from the logged predictions, results, and decisions.

## First build and run checks

Use the story bible’s ceremony time at tick 4. Keep the 06:00 radio cue, Ned’s opening greeting, and the venue schedule fixed. Give each live character time-bounded choices to move, speak, or act. Log a validated interaction once and use that event both to animate the scene and to build the ledger.

| Case | Expected observation |
| --- | --- |
| Same morning, same observed inputs | The clock, Ned’s opening greeting, and canonical replies repeat during replay. |
| Phil leaves the street before Ned finishes | The world records Phil’s new location and who heard his last line. Ned can respond to the new situation. |
| Phil tries to attend a lesson after it ends | The clock has advanced and the lesson is unavailable. The missed appointment can become a memory for a later loop. |
| Phil makes a pencil prediction and acts on it | The ledger records the prediction before the action, then records what Phil actually sees the next morning. |
| The actor cannot reach or use the proposed object | The world preserves the object’s state and logs why the attempt failed. The next model turn receives that outcome. |

Start with one complete day and a second day that consumes one retained observation. Verify that the same logs drive the decision ledger and a visible consequence before trialing longer runs. For the critic, score three events separately: Phil chose a test, the world confirmed its result, and a later action used that result.
