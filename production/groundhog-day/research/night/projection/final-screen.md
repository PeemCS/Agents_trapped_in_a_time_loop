# Final private screening

**Event-day choice.** Open with *Eight bars*, full-screen. Tell the room the first card is Phil’s supplied theory and plays silently. The first 10.30 seconds contain digital silence before the piano enters. End on the daughter’s “I know that voice. Play it again.”

## First viewing

I recorded these impressions from decoded picture and a fresh local Whisper pass before reading the three films’ production notes. I knew earlier project films, including another seed-711 edit. This was a machine-assisted screening. Room sound and human audience response remain untested.

- **Eight bars.** Phil tries the piano. His next thought puts him at a ballroom table, yet he sits alone at the depot while Rita goes dancing. On a later evening he sleeps on a Pittsburgh terminal bench. The hotel returns at six. Larry records Alma and delivers a reel. Rita also records Alma, takes the regional line, and Alma’s daughter recognizes her voice. I could infer who sent the interview. I couldn’t identify whose recording played. The opening explicitly says Phil was given his movie-ending hypothesis.
- **Couch-hauling season.** Larry wants a cornet-player portrait and films the bandstand. Rita takes Phil’s feed. Phil rides to Pittsburgh and calls his sister about a van and a hallway. Back at the hotel he calls it Wednesday while the clock says Tuesday. He considers multiple “runs,” then takes a second coach to Pittsburgh. I saw him notice a discrepancy. I heard no identification of the movie.
- **The one o’clock coach.** Five departures, five Pittsburgh evenings, five hotel wakes. The final alarm and February 2 calendar made the ending legible without attributing insight to Phil.

## What the receipts settle

Rita’s transmission was necessary. She could send her own recording, or Larry could deliver his day-two reel for her to send. The engine recorded delivery and the daughter’s authored reply without identifying which reel played. The corrected player labels its 15.83 s jump “Larry · earlier take · Tuesday 1” and explains that his day-two capture occurred off screen. I verified both in the live player. [Rialto causal replay](../editor/rialto-cut/backward-search.json)

The supplied clock really said Tuesday. Phil supplied both “Wednesday” and “runs” in emitted model notes. The 35.6–55.6 s terminal shot is where this cut drags. The hallway detail gives the call purpose, but the image holds through the rest of the monologue. The five-trip source contains a sixth departure. The film ends at the fifth witnessed hotel return. [Thinking-cut timing](../editor/thinking-cut/verification.json) · [Five-trip chain](../editor/five-trips/backward-search.json)

## Projection checks

| Film | Fully decoded frames and duration | Complete caption bodies recovered at desktop size | Working seek controls |
| --- | ---: | ---: | ---: |
| Eight bars | 1,926 · 80.250 s | 13/14 at 714 px | 7 |
| Couch-hauling season | 2,168 · 90.333 s | 10/10 at 856 px | 11 |
| The one o’clock coach | 983 · 40.958 s | 4/4 at 699 px | 15 |

All three hashes matched their receipts. Apple Vision read one decoded midpoint frame per SRT cue. The desktop miss was the visible word “hasn’t.” At 356–362 px video width, simulating a 390 px portrait screen at 1×, complete-cue OCR recovery fell to 2/14, 0/10 and 0/4 respectively. The phone-call lower third was particularly crowded.

Chrome 157 played and sought all 33 positions from disk and on the actual loopback server at desktop and phone widths. Stock WEBrick intermittently returned 304 during an immediate seek and Chrome reported media error 2. The project server fixed it. A conditional range request returned HTTP 206 and the correct 100 bytes. From the project root run the command below and open the [screening room](http://127.0.0.1:8765/screening/).

```sh
ruby research/night/projection/serve.rb 8765
```
