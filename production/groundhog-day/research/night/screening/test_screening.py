"""Verify offline film decoding, switching and shot-ledger synchronization with Chromium."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent


def main():
    with sync_playwright() as p:
        chrome=p.chromium.launch(channel="chrome")
        errors=[];web=[];rows=[]
        for w,h in [(1280,810),(390,844)]:
            page=chrome.new_page(viewport={"width":w,"height":h})
            page.on("pageerror",lambda exc:errors.append(str(exc)))
            page.on("request",lambda req:web.append(req.url) if req.url.startswith("http") else None)
            page.goto((HERE/"index.html").as_uri())
            page.wait_for_function("document.querySelector('video').readyState>=2")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            for i in range(page.locator("#chooser button").count()):
                page.locator("#chooser button").nth(i).click()
                page.wait_for_function("Number.isFinite(document.querySelector('video').duration)")
                last=page.locator("#shot option").count()-1
                page.locator("#shot").select_option(str(last))
                page.wait_for_function("([i,j])=>document.querySelector('#event').textContent===SCREENINGS[i].shots[j].id",arg=[i,last])
                assert page.locator("#shot").input_value()==str(last)
                video=page.locator("video")
                video.evaluate("v => {v.muted=true;return v.play()}")
                page.wait_for_function("document.querySelector('video').currentTime > SCREENINGS[Array.from(document.querySelectorAll('#chooser button')).findIndex(e=>e.getAttribute('aria-pressed')==='true')].shots.at(-1).at+.1")
                summary=video.evaluate("v=>({secs:v.duration,width:v.videoWidth,height:v.videoHeight,error:v.error?v.error.code:null})")
                assert summary["width"]==1280 and summary["height"]==720 and summary["error"] is None
                rows.append({"viewport":[w,h],"take_index":i,"last_label":page.locator("#event").inner_text(),**summary})
            page.close()
        chrome.close()
    assert not errors and not web
    (HERE/"verification.json").write_text(json.dumps({"checks":rows,"external_requests":web,"browser_errors":errors},indent=2)+"\n")
    print('Offline desktop and mobile decode, ledger seeks and all films verified.')


if __name__=="__main__":main()
