"""End-to-end checks in actual Chromium. Run from anywhere; no server or GPU is required."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence"
RUNS = ROOT.parent / "takes" / "q27"
URL = (ROOT / "index.html").as_uri()
state = "TuesdayTown.getState()"
checks = {}
errors = []
requests = []


def check(label, result):
    if not result:
        raise AssertionError(label)
    checks[label] = True


def recorded_page(browser, mobile=False):
    vp = (390, 844) if mobile else (1365, 850)
    context = browser.new_context(viewport={"width": vp[0], "height": vp[1]}, device_scale_factor=1,
                                  is_mobile=mobile, has_touch=mobile)
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: requests.append(r.url) if r.url.startswith(("https:", "http:")) else None)
    page.goto(URL)
    page.wait_for_function("typeof window.TuesdayTown !== 'undefined'")
    return page


def source(name):
    return json.loads((RUNS / name / "seed-701.json").read_text())


def seek(pg, i, progress, role="reporter", framing="close"):
    return pg.evaluate("""([i,p,role,framing])=>{
        TuesdayTown.setCamera({actor:role,framing});
        return TuesdayTown.seek(i,p);
    }""", [i, progress, role, framing])


def manual_controls(pg):
    start = pg.evaluate(state)
    check("Free walk starts with Phil, Rita and Larry", [p["name"] for p in start["subjects"]] == ["Phil", "Rita", "Larry"])
    pg.get_by_role("button", name="Mark the sill").click()
    pg.wait_for_function("TuesdayTown.getState().worldFacts.marked")
    pg.keyboard.down("ArrowRight")
    pg.wait_for_timeout(460)
    pg.keyboard.up("ArrowRight")
    end = pg.evaluate(state)
    check("Held arrow walks continuously", abs(end["position"]["x"] - start["position"]["x"]) > .35)
    pg.locator("#destination").select_option("depot")
    pg.locator("#go").click()
    pg.get_by_role("button", name="Wait for the 1 PM coach").wait_for(timeout=17000)
    pg.get_by_role("button", name="Wait for the 1 PM coach").click()
    pg.get_by_role("button", name="Board the coach").click()
    pg.wait_for_function("TuesdayTown.getState().phase === 'aboard coach'")
    ride = pg.evaluate(state)
    pg.wait_for_function("TuesdayTown.getState().phase === 'arriving in Pittsburgh'")
    arrive = pg.evaluate(state)
    check("Manual trip passes through moving coach in two environments",
          ride["scene"] == "town" and arrive["scene"] == "city" and arrive["place"] == "Pittsburgh" and not ride["subjects"][0]["visible"])
    pg.get_by_role("button", name="Use the payphone").click()
    pg.wait_for_function("TuesdayTown.getState().worldFacts.called_sister")
    pg.get_by_role("button", name="Stay until morning").click()
    pg.wait_for_function("TuesdayTown.getState().day === 2 && TuesdayTown.getState().phase === 'free walk'")
    wake = pg.evaluate(state)
    check("Manual dawn returns to hotel with cleared props",
          wake["place"] == "inn" and wake["clock"] == "6:00 am" and not wake["worldFacts"]["marked"]
          and not wake["worldFacts"]["called_sister"])
    picked = pg.evaluate("""()=>{
      const b=WinterMap.buildings.find(b=>b.id==="inn");
      return WinterArt.landmarkAt(WinterMap.iso({x:b.x+b.w/2,y:b.y+b.d/2},b.h+.15),"town")
    }""")
    check("A tap on the hotel roof resolves to its street entrance", picked == "inn")
    routes = pg.evaluate("""()=>{
      const ids=Object.keys(WinterMap.places).filter(id=>id!=="Pittsburgh");
      let tests=0;
      for(const a of ids)for(const b of ids)for(let j=0;j<3;j++){
        const p=WinterReplay.anchor(a,j),q=WinterReplay.anchor(b,j),way=WinterMap.route(p,q,"town");
        if(WinterMap.distance(way.at(-1),q)>.01)throw Error("Wrong endpoint "+a+" "+b);
        for(let i=0;i<=100;i++)if(!WinterMap.walkable(WinterMap.sample(way,i/100),"town"))throw Error("Collision "+a+" "+b);
        tests++;
      }return tests;
    }""")
    check("All 75 landmark routes reach their targets with sampled collision clearance", routes == 75)
    pg.locator("#expand").click()
    pg.wait_for_function("document.fullscreenElement || document.body.classList.contains('cinema')")
    dims = pg.locator("#town").bounding_box()
    check("Fullscreen occupies the landscape viewport", dims["width"] >= 1360 and dims["height"] >= 845)
    pg.evaluate("document.fullscreenElement ? document.exitFullscreen() : TuesdayTown.setCinematic(false)")


def sources_and_controls(pg):
    pg.get_by_role("button", name="Recorded runs").click()
    check("Default recorded run is the 27B Phil archive", pg.evaluate(state)["archive"].endswith("film-transcript/seed-701.json"))
    opts = pg.locator("#source option").all()
    check("Five authenticated archive choices ship offline", len(opts) == 5)
    for value in [0, 1]:
        pg.locator("#source").select_option(str(value))
        s = pg.evaluate(state)
        check("Original seed-511 archive " + str(value + 1) + " preserves Ellis, Lou and Bea",
              [p["name"] for p in s["subjects"]] == ["Ellis", "Lou", "Bea"])
    pg.locator("#source").select_option("0")
    check("Legacy Lou reply appears verbatim in the event log", "Time to get this radio show rolling" in pg.locator("#events").inner_text())
    pg.locator("#camera-actor").select_option("Lou")
    check("Legacy resident camera captions cite the recorded speaker", pg.locator("#film-speaker").inner_text() == "Lou")
    pg.locator("#next").click()
    check("Next decision advances and pauses", pg.evaluate(state)["index"] == 1 and not pg.evaluate(state)["playing"])
    pg.locator("#prev").click()
    check("Previous decision returns", pg.evaluate(state)["index"] == 0)
    pg.locator("#speed").click()
    pg.wait_for_function("document.getElementById('speed').textContent === '2×'")
    pg.locator("#play").click()
    pg.wait_for_function("TuesdayTown.getState().progress > .05")
    pg.locator("#play").click()
    pg.wait_for_function("!TuesdayTown.getState().playing")
    pg.locator("#scrub").evaluate("(x)=>{x.value=3.48;x.dispatchEvent(new Event('input'))}")
    s = pg.evaluate(state)
    check("Timeline seeks to fractional progress", s["index"] == 3 and abs(s["progress"] - .48) < .001)
    pg.locator("#overview").click()
    check("Overview toggles", pg.evaluate(state)["overview"])
    pg.locator("#overview").click()
    pg.locator("#file").set_input_files(str(RUNS / "neutral-receipts/seed-701.json"))
    pg.wait_for_function("TuesdayTown.getState().source === 'live_model'")
    pg.locator("#camera-actor").select_option("Cal")
    pg.locator("#close-shot").click()
    check("Viewer controls switch to the independently acting cameraman",
          pg.evaluate(state)["cameraActor"] == "Cal")
    s = seek(pg, 6, .82, framing="street")
    check("Neutral JSON import preserves Ellis, June, Cal",
          [p["name"] for p in s["subjects"]] == ["Ellis", "June", "Cal"])
    check("Independent neutral cast remains in town after Ellis reaches Pittsburgh",
          [(p["scene"], p["at"]) for p in s["subjects"]] == [("city", "Pittsburgh"), ("town", "inn"), ("town", "square")])
    pg.locator("#file").set_input_files({"name": "invalid.json", "mimeType": "application/json", "buffer": b'{"events":[]}'})
    pg.locator("#error").wait_for()
    check("Invalid import leaves the previous trace and playhead intact",
          pg.evaluate(state)["index"] == 6 and "events array" in pg.locator("#error").inner_text())


def film_frames(pg):
    pg.set_viewport_size({"width": 1280, "height": 720})
    pg.evaluate("(raw)=>TuesdayTown.loadTrace(raw)", source("film-transcript"))
    pg.evaluate("TuesdayTown.setCinematic(true,{captions:false})")
    for index, role, key, expected in [(7, "reporter", "phone", ("called_sister", True)),
                                       (13, "reporter", "cross", ("marked", True)),
                                       (1, "camera", "festival-camera", ("camera_battery", 0))]:
        s = seek(pg, index, .84, role)
        check("Verified close-up " + key,
              s["framing"] == "close" and s["worldFacts"][expected[0]] == expected[1])
        pg.screenshot(path=EVIDENCE / ("q27-" + key + ".png"))
    first = pg.locator("#town").screenshot()
    pg.wait_for_timeout(240)
    seek(pg, 1, .84, "camera")
    check("Seeking the same shot reproduces identical canvas pixels", first == pg.locator("#town").screenshot())
    before = seek(pg, 13, .40)
    after = seek(pg, 13, .86)
    check("Window cross appears after the action", not before["worldFacts"]["marked"] and after["worldFacts"]["marked"])
    bus = seek(pg, 6, .54, framing="street")
    pg.screenshot(path=EVIDENCE / "q27-coach.png")
    city = seek(pg, 6, .82, framing="street")
    previous = seek(pg, 8, .01, framing="street")
    morning = seek(pg, 8, .22)
    pg.screenshot(path=EVIDENCE / "q27-hotel-return.png")
    check("Recorded coach leaves town and the date loops after a genuine Pittsburgh evening",
          bus["phase"] == "aboard coach" and city["heroScene"] == "city" and previous["heroScene"] == "city"
          and previous["day"] == 2 and morning["cameraPlace"] == "inn" and morning["day"] == 3)
    pg.evaluate("(raw)=>TuesdayTown.loadTrace(raw)", source("film-receipts"))
    s = seek(pg, 9, .82)
    pg.screenshot(path=EVIDENCE / "q27-diner-plates.png")
    check("Diner rack counts follow the two recorded clear-table actions", s["worldFacts"]["dishes"] == 1
          and seek(pg, 10, .82)["worldFacts"]["dishes"] == 0)
    other = seek(pg, 10, .84, "camera")
    check("Camera follows a resident while reporter account is preserved", other["actor"] == "Phil"
          and other["cameraActor"] == "Larry" and other["cameraPlace"] == "square" and other["place"] == "diner")
    # The live host strips private observations and model reasoning before streaming.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT.parent / "story"))
    from audit import pack_run
    packed = pack_run(source("film-transcript"))
    pg.evaluate("(raw)=>TuesdayTown.loadTrace(raw)", packed)
    compact_early, compact_late = seek(pg, 13, .40), seek(pg, 13, .86)
    check("Actual live-host projection retains the pencil-mark transition and hides private fields",
          compact_early["worldFacts"] == before["worldFacts"] and compact_late["worldFacts"] == after["worldFacts"]
          and "positions" not in compact_late["worldFacts"])
    return hashlib.sha256(first).hexdigest()


def live(pg):
    run = source("film-transcript")
    first = {**run, "events": run["events"][:1]}
    pg.evaluate("(raw)=>TuesdayTown.loadTrace(raw)", first)
    s = pg.evaluate("TuesdayTown.play()")
    check("Live play starts the very first slot immediately", s["playing"] and s["index"] == 0)
    pg.wait_for_function("TuesdayTown.getState().progress > .02")
    p = pg.evaluate(state)["progress"]
    check("Repeat live play preserves current progress", pg.evaluate("TuesdayTown.play()")["progress"] >= p)
    pg.evaluate("TuesdayTown.seek(0,1)")
    check("Arming live follow at the completed tail stays at the tail", not pg.evaluate("TuesdayTown.play()")["playing"])
    update = {**run, "events": run["events"][:2]}
    s = pg.evaluate("(raw)=>TuesdayTown.appendOrRefresh(raw,{follow:true})", update)
    check("Growing live trace resumes at the committed tail", s["index"] == 0 and s["progress"] == 1
          and s["total"] == 2 and s["playing"])
    pg.wait_for_function("TuesdayTown.getState().index === 1")
    update["events"][0] = {**update["events"][0], "effect": "Changed receipt."}
    result = pg.evaluate("""raw=>{try {TuesdayTown.appendOrRefresh(raw);return ""} catch(e){return e.message}}""", update)
    check("Live trace rejects a rewritten committed decision", "changed in the live update" in result)


    pg.evaluate("(raw)=>TuesdayTown.loadTrace(raw)", first)
    rows = run["events"][1:4]
    pg.evaluate("(rows)=>TuesdayTown.appendEvents(rows,{offset:1})", rows)
    check("Instant append retry is idempotent", pg.evaluate(
        "(rows)=>TuesdayTown.appendEvents(rows,{offset:1}).total", rows) == 4)
    bad = [{**run["events"][4], "id": run["events"][0]["id"]}]
    error = pg.evaluate("""rows=>{try{TuesdayTown.appendEvents(rows,{offset:4})}
                     catch(e){return e.message}}""", bad)
    check("Invalid delta does not partially commit", "already occurs" in error and pg.evaluate(state)["total"] == 4)
    check("Delta retries may overlap a previously delivered prefix", pg.evaluate(
        "(rows)=>TuesdayTown.appendEvents(rows,{offset:3}).total", run["events"][3:6]) == 6)


def v2_fixture(pg):
    # A minimal cue grounded in the real input schema isolates the case of a producer
    # patching an empty return while all characters are in different places.
    event = source("film-transcript")["events"][7]
    event["decision"] = {"action":"look_around","words":""}
    event["cast"][0]["decision"] = {"action":"patch_reporter_line","words":""}
    bulletin = {"channel":"empty_selected_return","source_role":None,"source_place":None,
                "selected_by":"Rita","source_ids":[event["cast"][0]["id"],event["id"]]}
    event["visible_before"] = {"marked": False, "camera_battery": 0}
    event["visible_after"] = dict(event["visible_before"])
    event["bulletin"] = bulletin
    pg.evaluate("(row)=>TuesdayTown.loadTrace({protagonist:'Phil',source:'injected_fixture',events:[row]})", event)
    before, after = seek(pg, 0, .42, "producer"), seek(pg, 0, .85, "producer")
    check("V2 compact 7 PM fixture reveals the chosen empty return only after resolution",
          "bulletin" not in before["worldFacts"] and after["worldFacts"]["bulletin"]["channel"] == "empty_selected_return"
          and after["cameraActor"] == "Rita")
    check("Fixture source label distinguishes injected decisions", pg.locator("#mode-label").inner_text() == "FIXTURE REPLAY")
    metadata_event = dict(event)
    metadata_event.pop("actor")
    metadata_event["cast"] = [{k:v for k,v in n.items() if k not in ("actor","clock","day")} for n in event["cast"]]
    mapped = pg.evaluate("""e=>TuesdayTown.loadTrace({cast_names:{reporter:"Phil",producer:"Rita",camera:"Larry"},
                          source:"injected_fixture",events:[e]})""", metadata_event)
    check("Header-only identities and inherited slot times resolve correctly",
          [a["name"] for a in mapped["subjects"]] == ["Phil","Rita","Larry"])
    named_run = {"protagonist":"Phil", "source":"injected_fixture", "municipality":"Punxsutawney", "events":[event]}
    pg.evaluate("(raw)=>TuesdayTown.loadTrace(raw)", named_run)
    seek(pg, 0, .83, "producer")
    check("A recording can name Punxsutawney on its own HUD",
          pg.locator("#scene-name").inner_text() == "Punxsutawney, PA")
    seek(pg, 0, .83, "reporter")
    check("Pittsburgh keeps its destination identity for a named town",
          pg.locator("#scene-name").inner_text() == "Pittsburgh, PA")
    if os.getenv("V2_TRACE"):
        raw = json.loads(Path(os.environ["V2_TRACE"]).read_text())
        page = pg
        page.evaluate("(raw)=>TuesdayTown.loadTrace(raw)", raw)
        count = 0
        for i, row in enumerate(raw["events"]):
            bulletin = row.get("world_after",{}).get("bulletin")
            if row["clock"] == "7:00 pm" and bulletin:
                s = seek(page, i, .91, "producer")
                assert s["worldFacts"]["bulletin"]["channel"] == bulletin["channel"]
                count += 1
        check("All logged 7 PM results match the external V2 "+raw["source"]+" take", count > 0)


def mobile(browser):
    pg = recorded_page(browser, mobile=True)
    check("390-pixel page has no horizontal scroll",
          pg.evaluate("document.documentElement.scrollWidth === innerWidth"))
    pg.locator("[data-dir=right]").wait_for()
    start = pg.evaluate(state)["position"]
    pad = pg.locator("[data-dir=right]").bounding_box()
    pg.mouse.move(pad["x"] + pad["width"]/2, pad["y"] + pad["height"]/2)
    pg.mouse.down()
    pg.wait_for_timeout(380)
    pg.mouse.up()
    s = pg.evaluate(state)
    check("Narrow-screen directional pad moves the protagonist", abs(s["position"]["x"] - start["x"]) > .2)
    pg.screenshot(path=EVIDENCE / "mobile-town.png")
    pg.evaluate("(raw)=>TuesdayTown.loadTrace(raw)", source("film-transcript"))
    pg.evaluate("TuesdayTown.setCinematic(true,{captions:false})")
    seek(pg, 7, .84)
    pg.screenshot(path=EVIDENCE / "mobile-interior.png")
    size = pg.locator("#town").bounding_box()
    check("Portrait cinematic fills the viewport", size["width"] == 390 and size["height"] == 844)
    pg.context.close()


def frame_pacing(pg):
    pg.bring_to_front()
    pg.evaluate("(raw)=>TuesdayTown.loadTrace(raw)", source("film-transcript"))
    pg.evaluate("TuesdayTown.setCinematic(true,{captions:false})")
    samples = {}
    for name, slot, progress, framing in [("moving_coach",6,.40,"street"),
                                         ("terminal_phone",7,.21,"close")]:
        seek(pg, slot, progress, framing=framing)
        samples[name] = pg.evaluate("""()=>new Promise(resolve=>{
          const start=performance.now(),frames=[];let lastDraw=start,lastProgress=null,ticks=0;
          TuesdayTown.play();
          function tick(now){
            ticks++;
            const s=TuesdayTown.getState();
            if(s.progress!==lastProgress){if(lastProgress!==null)frames.push(now-lastDraw);lastDraw=now;lastProgress=s.progress;}
            if(now-start<1800){requestAnimationFrame(tick);return;}
            TuesdayTown.seek(s.index,s.progress);
            const sorted=frames.slice().sort((a,b)=>a-b);
            resolve({duration_ms:Math.round(now-start),display_callbacks:ticks,
                   observed_playhead_updates:frames.length,
                   updates_per_second:+(1000*frames.length/(now-start)).toFixed(1),
                   p95_update_gap_ms:+sorted[Math.floor(sorted.length*.95)].toFixed(1)});
          }
          requestAnimationFrame(tick);
        })""")
        check("Actual 27B "+name+" playback advances across frames", samples[name]["observed_playhead_updates"] > 10)
    return samples


def workload(pg):
    perf = pg.evaluate("""()=>{
      const clocks=WinterReplay.clocks;
      const base={actor:"Test Subject",origin:"inn",place:"inn",decision:{action:"look_around",words:""},effect:""};
      const raw={source:"synthetic_benchmark",events:Array.from({length:20000},(_,i)=>({
        ...base,id:"bench-"+i,day:1+Math.floor(i/4),clock:clocks[i%4]
      }))};
      let t=performance.now();TuesdayTown.loadTrace(raw);const load=performance.now()-t;
      const durations=[];
      for(let i=0;i<100;i++){t=performance.now();TuesdayTown.seek((i*19331)%20000,.84);durations.push(performance.now()-t);}
      durations.sort((a,b)=>a-b);
      return {decisions:20000,synthetic:true,repeated_seeks:100,load_ms:Math.round(load),
              median_seek_ms:+durations[50].toFixed(2),p95_seek_ms:+durations[95].toFixed(2),
              ledger_rows:document.querySelectorAll("#events article").length};
    }""")
    check("Twenty-thousand-slot synthetic take retains a bounded DOM ledger", 0 < perf["ledger_rows"] <= 11)
    return perf


def main():
    EVIDENCE.mkdir(exist_ok=True)
    chrome = os.environ.get("CHROME_PATH") or next((str(p) for p in [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path(shutil.which("google-chrome") or "/unavailable"), Path(shutil.which("chromium") or "/unavailable")
    ] if p.is_file()), None)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chrome, headless=True)
        pg = recorded_page(browser)
        pg.screenshot(path=EVIDENCE / "first-view.png")
        manual_controls(pg)
        sources_and_controls(pg)
        frame_hash = film_frames(pg)
        live(pg)
        v2_fixture(pg)
        mobile(browser)
        pacing = frame_pacing(pg)
        perf = workload(pg)
        check("Actual Chromium reported zero page errors", not errors)
        check("Static viewer issued zero HTTP requests", not requests)
        result = {"browser": browser.version, "checks": checks, "performance": perf, "playback_1280x720": pacing,
                  "festival_canvas_screenshot_sha256": frame_hash, "errors": errors, "http_requests": requests}
        browser.close()
    (EVIDENCE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"{len(checks)} browser checks passed. {perf}")


if __name__ == "__main__":
    main()
