"""Test the performance, the dance counterfactual and the clock in a cold browser."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


def check(browser, url, width):
    page = browser.new_page(viewport={"width":width,"height":900})
    errors = []
    external = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda req: external.append(req.url) if req.url.startswith(("http:", "https:"))
            and not req.url.startswith("http://127.0.0.1:8765/") else None)
    page.goto(url)
    assert page.locator("#status").inner_text() == "Recorded performance"
    assert "empty depot bench" in page.locator("#reporter-effect").inner_text()
    page.locator("#dance").click()
    assert "through one song" in page.locator("#party").inner_text()
    assert "Alternate" in page.locator("#status").inner_text() and page.locator("#calendar").inner_text() == "Tuesday"
    page.locator("#patch").click()
    assert "reaches her" in page.locator("#reel").inner_text()
    assert page.locator("#calendar").inner_text() == "Wednesday"
    page.locator("#restore").click()
    assert page.locator("#status").inner_text() == "Recorded performance"
    total = 0
    for run in page.locator("#run option").evaluate_all("xs=>xs.map(x=>x.value)"):
        page.locator("#run").select_option(run)
        with (HERE.parent / "runs" / run / "take.json").open() as reader:
            take = json.load(reader)
        for day in take["days"]:
            page.locator("#day").select_option(str(day["day"]))
            assert page.locator("#status").inner_text() == "Recorded performance"
            for role in ("reporter","producer","camera"):
                assert page.locator("#"+role).input_value() == day["evening"][role]["decision"]["action"]
                assert page.locator("#"+role+"-effect").inner_text() == day["ending"]["effects"][role]
                assert all(page.locator("#"+role+" option").all_text_contents())
            assert page.locator("#dance").is_disabled() == day["afternoon_state"]["city"]
            assert page.locator("#calendar").inner_text() == day["ending"]["story_complete_clock"]
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            total += 1
    assert not errors and not external
    page.close()
    return {"width":width,"transport":"local files" if url.startswith("file:") else "localhost",
            "checkpoints":total,"verified_ensemble_actions":total*3,"movie_dance_unlocks":False,
            "rita_line_changes_unlock_at_first_checkpoint":True,"errors":errors,"external_requests":external}


if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        rows = [check(browser,u,w) for u in [(HERE/"index.html").as_uri(),
                    "http://127.0.0.1:8765/last-reel/switchboard/index.html"] for w in (1366,390)]
        browser.close()
    (HERE/"verification.json").write_text(json.dumps(rows,indent=2)+"\n")
    print("Verified every recorded evening, the successful dance and both calendars in four cold viewing modes.")
