# Play It Again

The standalone film follows the first 108 seconds of the Groundhog Day recording script, then closes on a three-second title. The three-minute presentation continues directly from Wednesday into the scripted live-demo section. Both public MP4s are silent and include English subtitles.

## Scene sources

Open `Play-It-Again-sets.blend` to edit the modeled sets in Blender. The camera cuts, character performances, lighting changes and final grade run in Three.js. `edit.js` contains the 24 fps picture edit. `exteriors.js`, `hotel.js` and `music.js` contain the shot blocking. The matching Python files build the original unit sets and export their GLBs.

The original score reprised the same phrase at the upright. The finger movements and note attacks share `piano-score.json`. The original mix combined the project's cast and radio tracks with four synthesized Phil pickups, the period-room effects and the piano performance. `Trailer-complete.srt` follows the finished mix.

## View the Three.js cut

From this folder, run the commands below and open [the screening room](http://localhost:8080/stage.html). The Play button starts the silent scene preview.

```sh
npm ci
python3 -m http.server 8080 --bind 127.0.0.1
```

## Rebuild the film

The saved GLBs support a picture-only render. The render commands on this Mac use Chrome, Python Playwright, Pillow and FFmpeg. Regenerating the unit GLBs from Python uses Blender 4.2's `bpy` module.

```sh
python3 render.py --output /tmp/play-it-again-picture.mp4
```

The screenplay and picture handoff are in [the recording script](../audio-live/script-mix/Groundhog-Day-recording-script.md) and [the storyboard](../storyboard/video-handoff.md). The film dramatizes several rehearsals. The Ned-to-Rita conversation and the Wednesday exchange are scripted scenes.
