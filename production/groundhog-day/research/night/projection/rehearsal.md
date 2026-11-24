# Private projection rehearsal

On November 23, 2026, the three final MP4s played and sought successfully in Mac Chrome from disk and over a range-capable loopback server. Local speech recognition recovered the Wednesday couch call and all 22 words of Rita’s final broadcast in both a continuous listen and individual caption windows. The physical projector, sound system and room were outside this software test.

## Playback at the venue

Run this command from the project root on the rehearsal Mac. Open [the screening room](http://127.0.0.1:8765/screening/) and stop the server with Control-C after the show.

```sh
ruby -run -e httpd -- --bind-address=127.0.0.1 --port=8765 research/night
```

The installed Ruby 2.6.10 and WEBrick 1.9.1 served the screening room on port 8765. Full HTTP downloads of all three films matched their on-disk SHA-256 hashes. Opening each MP4 from disk also passed four playback-and-seek checks.

In Chrome 157 on macOS 27.2.1, the first seek in each HTTP test jumped beyond the data already buffered. The test used an empty browser context, disabled cache, 400,000 bytes/s download and 5 ms network latency. The audio signal was measured at a Web Audio analyser during actual playback.

| Film | Buffered through | First seek landed | Seek wait | Video frames advanced in next ~0.74 s | Peak audio-window RMS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Wednesday Couch | 1.776 s | 89.200 s | 3.880 s | 12 | −10.8 dBFS |
| Afternoon Coach | 1.865 s | 62.800 s | 1.406 s | 11 | −11.7 dBFS |
| The Seven O’clock Bulletin | 2.797 s | 76.000 s | 0.339 s | 18 | −14.5 dBFS |

For the 5,275,606-byte bulletin, Chrome received a partial response beginning at byte 5,046,272. A separate request for bytes 100–199 returned HTTP 206, the correct 100 bytes and `Content-Range: bytes 100-199/5275606`. HEAD returned 200, `video/mp4`, the full size and an empty body. A range past EOF returned 416. WEBrick omitted `Content-Range` on that error. The two other films passed the same protocol checks.

Python 3.14.6’s stock `http.server` returned the full file with HTTP 200 for range requests. Chrome reported a seekable interval of 0–0 s at first load. The same three cold seeks each landed at 0 s and played the opening. This can look like successful playback while showing the wrong scene.

## What the recognizer recovered

| Film | Reference words | Full-track word edits | Cue-window word edits | Integrated loudness | True peak |
| --- | ---: | ---: | ---: | ---: | ---: |
| Wednesday Couch | 151 | 1 | 1 | −17.54 LUFS | −1.35 dBTP |
| Afternoon Coach | 145 | 1 | 1 | −16.05 LUFS | −1.43 dBTP |
| The Seven O’clock Bulletin | 135 | 7 | 2 | −16.98 LUFS | −1.50 dBTP |

**Wednesday Couch.** The full-track recognizer heard “I’ve got a coach to catch” and later “I’m free to help move that couch.” It located “Pittsburgh” at 31.72 s, “Wednesday” at 37.22 s and “couch” at 39.76 s in the phone call. The entire call matched the spoken caption in both passes. The five spoken instances of “Rita” survived. The continuous pass added a second “Pittsburgh” at the end of cue 9. With cue 9 alone, “See you in Pittsburgh” became “See you at Pittsburgh.”

**Afternoon Coach.** All four spoken instances of “Rita” and all three of “Pittsburgh” survived. The recognizer rendered “Rita, it’s 1:00” at 19.795 s as “Rita, it’s 1-0-0” in context and “Rita, it’s 100” in isolation. Both passes recovered the later “one o’clock” and “Afternoon coach, right there. Good.”

**The Seven O’clock Bulletin.** The continuous pass omitted “Let’s get that 7 AM bulletin live” from Phil’s cue at 24.045–32.022 s. The cue-window pass recovered that entire sentence. The isolated second cue rendered “one o’clock coach” as “one the clock coach.” The continuous pass recovered it. At 75.400–82.242 s both passes recovered Rita’s complete station return, matching the selected producer feed and the final SRT.

> Good evening, folks. This is Rita on the scene in western Pennsylvania. We are on the air and ready for the forecast.

## Timing and quiet intervals

All three H.264/AAC files completed a strict FFmpeg audio/video decode. Their MP4 indexes precede their media data. Video and 48 kHz mono audio start at zero. Track end times differ by less than 1 ms, and the native 48 kHz decode contained zero full-scale samples.

One 400 ms voice excerpt from each of the 25 cues matched at its expected sample position in the final mix. Normalized correlations ranged from 0.9875 to 0.9999. The first 24 checks used the exported dialogue for the corresponding opening or short. Rita’s last line used the independently encoded station board aligned at the 56 s join. This samples sync once per cue. At a −45 dBFS threshold in 10 ms windows, voice activity began within −10 to +120 ms of the SRT start. Captions extended 195–577 ms beyond the last active window.

- Wednesday Couch goes 17.131 s between spoken cues at 59.664–76.795 s. Foley interrupts the quiet. The longest continuous stretch below −55 dBFS was 2.88 s, at 73.69–76.57 s.
- Afternoon Coach has 6.162 s after the final subtitle. The delivered audio stayed below −55 dBFS from 67.22–73.72 s, a 6.50 s stretch near the ending.
- The bulletin goes 21.561 s between spoken cues at 53.839–75.400 s. The control-room sequence starts at 56 s with short monitor sounds at 56, 60, 64 and 70 s. Its longest continuous stretch below −55 dBFS was 5.93 s, at 64.07–70.00 s. The Chrome meter read digital silence at 57.3 s and measured speech after the cut to Rita.

## Evidence and method

Whisper base.en ran locally on CPU using faster-whisper 1.2.1 and CTranslate2 4.9.1. The 147,769,510-byte model bundle was downloaded to private temporary storage. FFmpeg supplied mono 16 kHz PCM decoded from each finished AAC track. The first pass consumed the complete track before reading captions. The second used only caption times plus 160 ms of padding on each side. Both used English, beam size five, temperature zero, and local-only inference with no prompt, vocabulary hints, VAD or previous-text conditioning. The lexical scores normalize capitalization, punctuation and equivalent number typography, while preserving distinct clock readings. The browser meter measured the software path before a zero-gain sink.

The evidence file contains input and model hashes, exact SRT cues, ASR transcripts, word-level differences, waveform anchors, silent intervals, Chrome requests and seek measurements. [Machine evidence](evidence.json)
