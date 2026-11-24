"""Verify browser selection, raw integrity, portable playback and two real branches."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent

def verify_monitor(browser, url, size, recorded):
    page=browser.new_page(viewport={"width":size[0],"height":size[1]})
    errors=[];requests=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.on("request",lambda req:requests.append(req.url) if req.url.startswith("http") else None)
    page.goto(url+"#standard-d02-t03-reporter")
    page.wait_for_function("document.querySelector('#action').textContent==='call sister'")
    page.wait_for_function("document.querySelector('#thought').textContent.length>50 && document.querySelector('#raw').hasAttribute('href')")
    assert page.locator("#thought").inner_text() and page.locator("#line").inner_text()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    if recorded:
        assert not requests
    else:
        page.wait_for_function("document.querySelector('#mode').textContent.startsWith('Live monitor')")
    people=[]
    for role in ("producer","camera","reporter"):
        page.locator("#cast").select_option(role)
        page.wait_for_function("document.querySelector('#thought').textContent.length>50")
        people.append(page.locator("#who").inner_text())
        page.wait_for_function("document.querySelector('#input').textContent.includes('messages')")
    assert people==["Rita","Larry","Phil"]
    page.locator("#version").select_option("wake branch")
    page.wait_for_function("document.querySelector('#thought').textContent.length===5324")
    assert "Maybe this breaks the loop" in page.locator("#thought").inner_text()
    assert not errors
    page.close()
    return {"mode":"offline" if recorded else "live","viewport":size,"characters":people,
            "wake_characters":5324,"page_errors":errors,"offline_web_requests":requests if recorded else None}

def verify_branch(browser,size):
    path=NIGHT/"branches";page=browser.new_page(viewport={"width":size[0],"height":size[1]})
    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto((path/"index.html").as_uri())
    assert page.locator("canvas").count()==2
    rows=[]
    for i in range(4):
        page.locator("#steps button").nth(i).click()
        page.locator("#scrub").evaluate("(x,i)=>{x.value=i+0.98;x.dispatchEvent(new Event('input'));}",i)
        rows.append({"step":i,"places":page.locator(".where").all_text_contents(),"outcomes":page.locator(".effect").all_text_contents()})
    assert rows[1]["places"][0]!=rows[1]["places"][1] and rows[2]["places"][0]==rows[2]["places"][1]
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.locator("#play").click()
    page.wait_for_function("document.querySelector('#play').textContent==='Replay both'")
    assert not errors
    page.close()
    return {"viewport":size,"steps":rows,"page_errors":errors}

if __name__=="__main__":
    with sync_playwright() as p:
        browser=p.chromium.launch(channel="chrome");results=[];branches=[]
        for wh in ((1280,810),(390,844)):
            results.append(verify_monitor(browser,"http://127.0.0.1:18767/",wh,False))
            results.append(verify_monitor(browser,(HERE/"index.html").as_uri(),wh,True))
            branches.append(verify_branch(browser,wh))
        browser.close()
    (HERE/"browser-qa.json").write_text(json.dumps(results,indent=2)+"\n")
    (NIGHT/"branches/browser-qa.json").write_text(json.dumps(branches,indent=2)+"\n")
    print("Verified four viewing modes and two two-camera branch replays.")
