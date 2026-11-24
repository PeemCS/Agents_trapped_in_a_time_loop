"""Walk from a finished film to the exact Qwen decision on a relocated, disconnected copy."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
from playwright.sync_api import sync_playwright

def walk(browser,base,width,network):
    page=browser.new_page(viewport={"width":width,"height":850})
    external=[];errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    def filter_route(route):
        u=route.request.url
        if u.startswith(("http:","https:")) and (not network or not u.startswith(network)):
            external.append(u);route.abort()
        else:route.continue_()
    page.route("**/*",filter_route)
    page.goto(base+"screening/index.html#rialto-cut")
    page.wait_for_function("document.querySelector('video').readyState>=2")
    i=page.evaluate("SCREENINGS.find(s=>s.id==='rialto-cut').shots.findIndex(s=>s.id==='d01-evening-reporter' && s.view==='action')")
    assert i>=0
    page.locator("#shot").select_option(str(i))
    page.wait_for_function("document.querySelector('#fact').textContent.toLowerCase().includes('depot bench')")
    vid=page.locator("video").evaluate("v=>({width:v.videoWidth,height:v.videoHeight,at:v.currentTime,duration:v.duration})")
    assert vid["width"]==1280 and vid["height"]==720 and 80<vid["duration"]<81
    page.locator("#source-thinking").click()
    page.wait_for_function("document.querySelector('#action').textContent==='sit at depot'")
    page.wait_for_function("document.querySelector('#thought').textContent.toLowerCase().includes('in the ballroom')")
    assert page.locator("#status").inner_text()=="committed"
    raw=page.locator("#raw").get_attribute("href")
    native_url=page.locator("#raw").evaluate("a=>a.href")
    assert native_url.startswith(base)
    with urllib.request.urlopen(native_url) as resp: native=[json.loads(x) for x in resp if x.strip()]
    words="".join(x["provider"].get("message",{}).get("thinking","") for x in native if x["kind"]=="chunk")
    assert words==page.locator("#thought").text_content()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.goto(base+"last-reel/switchboard/index.html")
    page.locator("#dance").click()
    assert "through one song" in page.locator("#party").inner_text() and page.locator("#calendar").inner_text()=="Tuesday"
    page.locator("#patch").click()
    assert page.locator("#calendar").inner_text()=="Wednesday"
    page.goto(base+"free-walk/index.html?condition=free&seed=953")
    page.wait_for_function("typeof window.FreeWalkPilot!=='undefined'")
    move=page.evaluate("FreeWalkPilot.getState()")
    assert move["condition"]=="free" and move["seed"]==953 and move["requested"]=={"x":15,"y":14}
    page.evaluate("FreeWalkPilot.seek(0,.75)")
    later=page.evaluate("FreeWalkPilot.getState()")
    assert len(later["positions"])==3 and later["positions"]!=move["positions"]
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert not external and not errors
    page.close()
    return {"viewport":width,"mode":"local HTTP" if network else "disconnected files","movie":vid,"source_id":"last-reel-721-hypothesis-d01-t01-reporter",
            "raw":raw,"verified_thinking_chars":len(words),"counterfactual_dance_clock":"Tuesday","counterfactual_transmission_clock":"Wednesday",
            "free_walking_seed":move["seed"],"sampled_requested_coordinates":move["requested"],"rendered_actors":len(later["positions"]),
            "external_requests":external,"browser_errors":errors}

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument("night",type=Path);a.add_argument("--output",type=Path,required=True);args=a.parse_args()
    root=args.night.resolve()
    with socket.socket() as sock:sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
    url="http://127.0.0.1:"+str(port)+"/"
    server=subprocess.Popen(["ruby",str(root/"projection/serve.rb"),str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:
                with urllib.request.urlopen(url,timeout=1):break
            except OSError:time.sleep(.05)
        else:raise RuntimeError("Local screening server did not start")
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel="chrome")
            rows=[walk(browser,base,width,net) for base,net in [(url,url),(root.as_uri()+"/",None)] for width in (1366,390)]
            browser.close()
        args.output.write_text(json.dumps({"checks":rows},indent=2)+"\n")
        print("All four cold-room paths decoded film, sought, and matched the native stream exactly.")
    finally:
        server.terminate();server.wait(timeout=5)
if __name__=="__main__":main()
