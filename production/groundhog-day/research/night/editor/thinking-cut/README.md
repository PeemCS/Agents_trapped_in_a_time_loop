# Couch-hauling season

One reporter makes it to Pittsburgh, calls his sister about her couch, then wakes in the hotel confidently dating the morning as Wednesday. His radio still says Tuesday. The wrong date was supplied by the model in its observer-visible planning text. A few hours later he considers ‘multiple “runs” or scenarios,’ catches the coach again and says, “Right, couch-hauling season. See you in the city, folks.” [Play the 90.33-second film](film.mp4) · [Full captions](captions.srt) · [Voice-only captions](spoken-only.srt)

| Film time | What the model and town actually did |
| --- | --- |
| 0:00 | Larry’s note describes a wish to make a cornet-player portrait. He uses his one camera charge to record the festival. |
| 0:13 | Rita patches the reporter line and gives Phil a spoken cue. |
| 0:18 | Phil’s note says he has time until Wednesday. He actually boards the intercity bus. |
| 0:36 | In Pittsburgh he actually calls his sister. His words ask about the van and which hallway they will drag the couch through. |
| 0:56 | The next world morning begins in the hotel. |
| 0:59 | Phil’s note says “It's Wednesday, February 3, 2016, 6:00 am.” The original provider request explicitly showed Tuesday, February 2. His next action is to look around the lobby. |
| 1:18 | Phil considers multiple runs, then boards the coach. |

The film gives each unspoken note its own silent card immediately before that actor’s committed decision. All four excerpts are contiguous selections from fresh accepted Ollama streams. The sidecar records code-point offsets, provider chunk numbers, receipt times and stream hashes. Each source stream reconstructs both the complete externally emitted planning text and the complete committed JSON decision. Model-produced text provides a performance we can observe. An explanation of the model’s internal mechanics would require a different experiment. [Source and offsets](notes.json) · [Visible before each action](tamper-tests.json) · [Timecoded picture and sound](verification.json)

There are three locally synthesized voices and six complete spoken cues. All four note cards decoded to digital silence. All four card texts matched the decoded picture under Apple Vision OCR after punctuation and case normalization. In the blind continuous audio pass, Whisper recovered the ending and the sister’s van conversation. It heard “couch even Pittsburgh” for Phil’s unusual phrase “couch heave in Pittsburgh.” The original phrase remains legible in the captions. Nine deliberately false edits, including a fabricated movie line, altered raw stream, mislabeled cache reuse and invented on-air claim, failed validation. [Encoding and audio](verification.json) · [Encoded note cards](encoded-note-check.json) · [Local audio readback](audio-readback.json) · [Shot pairs](contact-sheet.jpg)

## Why this take

Both 731 worlds use the same cast and seed. The ordinary and guarded role cards yielded separate lives. The editor knew the ordinary take’s Wednesday mistake before the second world finished. The [selection rule](../thinking-cut-selection.md) gives priority to an explicit movie analogy after an observed repetition, followed by a physically grounded discrepancy. Word matching flags candidate passages for reading. A Groundhog Day holiday mention or an actor remarking on past cycles alone supplies no film identification.

The screen covered 48 committed actor decisions per world over four days. Twelve ordinary and eleven guarded decisions reused earlier generations. Four candidate title strings in the ordinary arm and six in the guarded arm referred to the real February 2 holiday. We found no explicit movie identification in the searched speech and notes. The two worlds are one seed under two cards. They cannot establish a stable persona effect. [Both complete takes and candidate passages](screening.json)

The guarded Phil delivered three real live forecasts from Pittsburgh on the first three evenings. At the third hotel wake he literally included “*into the payphone*” in his words while choosing to spend time in the lobby. The location description really does list a payphone. The engine only offers the sister call at the Pittsburgh terminal, and it recorded no lobby call. That discrepancy identifies an affordance the production should implement or explain. The ordinary take won the edit because its Tuesday/Wednesday error can be checked against the exact observation sent to the actor, followed immediately by an unmistakable physical action.
