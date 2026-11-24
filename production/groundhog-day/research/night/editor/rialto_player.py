#!/usr/bin/env python3
"""Package a subtitle-enabled festival player and a receiver-to-source trace that works from disk."""

import json
from pathlib import Path
import sys
from html import escape


def build(folder):
    evidence = json.loads((folder / "shot-evidence.json").read_text())
    proof = json.loads((folder / "backward-search.json").read_text())

    def shot_link(shot, label):
        return f"<button data-at='{shot['start_s']:.4f}'>{escape(label)}</button>"

    notes = [s for s in evidence["shots"] if s["kind"] == "note"]
    steps = "".join(
        f"<li>{shot_link(n, n['actor'] + '’s note at ' + str(round(n['start_s'])) + 's')}</li>"
        for n in notes
    )
    full = "<br>".join(
        escape(x["event"]) + " · " + escape(x["verb"].replace("_", " "))
        for x in proof["individually_necessary_in_full_recorded_contribution_set"]
    )
    routes = "".join(
        "<li>"
        + " → ".join(escape(x["verb"].replace("_", " ")) for x in chain)
        + "</li>"
        for chain in proof["minimal_sufficient_sets_for_delivery"]
    )
    causal_ids = {x["event"] for route in proof["minimal_sufficient_sets_for_delivery"] for x in route}
    picture_ids = {s["event_id"] for s in evidence["shots"] if s["kind"] == "action"}
    missing = causal_ids - picture_ids
    buttons = []
    for shot in evidence["shots"]:
        if (
            shot["kind"] == "receipt"
            or shot["action"]
            in ("transmit_interview", "interview_Alma", "film_Alma", "deliver_reel")
            and shot["kind"] == "action"
        ):
            buttons.append(
                shot_link(
                    shot,
                    shot["actor"]
                    + " · "
                    + (
                        "receipt visible in his input"
                        if shot["kind"] == "receipt"
                        else (shot["action"].replace("_", " ") if shot["event_id"] in causal_ids else "earlier take · Tuesday " + str(shot["day"]))
                    )
                    + " · "
                    + str(round(shot["start_s"]))
                    + "s",
                )
            )
    pg = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title><style>
:root{color-scheme:dark;--bg:#13272b;--fg:#f2e4c9;--accent:#edba77;--muted:#bbcdc0}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:"Avenir Next",system-ui,sans-serif}main{max-width:1180px;margin:35px auto;padding:0 24px 30px}h1,h2{font-family:Georgia,serif;font-weight:400}h1{font-size:clamp(46px,7vw,80px);line-height:1.05;margin:0 0 10px}h2{font-size:29px;margin-top:15px}p,li{line-height:1.5}article{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(270px,1fr);gap:22px}video{width:100%;aspect-ratio:16/9;display:block;background:#000}button{background:#243e40;color:var(--fg);font:inherit;padding:8px 10px;border:1px solid #55706a;border-radius:4px;margin:4px 0;cursor:pointer}button:hover,button:focus-visible{border-color:var(--accent)}.deck{color:var(--muted);margin:0 0 20px}.paths{color:var(--muted);padding-left:20px}.links{display:flex;flex-wrap:wrap;gap:6px}.role{font-size:14px;color:var(--accent)}a{color:var(--accent)}details{border-bottom:1px solid #44605e;padding:12px 0}summary{cursor:pointer}aside h2{margin-top:0}li button{margin:0}ul.plain{list-style:none;padding:0;display:flex;gap:8px;flex-wrap:wrap}@media(max-width:780px){article{grid-template-columns:1fr}main{margin:18px auto;padding:0 14px}}
</style></head><body><main><header><h1>__TITLE__</h1><p class="deck">A three-day Rialto rehearsal from the __TAKE__ take.</p></header><article><section><video controls preload="metadata" playsinline src="film.mp4"></video><ul class="plain">__NOTES__</ul><a href="captions.srt">Captions</a> · <a href="shot-evidence.json">Source dialogue and picture evidence</a></section><aside><h2>Follow Alma’s reply</h2><p>Her daughter’s receipt appears in Phil’s next morning observation. Jump to the work that made it possible.</p><div class="links">__BUTTONS__</div><details open><summary>Which actions could deliver the interview?</summary><ol class="paths">__ROUTES__</ol><p class="role">Required across every sufficient route</p><p>__NEEDED__</p></details><details><summary>Which Tuesday did the actors live?</summary><p>The closed world returned to Tuesday even after the first successful delivery on day __DAY__. The daughter’s receipt survived. A separately evaluated rule would have advanced to Wednesday at that delivery. The actors never experienced that alternate morning in this take.</p></details><p><a href="backward-search.json">Read the counterfactual comparisons</a></p></aside></article></main><script>const video=document.querySelector('video');document.querySelectorAll('[data-at]').forEach(b=>b.onclick=()=>{video.currentTime=Number(b.dataset.at);video.play().catch(()=>{})});</script></body></html>"""
    for k, v in {
        "TITLE": escape(evidence["title"]),
        "TAKE": escape(evidence["take"]),
        "NOTES": steps,
        "BUTTONS": "".join(buttons),
        "ROUTES": routes,
        "NEEDED": full,
        "DAY": str(proof["first_delivery_day"]),
    }.items():
        pg = pg.replace("__" + k + "__", v)
    if "d02-afternoon-camera" in missing:
        pg=pg.replace("Jump to the work that made it possible.","Larry’s first interview appears on Tuesday 1. He records Alma again off screen on Tuesday 2. Follow the second day’s interview, delivery and transmission.")
    if evidence["take"]=="721-hypothesis":
        base=Path(__file__).resolve().parent.parent/"last-reel"/"epilogues"
        ep={k:json.loads((base/k/"reporter.json").read_text()) for k in ("tuesday","wednesday")}
        assert all(r["source_sha256"]==evidence["source_sha256"] and r["source_day"]==2 for r in ep.values())
        extra="<details><summary>What happened in the two additional epilogue runs?</summary><p>After the same day-two delivery we separately ran the actors once under each rule. The closed-clock Phil woke in the hotel and chose to walk to the depot. The released Phil woke in Pittsburgh on Wednesday. He could help move the couch and chose to phone his sister. She answered.</p><p><a href='../../last-reel/epilogues/tuesday/reporter.json'>Tuesday actor receipt</a> · <a href='../../last-reel/epilogues/wednesday/reporter.json'>Wednesday actor receipt</a></p></details>"
        pg=pg.replace("</aside>",extra+"</aside>")
    (folder / "index.html").write_text(pg)


if __name__ == "__main__":
    build(Path(sys.argv[1]))
