"""Browser verification for raw coordinate provenance, route playback, controls and responsive layout."""
import hashlib,json,shutil,os,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent;OUT=HERE/"evidence";URL=(HERE/"index.html").as_uri()
sys.path.insert(0,str(HERE.parent/"stage3d/viewer"));from verify import chrome_path
def main():
    checks=[];errors=[];network=[]
    def check(label,val):
        if not val:raise AssertionError(label)
        checks.append(label)
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,executable_path=chrome_path())
        p=b.new_page(viewport={"width":1365,"height":820},device_scale_factor=1)
        p.on("pageerror",lambda e:errors.append(str(e)));p.on("request",lambda r:network.append(r.url) if r.url.startswith(("http:","https:")) else None)
        p.goto(URL+"?condition=free&seed=953");p.wait_for_function("typeof window.FreeWalkPilot!=='undefined'")
        state=lambda:p.evaluate("FreeWalkPilot.getState()")
        s=state();check("Source deep link opens the actual local seed-953 coordinate pilot",s["condition"]=="free" and s["seed"]==953 and s["model"]=="qwen3:0.6b")
        take=json.loads((HERE/"runs/free-953/take.json").read_text());e=take["ticks"][0][0]
        check("The displayed target and source raw file match the logged model result",s["requested"]==e["requested"] and s["raw"]==e["raw"] and p.locator("#receipt").get_attribute("href")==e["raw"])
        a=p.evaluate("FreeWalkPilot.seek(0,0)");m=p.evaluate("FreeWalkPilot.seek(0,.52)");z=p.evaluate("FreeWalkPilot.seek(0,1)")
        check("A fractional seek moves Phil along the recorded route and ends at his resolved point",a["positions"]["Phil"]!=m["positions"]["Phil"]!=z["positions"]["Phil"] and z["positions"]["Phil"]==e["resolved"])
        check("All three performers finish at their independently resolved points",all(z['positions'][row['actor']]==row['resolved'] for row in take["ticks"][0]))
        p.evaluate("FreeWalkPilot.seek(0,.65)");p.screenshot(path=OUT/"desktop.png")
        p.locator("#follow").click();p.locator("#actor").select_option("camera");check("The subject selector changes to Larry's raw call without changing time",state()["eventId"].endswith("-camera") and not state()["wide"] and state()["progress"]==.65)
        p.locator("#next").click();check("The next turn preserves the chosen cast member",state()["slot"]==1 and state()["role"]=="camera")
        p.locator("#back").click();p.locator("#time").fill("2.45");check("Timeline seeks arbitrary fractions",state()["slot"]==2 and abs(state()["progress"]-.45)<.00001)
        p.evaluate("FreeWalkPilot.seek(0,.99)");p.locator("#play").click();p.wait_for_function("FreeWalkPilot.getState().slot===1 && FreeWalkPilot.getState().progress>.02");p.locator("#play").click()
        check("Playback progresses continuously across the shared turn barrier",state()["slot"]==1 and not state()["playing"])
        p.goto(URL+"?condition=obstruction&seed=967");p.wait_for_function("window.FreeWalkPilot")
        check("A blocked hotel pin exposes its resolved curb coordinates",state()["requested"]=={"x":5.2,"y":6} and state()["resolved"]=={"x":5.2,"y":4.4} and "Closest reachable" in p.locator("#result").inner_text())
        p.evaluate("FreeWalkPilot.seek(0,.70)");p.locator("#follow").click();p.screenshot(path=OUT/"adjusted.png")
        p.locator("#next").click();check("Phil's second calibration walk reads the previous blocked outcome",state()["raw"].endswith("t01-reporter.json") and state()["requested"]!={"x":5.2,"y":6})
        p.goto(URL+"?condition=unmarked&seed=927");p.wait_for_function("window.FreeWalkPilot");p.evaluate("FreeWalkPilot.seek(1,.52)")
        p.goto(URL+"?condition=free&seed=913&policy=reserved");p.wait_for_function("window.FreeWalkPilot");p.evaluate("FreeWalkPilot.seek(0,1)")
        reserved=p.evaluate("FreeWalkPilot.getState()")
        check("The reserved counterfactual is labeled and separates duplicate door requests",reserved["source"]=="counterfactual_reserved_routes" and reserved["positions"]["Phil"]!=reserved["positions"]["Rita"] and "counterfactual" in p.locator("#provenance").inner_text().lower())
        p.locator("#policy").select_option("original");true_state=p.evaluate("FreeWalkPilot.getState()")
        check("Switching back restores the original coincident endpoint and same raw proposal",true_state["source"]=="local_ollama_coordinate_pilot" and true_state["positions"]["Phil"]==true_state["positions"]["Rita"] and true_state["requested"]==reserved["requested"])
        p.goto(URL+"?condition=coordinated&seed=913");p.wait_for_function("window.FreeWalkPilot")
        s=p.evaluate("FreeWalkPilot.seek(0,1)")
        check("The fresh coordinated run shows actual separated endpoints and its own logged model receipts",s["condition"]=="coordinated" and s["positions"]["Phil"]!=s["positions"]["Rita"] and s["raw"].startswith("prospective/") and p.locator("#policy").is_disabled())
        p.screenshot(path=OUT/"live-reservations.png")
        m=b.new_context(viewport={"width":390,"height":844},has_touch=True,is_mobile=True,device_scale_factor=1);mobile=m.new_page();mobile.goto(URL+"?condition=free&seed=953")
        mobile.wait_for_function("window.FreeWalkPilot");mobile.locator("#follow").tap();mobile.evaluate("FreeWalkPilot.seek(0,.5)");mobile.screenshot(path=OUT/"mobile.png")
        check("Touch controls work in portrait and show all three real actors",len(mobile.evaluate("FreeWalkPilot.getState().positions"))==3 and not mobile.evaluate("FreeWalkPilot.getState().wide"))
        mobile.set_viewport_size({"width":320,"height":740});check("A 320px viewport has no horizontal overflow",mobile.evaluate("document.documentElement.scrollWidth<=innerWidth"))
        check("The published offline browser made no external requests or page errors",not errors and not network)
        r={"checks":checks,"count":len(checks),"browser":b.version,"network":network,"errors":errors};(OUT/"browser.json").write_text(json.dumps(r,indent=2)+"\n");b.close()
    print(len(checks),"browser checks passed")
if __name__=="__main__":main()
