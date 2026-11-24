"""Verify the unmodified source, rendered physical actions, dual-camera geography and offline fallback."""
from __future__ import annotations
import hashlib
import json
import math
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from build_take import build, SOURCE

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE/"evidence"
URL=(HERE/"index.html").as_uri()
checks=[]
errors=[]
requests=[]


def chrome_path():
    choices=[os.environ.get("CHROME_PATH"),"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             shutil.which("google-chrome"),shutil.which("chromium")]
    return next((x for x in choices if x and Path(x).exists()),None)


def check(name,condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def watch(page):
    page.on("request",lambda r: requests.append(r.url) if r.url.startswith(("http:","https:")) else None)
    page.on("pageerror",lambda e: errors.append(str(e)))
    page.on("console",lambda m: errors.append(m.text) if m.type=="error" else None)


def ready(page):
    page.goto(URL)
    page.wait_for_function("typeof window.Rialto3D !== 'undefined'")


def state(page):
    return page.evaluate("Rialto3D.getState()")


def seek(page,i,p=.63):
    return page.evaluate("a=>Rialto3D.seek(...a)",[i,p])


def desktop(browser):
    context=browser.new_context(viewport={"width":1365,"height":820},device_scale_factor=1)
    p=context.new_page();watch(p)
    p.goto((HERE.parent/"index.html").as_uri())
    p.wait_for_function("typeof TuesdayStage3D!=='undefined'")
    p.locator("#recorded").click();p.locator("#take").select_option("rialto-alt")
    p.wait_for_function("typeof Rialto3D!=='undefined'")
    check("The original town recording selector opens a distinct 721 stage",p.url==URL)
    live_source=p.evaluate("window.RialtoTake");raw_source=build()
    check("The browser projection reproduces the source bytes and full request keys",live_source==raw_source and raw_source["sha256"]==hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    check("Nine beats use six venues and contain no model prompts or hidden planning",len(live_source["shots"])==9 and len(set(s["set"] for s in live_source["shots"]))==6 and not any(x in json.dumps(live_source) for x in ['"messages"','"intention"','"full_words_field"','"attempts"']))
    check("Chrome created a working WebGL context",state(p)["renderer"]=="WebGL")
    original=json.loads(SOURCE.read_bytes())
    rows=[]
    for i,shot in enumerate(raw_source["shots"]):
        s=seek(p,i);day=original["days"][shot["day"]-1]
        phase="afternoon" if shot["phase"]=="dawn" else shot["phase"]
        role="reporter" if shot["role"]=="world" else shot["role"]
        call=day[phase][role]
        if shot["kind"]!="receipt":
            source=day["afternoon_state"] if phase=="afternoon" else day["ending"]
            assert s["effect"]==source["effects"][role] and s["action"]==call["decision"]["action"]
        assert s["key"]==call["key"] and s["id"]==shot["id"]
        assert [k for k,v in s["geometry"].items() if v["visible"]]==[s["set"]]
        for actor,pos in s["positions"].items():
            assert math.dist(pos,s["geometry"][s["set"]]["origin"])<7
        rows.append({"id":s["id"],"request_key":s["key"],"set":s["set"],"rendered":s["visible"]})
    check("Every visible action and request key matches the original take; each single shot has one active physical set",len(rows)==9)
    st=seek(p,0,.16);st2=seek(p,0,.55)
    check("Phil's wrist and physical piano keys animate",st["poses"]["Phil"]["wrist"]!=st2["poses"]["Phil"]["wrist"] and st["art"]["keys"]!=st2["art"]["keys"])
    check("Re-seeking reproduces Phil and the complete physical piano state",seek(p,0,.16)["poses"]==st["poses"] and state(p)["art"]==st["art"])
    st=seek(p,1);check("Only Phil occupies the local first-evening depot",st["visible"]==["Phil"] and st["set"]=="depot" and st["action"]=="sit_at_depot")
    st2=seek(p,2,.06);st3=seek(p,2,.40)
    check("Rita physically dances at the separate ballroom in the same source slot",st2["visible"]==["Rita"] and st2["set"]=="ballroom" and st2["positions"]!=st3["positions"] and st["day"]==st2["day"] and st["phase"]==st2["phase"])
    p.locator("#parallel").click();twins=state(p)["comparison"]
    check("The split camera draws disjoint casts sourced from the real simultaneous decisions",[(s["id"],s["visible"]) for s in twins]==[("d01-evening-reporter",["Phil"]),("d01-evening-producer",["Rita"])])
    check("Desktop split appears physically side by side",twins[1]["rect"]["x"]>600 and twins[1]["rect"]["y"]==0)
    p.screenshot(path=EVIDENCE/"parallel-evening.png")
    p.get_by_role("button",name="Phil · Town depot").click();check("The crew strip follows the independently located actor in the same slot",state(p)["id"]=="d01-evening-reporter")
    p.locator("#parallel").click();coach_a=seek(p,3,.05);coach_b=seek(p,3,.48);coach_c=seek(p,3,.94)
    check("A moving physical Pittsburgh coach conceals its passenger until the recorded disembark",coach_a["visible"]==coach_b["visible"]==[] and coach_c["visible"]==["Phil"] and coach_b["bus"]["position"][0]-coach_a["bus"]["position"][0]>4)
    check("The local depot and Pittsburgh terminal occupy distinct stage roots at least 20 metres apart",math.dist(st["geometry"]["depot"]["origin"],st["geometry"]["terminal"]["origin"])>=20)
    st=seek(p,4,.15);st2=seek(p,4,.31)
    check("The Rialto booth holds both independent crew recordings and world character Alma",set(st["visible"])=={"Rita","Larry","Alma"} and st["crew"]["producer"]["action"]=="interview_Alma" and st["crew"]["camera"]["action"]=="film_Alma" and st["art"]["spools"]==st2["art"]["spools"] and st["art"]["cameraRecordingTally"]!=st2["art"]["cameraRecordingTally"])
    p.screenshot(path=EVIDENCE/"rialto-booth.png")
    asleep=seek(p,5);check("Sleeping Phil stays at the remote Pittsburgh terminal",asleep["visible"]==["Phil"] and asleep["poses"]["Phil"]["hip"]<.7 and asleep["set"]=="terminal" and asleep["art"]["closedEyes"])
    reel=seek(p,6);line_a=seek(p,7,.1);line_b=seek(p,7,.6)
    check("Larry delivers a reel and Rita independently transmits at the station",reel["action"]=="deliver_reel" and line_a["action"]=="transmit_interview" and reel["set"]==line_a["set"]=="station" and set(line_a["visible"])=={"Rita","Larry"})
    check("The physical transmission reels and level meters respond over time",line_a["art"]["spools"]!=line_b["art"]["spools"] and line_a["art"]["levels"]!=line_b["art"]["levels"])
    early=seek(p,6,.05);delivered=seek(p,6,.92);same_time=seek(p,7,.92)
    check("The physical reel leaves Larry's hand and reaches a neutral intake tray",early["art"]["intakeReel"] is None and delivered["art"]["intakeReel"] is not None)
    check("Switching between Rita and Larry preserves both performers and the deposited reel at the same slot progress",delivered["positions"]==same_time["positions"] and delivered["art"]==same_time["art"])
    p.locator("#parallel").click();check("The second-evening comparison preserves Pittsburgh and the distinct station",[(v["set"],len(v["visible"])) for v in state(p)["comparison"]]==[("terminal",1),("station",2)])
    p.screenshot(path=EVIDENCE/"parallel-transmission.png")
    end=seek(p,8);obs=json.loads(next(m["content"] for m in original["days"][2]["afternoon"]["reporter"]["messages"] if m["role"]=="user"))["what_you_observe"]
    check("The third dawn contains a physical envelope and the daughter’s exact world-authored reply",end["set"]=="hotel" and end["phase"]=="dawn" and end["action"] is None and end["receipt"]=="I know that voice. Play it again." and bool(end["art"]["envelope"]) and any(end["receipt"] in x for x in obs))
    check("The daughter is offstage; the Tuesday clock and receiving observer remain correct",end["visible"]==["Phil"] and original["days"][1]["ending"]["closed_clock"]=="Tuesday" and "Tuesday" in p.locator("#effect").inner_text() and not state(p)["parallel"])
    p.screenshot(path=EVIDENCE/"receipt.png")
    p.locator('[data-angle=close]').click();close=state(p);p.locator('[data-angle=overhead]').click();above=state(p)
    check("Camera controls change the physical eye without moving the actor or envelope",close["eye"]!=above["eye"] and close["positions"]==above["positions"] and close["art"]==above["art"])
    p.locator("#shots").select_option("0");p.locator("#next").click();p.locator("#prev").click()
    check("The shot selector and previous/next buttons seek correctly",state(p)["index"]==0)
    p.locator("#time").fill("2.5");check("The timeline jumps to a fractional physical beat",state(p)["index"]==2 and abs(state(p)["progress"]-.5)<.001)
    seek(p,1,.99);p.locator("#play").click();p.wait_for_function("Rialto3D.getState().index===2 && Rialto3D.getState().progress>.01");p.locator("#play").click()
    check("Real-time playback crosses a source slot view without skipping it",state(p)["index"]==2 and not state(p)["playing"])
    p.locator("h2").click();p.keyboard.press("ArrowRight");check("Keyboard controls reach the coach arrival",state(p)["index"]==3)
    p.locator("#full").click();p.wait_for_function("!!document.fullscreenElement");p.evaluate("document.exitFullscreen()")
    check("The interactive viewport can enter and leave fullscreen",p.evaluate("!document.fullscreenElement"))
    perf=p.evaluate("""async()=>{Rialto3D.seek(1,.1);Rialto3D.setParallel(true);document.querySelector('#play').click();
      const t=performance.now();let previous=-1,frames=0;while(performance.now()-t<1000){await new Promise(requestAnimationFrame);
      const v=Rialto3D.getState().progress;if(v!==previous){frames++;previous=v;}}
      document.querySelector('#play').click();return {elapsed_ms:Math.round(performance.now()-t),rendered_frames:frames}}""")
    p.goto(URL+"?shot=d01-evening-reporter&view=split&at=.7");p.wait_for_function("window.Rialto3D");
    check("A source-ID deep link opens the correct paired scene and fraction",state(p)["id"]=="d01-evening-reporter" and state(p)["parallel"] and state(p)["progress"]==.7)
    context.close();return rows,perf


def mobile(browser):
    context=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,device_scale_factor=1)
    p=context.new_page();watch(p);ready(p);seek(p,1,.73);p.locator("#parallel").tap()
    pair=state(p)["comparison"]
    check("Portrait stacks both shot cameras and preserves their world positions",pair[1]["rect"]["y"]>110 and pair[1]["rect"]["x"]==0 and pair[0]["visible"]==["Phil"] and pair[1]["visible"]==["Rita"])
    p.screenshot(path=EVIDENCE/"mobile-split.png")
    for width in [390,320]:
        p.set_viewport_size({"width":width,"height":844});p.wait_for_timeout(40)
        check(f"{width}px viewport fits its controls without horizontal overflow",p.evaluate("document.documentElement.scrollWidth<=innerWidth"))
    context.close()


def fallback(pw,exe):
    browser=pw.chromium.launch(headless=True,executable_path=exe,args=["--disable-webgl"])
    p=browser.new_page();p.on("pageerror",lambda e: errors.append(str(e)));ready(p)
    check("WebGL-off devices receive the locally packaged illustrated film",state(p)["renderer"]=="video" and p.locator("#fallback video").is_visible())
    p.locator("#fallback video").evaluate("v=>{v.muted=true;return v.play()}")
    p.wait_for_function("document.querySelector('#fallback video').currentTime>.10")
    check("The offline fallback actually decodes and plays",p.locator("#fallback video").evaluate("v=>v.videoWidth>0"))
    browser.close()


def main():
    EVIDENCE.mkdir(exist_ok=True);exe=chrome_path()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=exe)
        version=browser.version;rows,perf=desktop(browser);mobile(browser);browser.close();fallback(pw,exe)
    check("The interactive browser made zero external HTTP requests and reported zero errors",not requests and not errors)
    report={"checks":checks,"count":len(checks),"take_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),"shots":rows,
            "browser":version,"desktop":{"width":1365,"height":820},"mobile":"Chromium touch/portrait emulation at 390 and 320 CSS px",
            "split_desktop_frame_sample":perf,"network_requests":requests,"browser_errors":errors}
    (EVIDENCE/"verification.json").write_text(json.dumps(report,indent=2)+"\n");print(f"{len(checks)} checks passed",perf)


if __name__=="__main__":
    main()
