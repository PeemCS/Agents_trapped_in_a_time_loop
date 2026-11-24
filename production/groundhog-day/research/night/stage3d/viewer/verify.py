"""Exercise the offline 3D viewer and compare its samples to the shipped native USD tracks."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REHEARSAL = HERE.parent / "rehearsal"
TAKES = HERE.parents[1] / "takes" / "q27"
URL = (HERE / "index.html").as_uri()
API = "TuesdayStage3D"
checks = {}
errors = []
network = []
evidence = HERE / "evidence"


def check(title, condition):
    if not condition:
        raise AssertionError(title)
    checks[title] = True


def chrome_path():
    candidates = [os.environ.get("CHROME_PATH"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  shutil.which("google-chrome"), shutil.which("chromium")]
    return next((p for p in candidates if p and Path(p).is_file()), None)


def get(pg):
    return pg.evaluate("TuesdayStage3D.getState()")


def page(browser, mobile=False):
    context = browser.new_context(viewport={"width": 390 if mobile else 1365, "height": 844 if mobile else 820},
                                  has_touch=mobile,is_mobile=mobile,device_scale_factor=1)
    pg=context.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type=="error" else None)
    pg.on("request", lambda r: network.append(r.url) if r.url.startswith(("https:","http:")) else None)
    pg.goto(URL)
    pg.wait_for_function("typeof window.TuesdayStage3D !== 'undefined'")
    check(("Mobile" if mobile else "Desktop")+" created a real WebGL scene", get(pg)["renderer"] == "WebGL")
    return pg


def atomic_pos(pg):
    return get(pg)["subjects"][0]


def walk(pg):
    s=get(pg)
    check("A native local USDZ and the primary town are linked",pg.locator('a[download]').get_attribute("href").endswith(".usdz")
          and pg.locator('nav a').first.get_attribute("href").endswith("visual/index.html"))
    check("Starting subject is the directly controlled Phil",s["mode"]=="walk" and s["source"]=="manual" and s["actor"]=="Phil")
    check("All three real 3D character roots start on the correct canonical anchors",
          len(s["stats"]["rigs"])==3 and all(abs(r["position"][0]-p["x"])<1e-7 and abs(r["position"][2]-p["z"])<1e-7 for r,p in zip(s["stats"]["rigs"],s["subjects"])))
    check("Only the town stage is visible on arrival", s["stats"]["visibleSets"]==["town"])
    pg.screenshot(path=evidence/"desktop-town.png")
    pg.locator("#interact").click()
    pg.wait_for_function("TuesdayStage3D.getState().facts.marked")
    a=atomic_pos(pg)
    pg.keyboard.down("d")
    pg.wait_for_function("([x,z])=>Math.hypot(TuesdayStage3D.getState().subjects[0].x-x,TuesdayStage3D.getState().subjects[0].z-z)>.25", arg=[a["x"],a["z"]], timeout=11000)
    pg.keyboard.up("d")
    check("WASD moves a rig across the depth plane",atomic_pos(pg)["moving"] or math.hypot(atomic_pos(pg)["x"]-a["x"],atomic_pos(pg)["z"]-a["z"])>.25)
    pg.get_by_role("button",name="Orbit",exact=True).click()
    old=get(pg)["camera"]
    box=pg.locator("#view").bounding_box();x=box["x"]+box["width"]*.55;y=box["y"]+box["height"]*.45
    pg.mouse.move(x,y);pg.mouse.down();pg.mouse.move(x+94,y+19,steps=6);pg.mouse.up()
    new=get(pg)["camera"]
    check("Dragging orbits the physical camera without teleporting the actor",new["type"]=="orbit" and abs(old["yaw"]-new["yaw"])>.45)
    pg.mouse.wheel(0,-175)
    pg.wait_for_function("TuesdayStage3D.getState().camera.zoom < 1")
    check("Scroll changes optical distance", get(pg)["camera"]["zoom"] < 1)
    pg.get_by_role("button",name="Aerial",exact=True).click()
    eye=get(pg)["camera"]["eye"]
    check("Aerial camera changes both height and viewing angle",eye[1]>12 and get(pg)["camera"]["pitch"]>.8)
    pg.screenshot(path=evidence/"aerial-town.png")
    dressed=pg.locator("#view").screenshot()
    pg.get_by_role("button",name="Dressed set",exact=True).click()
    check("Original USD blocking can be isolated",not get(pg)["dressed"] and pg.locator("#view").screenshot()!=dressed)
    pg.get_by_role("button",name="USD blocking",exact=True).click()
    pg.get_by_role("button",name="Follow",exact=True).click()
    # Hit the hotel facade via the actual perspective projection and pointer picking.
    point=pg.evaluate("()=>TuesdayStage3D.projectWorld(5.15,1.02,7.53)")
    rect=pg.locator("#view").bounding_box()
    pg.mouse.click(rect["x"]+point["x"],rect["y"]+point["y"])
    pg.wait_for_function("document.getElementById('feedback').textContent.includes('Hearthside Hotel')",timeout=7000)
    check("Clicking physical building geometry routes to its entrance",point["visible"])
    pg.locator("#dest").select_option("depot");pg.locator("#go").click()
    pg.wait_for_function("document.getElementById('interact').textContent === 'Wait for the 1 PM coach'",timeout=24000)
    pg.locator("#interact").click()
    pg.wait_for_function("document.getElementById('interact').textContent === 'Board the coach'")
    pg.locator("#interact").click()
    pg.wait_for_function("TuesdayStage3D.getState().phase==='aboard coach'",timeout=11000)
    ride=get(pg)
    check("Manual bus hides Phil inside the moving physical coach",ride["stats"]["coach"] and
          not ride["stats"]["rigs"][0]["visible"] and ride["bus"]["scene"]=="town")
    pg.wait_for_function("TuesdayStage3D.getState().scene==='city'",timeout=13000)
    city=get(pg)
    check("Pittsburgh occupies a separate stage and town actors remain in town",city["stats"]["visibleSets"]==["city"]
          and city["subjects"][0]["x"]>39 and city["subjects"][1]["scene"]=="town" and not city["stats"]["rigs"][1]["visible"])
    pg.wait_for_function("document.getElementById('interact').textContent==='Use the payphone'",timeout=12000)
    pg.locator("#interact").click()
    pg.wait_for_function("document.getElementById('interact').textContent==='Stay until morning'")
    pg.locator("#interact").click()
    pg.wait_for_function("TuesdayStage3D.getState().day === 2 && TuesdayStage3D.getState().phase === 'free walk'",timeout=12000)
    morning=get(pg)
    check("Next dawn resets location, time and the pencil mark",morning["scene"]=="town" and morning["clock"]=="6:00 am"
          and not morning["facts"]["marked"] and not morning["facts"]["called_sister"])


def extract_track(source,prim,attribute):
    node=source.index('def Xform "'+prim+'" {')
    hit=re.search(re.escape(attribute)+r'\.timeSamples\s*=\s*\{(.*?)\n\}',source[node:],re.S)
    assert hit
    rows={}
    for line in hit.group(1).strip().splitlines():
        key,value=line.strip().rstrip(",").split(":",1);key=float(key)
        if key.is_integer():
            rows[int(key)]=[float(v) for v in value.strip(" ()").split(",")]
    return rows


def geometry_clearance(pg):
    result=pg.evaluate("""()=>{
      const runs=[false,true].map(dressed=>{
        const hits=new Set();
        for(let i=0;i<=2000;i++){
          const f=.38+.51*i/2000,move=WinterReplay.move({origin:"inn",place:"Pittsburgh"},f);
          if(!move.bus)continue;
          const b=move.bus.pos,theta=Math.atan2(b.dy??0,b.dx??1);
          const hx=Math.abs(Math.cos(theta))*.97+Math.abs(Math.sin(theta))*.356;
          const hz=Math.abs(Math.sin(theta))*.97+Math.abs(Math.cos(theta))*.356;
          TownStagePlacement.buildings(move.scene,dressed).forEach((box,j)=>{
            if(b.x+hx>box.x&&b.x-hx<box.x+box.w&&b.y+hz>box.y&&b.y-hz<box.y+box.d)hits.add(move.scene+"/"+(box.id||box.kind+j));
          });
        }
        return [...hits];
      });
      const a={x:11.2,y:12},b={x:3,y:12},route=TownStagePlacement.route(a,b,"city",true);
      let clear=true;for(let i=0;i<=100;i++)if(!TownStagePlacement.walkable(WinterMap.sample(route,i/100),"city",true))clear=false;
      return {native_proxy_overlaps:runs[0],dressed_proxy_overlaps:runs[1],coach_hull_samples:2001,
        continuous_native_all:TownStagePlacement.sweptCoach(false),continuous_dressed_all:TownStagePlacement.sweptCoach(true),
        tested_dressed_obstacles:["town","city"].reduce((n,k)=>n+TownStagePlacement.coachObstacles(k,true).length,0),
        corrected_street_walk:clear&&WinterMap.distance(route.at(-1),b)<.01};
    }""")
    check("Expanded coach hull clears every building in the dressed set at 2,001 samples",
          result["dressed_proxy_overlaps"]==[] and sorted(result["native_proxy_overlaps"])==["city/shop5","town/house8"])
    check("Direct navigation reaches the corrected Pittsburgh street without intersecting the moved cafe",result["corrected_street_walk"])
    check("Continuous swept coach envelope clears buildings, lamps, benches, conifers and the payphone on every travel leg",
          result["continuous_dressed_all"]==[] and {hit["obstacle"] for hit in result["continuous_native_all"]}=={"town/house8","city/shop5","city/Payphone"})
    paths=pg.evaluate("""()=>{
      const ids=Object.keys(WinterMap.places).filter(k=>k!=="Pittsburgh");let n=0;
      for(const a of ids)for(const b of ids)for(let j=0;j<3;j++){
        const x=WinterReplay.anchor(a,j),y=WinterReplay.anchor(b,j),p=TownStagePlacement.route(x,y,"town",true);
        if(WinterMap.distance(y,p.at(-1))>.01)throw Error("unreachable "+a+" to "+b);
        for(let f=0;f<=80;f++)if(!TownStagePlacement.walkable(WinterMap.sample(p,f/80),"town",true))throw Error("walk collision");
        n++;
      }return n;
    }""")
    check("All 75 dressed town anchor routes clear both buildings and practical props",paths==75)
    return result


def stage_parity(pg):
    native=(REHEARSAL/"another-tuesday.usda").read_text()
    manifest=json.loads((REHEARSAL/"shot-manifest.json").read_text())
    path=TAKES/"film-transcript/seed-701.json"
    raw=json.loads(path.read_text())
    check("Playback input matches the performance hash embedded in the native export",
          hashlib.sha256(path.read_bytes()).hexdigest()==manifest["source_sha256"])
    check("The active runtime geometry fingerprints the actual shipped USDA",get(pg)["actualStageSHA256"]==hashlib.sha256(native.encode()).hexdigest())
    pg.evaluate("(r)=>TuesdayStage3D.loadTrace(r)",raw)
    pg.evaluate("TuesdayStage3D.setCamera('follow')")
    # The independent reference below is the already-shipped native stage, not a second route sampler.
    samples=pg.evaluate("""r=>{
        const t=WinterReplay.normalize(r),out=[];
        for(let slot=4;slot<10;slot++)for(let tick=0;tick<96;tick++){
          const w=WinterReplay.at(t,slot,tick/95);
          const p=(row)=>[row.pos.x+TUESDAY_STAGE.sets[row.scene].offset[0],0,row.pos.y];
          out.push({actors:w.people.map(p),coach:w.bus?[w.bus.pos.x+TUESDAY_STAGE.sets[w.bus.scene].offset[0],.4,w.bus.pos.y]:[0,-20,0]});
        }return out;
    }""",raw)
    tracks=[extract_track(native,n,"xformOp:translate") for n in ("Phil","Rita","Larry","Coach")]
    maximum=0
    for frame,s in enumerate(samples):
        pairs=list(zip(tracks[:3],s["actors"]))+[(tracks[3],s["coach"])]
        for track,actual in pairs:
            maximum=max(maximum,max(abs(a-b) for a,b in zip(track[frame],actual)))
    check("All 2,304 actor and vehicle native transform samples match within USD text precision",len(samples)==576 and maximum<.000012)
    model_meta={"native_frames":len(samples),"position_samples":len(samples)*4,"max_component_difference_metres":round(maximum,8),
                "usd_sha256":get(pg)["actualStageSHA256"],"take_sha256":manifest["source_sha256"]}
    for slot,p in [(4,.22),(5,.35),(6,.37),(6,.54),(6,.82),(7,.85),(8,.06),(8,.22),(9,.81)]:
        s=pg.evaluate("([i,p])=>TuesdayStage3D.seek(i,p)",[slot,p])
        for subject,rig in zip(s["subjects"],s["stats"]["rigs"]):
            assert abs(subject["x"]-rig["position"][0])<1e-6 and abs(subject["z"]-rig["position"][2])<1e-6
        if slot==6 and p==.54:
            pg.screenshot(path=evidence/"recorded-coach.png")
            check("Recorded coach origin uses the town set",s["phase"]=="aboard coach" and s["scene"]=="town")
        if slot==6 and p==.82:check("Recorded coach arrival uses the Pittsburgh set",s["scene"]=="city" and s["stats"]["coach"][0]>41)
        if slot==7 and p==.85:
            pg.screenshot(path=evidence/"recorded-pittsburgh.png")
            check("The on-screen payphone take retains the model's own words",s["facts"]["called_sister"] and "moving" not in s["phase"]
                  and "Wednesday" in pg.locator("#subtitle").inner_text())
        if slot==8 and p==.06: check("The previous evening remains in Pittsburgh at the beginning of the reset",s["scene"]=="city" and s["day"]==2)
        if slot==8 and p==.22:
            pg.screenshot(path=evidence/"recorded-dawn.png")
            check("Dawn resolves to the hotel after the set change",s["scene"]=="town" and s["day"]==3 and not pg.locator("#alarm").is_hidden())
    check("Actual Three.js mesh roots at nine witness frames match their rendered receipt positions",True)
    for t in [.42,.46,.50,.54,.58,.72,.82]:
        s=pg.evaluate("p=>TuesdayStage3D.seek(6,p)",t)
        bounds=s["stats"]["coachScreen"]
        assert 0 < bounds["left"] < bounds["right"] < 1 and 0 < bounds["top"] < bounds["bottom"] < 1
        assert .06 < bounds["right"]-bounds["left"] < .82
    check("The entire moving vehicle stays framed at seven town and Pittsburgh witness positions",True)
    for positions in [[.515,.54,.56,.60,.64,.665],[.69,.72,.75,.79,.82,.86]]:
        bearings=[pg.evaluate("p=>TuesdayStage3D.seek(6,p).camera.bearing",p) for p in positions]
        assert max(bearings)-min(bearings)<.00001
    check("Coach tracking holds a stable lens for each continuous straight road leg",True)
    s=pg.evaluate("TuesdayStage3D.seek(7,.85)")
    check("Dressed evening composition releases the unobserved parked coach", s["bus"] is not None and s["stats"]["coach"] is None)
    s=pg.evaluate("TuesdayStage3D.setDressing(false)")
    check("The native blocking toggle restores the original parked coach transform",s["stats"]["coach"] is not None)
    pg.evaluate("TuesdayStage3D.setDressing(true)")
    s=pg.evaluate("()=>{TuesdayStage3D.seek(6,.84);return TuesdayStage3D.follow('camera')}")
    check("Larry's independent camera shows the town while Phil is physically in Pittsburgh",s["actor"]=="Phil" and s["subject"]=="Larry" and s["scene"]=="town"
          and s["subjects"][0]["scene"]=="city" and not s["stats"]["rigs"][0]["visible"])
    pg.locator("#file").set_input_files(str(TAKES/"neutral-receipts/seed-701.json"))
    pg.wait_for_function("TuesdayStage3D.getState().actor==='Ellis'")
    s=get(pg)
    check("Local JSON import preserves neutral identities", [p["name"] for p in s["subjects"]]==["Ellis","June","Cal"])
    pg.locator("#file").set_input_files({"name":"bad.json","mimeType":"application/json","buffer":b"{}"})
    pg.locator("#error").wait_for()
    check("Invalid JSON preserves the prior performance",get(pg)["actor"]=="Ellis")
    pg.locator("#take").select_option("0");s=get(pg)
    check("Legacy playback retains Ellis, Lou and Bea", [p["name"] for p in s["subjects"]]==["Ellis","Lou","Bea"])
    badge=HERE.parents[1]/"takes/badges/film/seed-721.json"
    badge_raw=json.loads(badge.read_text())
    check("Badge validation uses a real completed 27B model trace",badge_raw["source"]=="live_model" and badge_raw["status"]=="complete")
    pg.evaluate("r=>TuesdayStage3D.loadTrace(r)",badge_raw)
    pg.evaluate("TuesdayStage3D.follow('producer')")
    s=pg.evaluate("TuesdayStage3D.seek(15,.84)")
    check("The named Punxsutawney recording shows Rita's real portable switcher channel",
          s["municipality"]=="Punxsutawney" and pg.locator("#municipality").inner_text()=="Punxsutawney, PA"
          and s["subject"]=="Rita" and s["stats"]["visibleSwitcher"]=="producer"
          and s["facts"]["bulletin"]["channel"]=="camera_take" and "CAMERA TAPE" in pg.locator("#event-id").inner_text()
          and pg.locator("#monitor").is_visible() and "CAMERA TAPE" in pg.locator("#monitor").inner_text())
    pg.screenshot(path=evidence/"punxsutawney-switcher.png")
    pg.evaluate("TuesdayStage3D.setCinematic(true,{captions:false})")
    s=pg.evaluate("TuesdayStage3D.seek(15,.84)")
    check("Cinematic frames fill the viewport with switchable captions",s["cinematic"] and pg.locator("#subtitle").is_hidden()
          and pg.locator("#view").bounding_box()["height"]==820 and pg.locator("header").is_hidden())
    initial=pg.locator("#view").screenshot()
    pg.evaluate("TuesdayStage3D.seek(15,.84)")
    check("A repeated stationary camera seek yields identical pixels",initial==pg.locator("#view").screenshot())
    pg.evaluate("TuesdayStage3D.setCinematic(false)")
    return model_meta


def wardrobe(pg):
    model=HERE/"assets/field-coat.glb"
    film=json.loads((TAKES/"film-transcript/seed-701.json").read_text())
    pg.evaluate("r=>TuesdayStage3D.loadTrace(r)",film)
    s=pg.evaluate("TuesdayStage3D.seek(13,.86)")
    initial=s["stats"]["rigs"][0]["position"]
    pg.locator("#asset-file").set_input_files(str(model))
    pg.wait_for_function("TuesdayStage3D.getState().stats.rigs[0].asset==='field-coat.glb'")
    changed=get(pg)
    check("The real GLB loader replaces the reporter on the identical USD role transform",
          changed["stats"]["rigs"][0]["position"]==initial and changed["stats"]["rigs"][0]["assetClip"]=="Idle"
          and pg.locator("#asset").inner_text()=="Reset mesh")
    pg.screenshot(path=evidence/"field-coat-binding.png")
    moving=pg.evaluate("TuesdayStage3D.seek(6,.22)")
    check("A source movement switches the replacement GLB to its embedded Walk animation",
          moving["subjects"][0]["moving"] and moving["stats"]["rigs"][0]["assetClip"]=="Walk")
    pg.evaluate("TuesdayStage3D.setDressing(false)")
    check("The baseline proxy is available while a custom performer is installed",get(pg)["stats"]["rigs"][0]["asset"] is None)
    pg.evaluate("TuesdayStage3D.setDressing(true)")
    pg.locator("#file").set_input_files(str(TAKES/"neutral-receipts/seed-701.json"))
    pg.wait_for_function("TuesdayStage3D.getState().actor==='Ellis'")
    check("Uploaded Phil wardrobe does not relabel or reskin neutral Ellis",get(pg)["stats"]["rigs"][0]["asset"] is None)
    pg.evaluate("r=>TuesdayStage3D.loadTrace(r)",film)
    check("Returning to Phil recovers only his bound asset",get(pg)["stats"]["rigs"][0]["asset"]=="field-coat.glb")
    blob=model.read_bytes();length=struct.unpack_from("<I",blob,12)[0]
    doc=json.loads(blob[20:20+length]);doc["images"]=[{"uri":"relative-external-texture.png"}]
    scene=json.dumps(doc,separators=(",",":")).encode();scene+=b" "*((-len(scene))%4);tail=blob[20+length:]
    bad=b"glTF"+struct.pack("<II",2,20+len(scene)+len(tail))+struct.pack("<I4s",len(scene),b"JSON")+scene+tail
    pg.locator("#asset-file").set_input_files({"name":"external.glb","mimeType":"model/gltf-binary","buffer":bad})
    pg.locator("#error").wait_for()
    check("An external-resource GLB is rejected before loading and preserves the installed cast",
          "Embed textures" in pg.locator("#error").inner_text() and get(pg)["stats"]["rigs"][0]["asset"]=="field-coat.glb")
    enc=base64.b64encode(blob).decode()
    winner=pg.evaluate("""async encoded=>{
      const data=Uint8Array.from(atob(encoded),x=>x.charCodeAt(0));let release;
      const slow={name:"older.glb",size:data.length,arrayBuffer:()=>new Promise(resolve=>{release=resolve;})};
      const old=TuesdayStage3D.replaceActor(slow);
      await TuesdayStage3D.replaceActor(new File([data],"newer.glb"));
      release(data.slice().buffer);await old;
      return TuesdayStage3D.getState().stats.rigs[0].asset;
    }""",enc)
    check("A slower earlier GLB upload cannot overwrite a newer performer",winner=="newer.glb")
    pg.locator("#asset").click()
    check("Reset mesh recovers the native rig without rewinding the take",get(pg)["stats"]["rigs"][0]["asset"] is None
          and get(pg)["actor"]=="Phil" and pg.locator("#error").is_hidden())


def mobile(pg):
    check("390px layout has no horizontal overflow",pg.evaluate("document.documentElement.scrollWidth===innerWidth"))
    btn=pg.locator('[data-direction="right"]');box=btn.bounding_box();start=atomic_pos(pg)
    pg.mouse.move(box["x"]+box["width"]/2,box["y"]+box["height"]/2);pg.mouse.down()
    pg.wait_for_function("x=>Math.abs(TuesdayStage3D.getState().subjects[0].x-x)>.16",arg=start["x"],timeout=10000);pg.mouse.up()
    check("Portrait directional pad moves Phil",abs(atomic_pos(pg)["x"]-start["x"])>.16)
    pg.screenshot(path=evidence/"mobile-town.png")
    pg.locator("#fullscreen").click()
    pg.wait_for_function("document.fullscreenElement || document.getElementById('scene').classList.contains('full-view')",timeout=10000)
    rect=pg.locator("#view").bounding_box()
    check("Portrait fullscreen fills the device",rect["width"]>385 and rect["height"]>835)
    pg.evaluate("document.fullscreenElement?document.exitFullscreen():document.getElementById('scene').classList.remove('full-view')")


def fallback(pw, executable):
    b=pw.chromium.launch(executable_path=executable,headless=True,args=["--disable-webgl","--disable-webgl2"])
    pg=b.new_page(viewport={"width":1100,"height":700});pg.goto(URL);pg.wait_for_function("!!window.TuesdayStage3D")
    check("A browser with WebGL disabled presents the local native render",get(pg)["renderer"]=="fallback" and pg.locator("#fallback video").is_visible())
    pg.locator("#fallback video").evaluate("(v)=>{v.muted=true;return v.play()}")
    pg.wait_for_function("document.querySelector('#fallback video').currentTime>.1",timeout=10000)
    check("The offline fallback video actually decodes and advances",pg.locator("#fallback video").evaluate("v=>v.videoWidth>0&&v.currentTime>0"))
    pg.screenshot(path=evidence/"fallback.png")
    b.close()


def pace(pg):
    pg.locator("#take").select_option("2");pg.evaluate("TuesdayStage3D.seek(6,.39)")
    pg.locator("#play").click()
    s=pg.evaluate("""()=>new Promise(resolve=>{
      const start=performance.now(), gaps=[];let prev=start,p=null,draws=0,calls=0;
      function step(now){const s=TuesdayStage3D.getState();calls++;
        if(p!==s.progress){if(p!==null)gaps.push(now-prev);p=s.progress;prev=now;draws++;}
        if(now-start<2100){requestAnimationFrame(step);return;}
        const sorted=gaps.sort((a,b)=>a-b);
        resolve({duration_ms:Math.round(now-start),display_callbacks:calls,playhead_updates:draws,
          updates_per_second:+(draws*1000/(now-start)).toFixed(2),p95_update_gap_ms:+sorted[Math.floor(sorted.length*.95)].toFixed(2),
          width:s.stats.width,height:s.stats.height,draw_calls:s.stats.drawCalls,triangles:s.stats.triangles});
      }requestAnimationFrame(step);})""")
    check("Recorded moving 3D playback advances under real browser rendering",s["playhead_updates"]>=5)
    return s


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",type=Path,default=HERE/"evidence")
    args=parser.parse_args()
    global evidence
    evidence=args.evidence;evidence.mkdir(parents=True,exist_ok=True)
    exe=chrome_path()
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=exe,headless=True,args=["--enable-unsafe-swiftshader"])
        pg=page(b)
        driver=pg.locator("#view").evaluate("""c=>{const gl=c.getContext('webgl2')||c.getContext('webgl');
          const ext=gl.getExtension('WEBGL_debug_renderer_info');return {version:gl.getParameter(gl.VERSION),
          driver:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER)}}""")
        linked=pg.context.new_page()
        linked.goto(URL+"?take=film-transcript/seed-701.json&event=d02-t02-reporter&at=.55")
        linked.wait_for_function("!!window.TuesdayStage3D")
        witness=get(linked)
        check("An offline witness link opens the exact recorded coach frame",witness["index"]==6 and witness["phase"]=="aboard coach" and witness["actor"]=="Phil")
        linked.close();pg.bring_to_front()
        walk(pg);clearance=geometry_clearance(pg);native=stage_parity(pg);wardrobe(pg);timing=pace(pg)
        pg.context.close()
        mobile_pg=page(b,True);mobile(mobile_pg);mobile_pg.context.close()
        fallback(pw,exe)
        check("Interactive pages issued zero external network requests",not network)
        check("Interactive pages produced zero uncaught or shader errors",not errors)
        version=b.version;b.close()
    report={"browser":version,"webgl":driver,"checks":checks,"native_stage_parity":native,"geometry_clearance":clearance,"headless_playback":timing,
            "external_http_requests":network,"errors":errors}
    (evidence/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"{len(checks)} checks passed",native,timing)


if __name__=="__main__":
    main()
