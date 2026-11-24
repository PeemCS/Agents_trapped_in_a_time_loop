# Fifty Tuesdays

Phil bought maple syrup for the first pancake his sister makes after they move their father's couch. The bottle is back on the hotel dresser every morning. Only Phil remembers reaching the night before that breakfast, again and again.

[Open the searchable dialogue reader](fifty/reader.html) · [Read the three-minute paper cut](story-selects.md) · [Follow a decision trace](decision-trace.md) · [Read Phil’s 100 voice memos](fifty/voice-diary.md)

## What happened

We ran one Phil for 50 consecutive Tuesdays in Rialto on an H100 GPU. The 908 performed turns include 100 private recordings. He packed the syrup 40 times, left it wrapped eight times, opened it for himself once, and poured it out once. He called Jo on 22 afternoons and walked past the working phone on 28. The log contains 61 distinct recording texts across 100 memos, including stretches when he repeats an earlier recording word for word. [Verified counts](fifty/outcomes.json)

On Tuesday 28 he empties the bottle into the sink. By night he is telling the recorder the syrup is in his bag. On Tuesday 50 he packs the bottle, calls Jo, and she tells him she’s making pancakes on the blue griddle. He still cares. His evening recording is down to a few words: “Cut it. Eight o'clock, sharp.” [The low point](fifty/day-28.json) · [The fiftieth Tuesday](fifty/day-50.json)

In four paired auditions we offered the same hotel pancake before and after the long run. All eight Phils stayed to eat it. Their dialogue and stated motives differed. The comparison supports keeping the sink scene as a moment of despair, without claiming the invitation permanently lost its meaning. [The eight performances and their stated motives](fifty/breakfast/README.md)

## What was on the role cards

Take 951 follows one Phil. His first morning supplies a real thing he likes, the lopsided first pancake off Jo’s blue griddle. Every morning he can pack her syrup, leave it wrapped, open it for himself, or pour it out. Every afternoon he can call Jo or walk past the phone. The simulation never pays him a Wednesday. There is no villain role and no rule that lowers his mood.

Only Phil carries memories across Tuesdays. He gets the turns he witnessed over the last two days, his first morning and evening recordings, Jo’s first telephone reply if he heard one, and his own two recordings from every seventh earlier day. The archive keeps every performance in full. Rita, Larry, Alma and Jo start each Tuesday with the same role cards. They hear the people in their room, including someone at the other end of an answered phone. Larry and Rita can repeat something Phil said to Alma once he leaves. She never receives his private recordings.

At seven, Larry can prepare one input and Rita can route it. A missing cartridge cannot be played. Alma can limit her voice to a private telephone line, authorize a public microphone or decline both. Phil can hear the public station. Dead air alone tells him nothing about what the crew said behind closed doors. A character can still misremember, lie or contradict the stage record.

The reader shows the decision trace beneath each line. It includes the last witnessed turn, all earlier context supplied to that character, the options open to them, their chosen action, and the later decisions that received it. The pocket recordings are performed dialogue. For a short example with a source at each step, open [why Phil walks past the phone](decision-trace.md). Selected scenes also have a one-sentence public cast commentary, recorded in a separate playback pass after the scene with access only to that character’s evidence. A cast member’s recollection can conflict with the clock or the action they took. Tuesday eight has an example. The cast comments never enter a later day. Model thinking was disabled. [World and role cards](shoot.py) · [Long-run memory rules](fifty.py)

## Reading the evidence

The reader works offline. Download `reader.html` and open it in a browser. Select **All Tuesdays** to search the whole run. **When Phil is absent** plays the other side of the story. The voice diary also reads directly on GitHub.

The three four-day takes and two single-day replays have their own transcripts. The replays use the same morning with a single silent change to what Phil does with the weather cartridge. [Offscreen scenes and replay outcomes](room-takes.md)

Run `python3 -B read_fifty.py`, `python3 -B readback.py` and `python3 -B compare.py` in this directory for an offline check of actor inputs, output text, witnesses, permissions and recorded choices.
