# Eight bars in 3D

[Open the interactive stage](index.html) · [Watch the 26.5-second 3D cut](evidence/eight-bars-3d.mp4) · [Watch the illustrated short with sound](../../../editor/rialto-cut/index.html)

Phil rehearses eight bars at the ballroom piano. That evening he sits alone at the local depot, while Rita makes her own decision to go dancing. Open the [two-venue shot](index.html?shot=d01-evening-reporter&view=split&at=.70) to watch the two recorded choices side by side. On a phone, the two views stack vertically.

**Play** advances the performance. Choose a shot, drag the timeline or use the arrow keys to scrub. **House**, **Close** and **Overhead** change the lens. The underlined crew names follow another actor from the same decision slot. The full-screen control expands the stage. The viewer opens directly from disk. In a browser with WebGL disabled, it can play the local illustrated film.

## What the performance records

The [original 721-hypothesis take](../../../last-reel/runs/721-hypothesis/take.json) supplies every committed action and its resolved effect. Phil starts this branch with the theory that reenacting the movie's ending could unlock Wednesday. The crew can choose independent physical actions. Alma appears as a world character in the recorded interview. Her daughter’s reply is a piece of world-authored mail in Phil’s third-morning observation.

| Shot | Physical action | Source ID |
| --- | --- | --- |
| Ballroom piano | Phil rehearses the final eight bars. | `d01-afternoon-reporter` |
| Local depot | Phil sits alone on the empty bench. | `d01-evening-reporter` |
| Ballroom floor | Rita goes dancing in the same evening slot. | `d01-evening-producer` |
| Intercity coach | Phil takes the paid coach and steps off in Pittsburgh. | `d02-afternoon-reporter` |
| Rialto projection booth | Rita records Alma. Larry uses his last charged recording there too. | `d02-afternoon-producer` and `d02-afternoon-camera` |
| Pittsburgh terminal | Phil sleeps on a terminal bench. | `d02-evening-reporter` |
| Regional station intake | Larry delivers Alma’s reel. | `d02-evening-camera` |
| Regional line | Rita transmits. The interview reaches Alma’s daughter in Pittsburgh. | `d02-evening-producer` |
| Hearthside Hotel | At six on the next Tuesday, Phil sees the mailed reply, “I know that voice. Play it again.” | `d03-afternoon-reporter`, world observation |

The physical envelope ends this cut. The resolver establishes delivery with two usable sources and leaves the identity of the played reel unspecified. The imagery places Larry’s film in an intake tray. The regional console displays its own line activity. The local depot, ballroom, Rialto, regional patch, Pittsburgh terminal and Hearthside each have separate stage roots. The original native seed-701 town has its own geometry and routes.

Set dimensions, dance steps, hand poses, lights, camera positions and shot duration are editorial. Split views align two acts from the same model decision slot. The engine records that shared slot and each physical outcome. Exact timing within the slot comes from staging. The separate sets sit 24 metres apart in a production layout. They convey distinct places without making a claim about geographic distance.

[Projection booth](evidence/rialto-booth.png) · [Depot and ballroom](evidence/parallel-evening.png) · [Pittsburgh and the regional line](evidence/parallel-transmission.png) · [The envelope](evidence/receipt.png) · [Portrait controls](evidence/mobile-split.png)

## Evidence and reuse

The [projection builder](build_take.py) reads committed actions, request keys, resolver outcomes and the single written receipt. Eight role-bound shots and one world observation appear under their full source request keys. Identical model calls can share a cache key across days. The run name, day, phase and role identify a decision occurrence. The raw source SHA-256 is `b7500bd631c2a27cbf43ae396b48ee28247e665c77d7707acd8207390340f3ea`.

The [set builders](sets.js) contain the original replaceable geometry. The [stage reader](rialto.js) selects the set, samples motion and switches cameras. A split shot uses one WebGL renderer with independent scissored views. Both coverage angles at the station evaluate identical performer positions and reel placement at the same input progress. The projection carries the three crew positions, public world effects and the written receipt.

After `rialto3d:ready`, the page exposes `window.Rialto3D.seek(shotIndex, normalizedProgress)`, `setCamera("house" | "close" | "overhead")`, `setParallel(boolean)`, `setCinematic(true, {captions:true})`, `renderNow()` and `getState()`. Deep links accept a source event ID in `shot`, normalized progress in `at`, `camera` and `view=split`. The [frame ledger](evidence/shot-ledger.json) gives each rendered camera’s source ID and complete request key, the edit’s frame ranges and the film hash.

From the repository root, rebuild and verify with Python, Playwright, Chromium, FFmpeg and ffprobe. Set `CHROME_PATH` for an alternate installed Chromium executable.

```sh
python3 -B research/night/stage3d/viewer/rialto/build_take.py
python3 -B research/night/stage3d/viewer/rialto/verify.py
python3 -B research/night/stage3d/viewer/rialto/render.py
```

The [verification report](evidence/verification.json) covers 36 checks, including the source bytes, independent casts, key movement, eyes closed at the terminal, a real reel handoff, split-camera geometry, the physical receipt, touch controls and video fallback. The recorded cut is silent H.264 at 960 × 540, 24 fps and 636 frames. Physical-phone performance remains unmeasured.
