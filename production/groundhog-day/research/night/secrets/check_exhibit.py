"""Exercise every actor lens and real trace link in the packaged file viewer."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
if __name__=="__main__":
    measured=json.loads((HERE/"measured.json").read_bytes())
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel="chrome")
        for width,height in [(1280,850),(390,844)]:
            p=browser.new_page(viewport={"width":width,"height":height})
            errors=[];p.on("pageerror",lambda err:errors.append(str(err)))
            p.goto((HERE/"exhibit.html").as_uri(),wait_until="load")
            checks=0
            for take in measured["takes"]:
                p.locator("#seed").select_option(str(take["root"]))
                p.locator("#arm").select_option(take["sightline"])
                for i,step in enumerate(take["steps"]):
                    p.locator("#phases button").nth(i).click()
                    assert p.locator("#clock").inner_text()==str(step["clock"]).zfill(2)+"s"
                    assert p.locator("#choice").inner_text()==step["menu"][step["chosen"]]
                    for role in ("Phil","Rita","Larry"):
                        p.locator("#people button",has_text=role).click()
                        assert p.locator("#view").inner_text()==step["observers"][role]["text"]
                        checks+=1
                    for link in ("raw","request","take"):
                        assert (HERE/p.locator("#"+link).get_attribute("href")).is_file()
                assert p.locator("#meters").inner_text().endswith(take["later_board_access"])
            assert not errors
            assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            p.close()
            results.append({"size":[width,height],"verified_view_selections":checks,"page_errors":errors})
        browser.close()
    (HERE/"browser-qa.json").write_text(json.dumps(results,indent=2)+"\n")
    print(results)
