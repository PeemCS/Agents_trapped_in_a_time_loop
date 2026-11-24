"""Exercise the audience card locally. All responses produced here are synthetic."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent
FILM = HERE.parents[1] / "editor" / "rialto-cut" / "film.mp4"


def seek(video, seconds):
    return video.evaluate(
        """async (v, t) => {
            v.pause();
            await new Promise((resolve, reject) => {
                const timer = setTimeout(() => reject(Error("seek timed out")), 10000);
                v.addEventListener("seeked", () => { clearTimeout(timer); resolve(); }, {once: true});
                v.currentTime = t;
            });
            return v.currentTime;
        }""",
        seconds,
    )


def check(browser, url, mobile, film_sha, scratch):
    width, height = (390, 844) if mobile else (1280, 810)
    context = browser.new_context(
        viewport={"width": width, "height": height},
        is_mobile=mobile,
        has_touch=mobile,
        device_scale_factor=2 if mobile else 1,
        accept_downloads=True,
    )
    page = context.new_page()
    requests, unexpected, errors = [], [], []
    allowed_host = urlsplit(url).netloc

    def check_request(route):
        parsed = urlsplit(route.request.url)
        if parsed.scheme in ("http", "https") and parsed.netloc != allowed_host:
            unexpected.append(parsed.netloc)
            route.abort()
            return
        route.continue_()

    context.route("**/*", check_request)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda req: requests.append((req.method, req.url, req.post_data)))
    try:
        page.goto(url)
        video = page.locator("video")
        video.evaluate("""v => v.readyState >= 2 || new Promise(resolve =>
            v.addEventListener('loadeddata', resolve, {once:true}))""")
        assert video.evaluate("v => v.controls && v.videoWidth === 1280 && v.videoHeight === 720")
        assert abs(video.evaluate("v => v.duration") - 80.25) < .002
        assert not page.locator("#response").is_visible()
        assert page.get_by_role("textbox").count() == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("#start").is_visible() and video.evaluate("v => v.inert")
        page.locator("#start").click()
        page.locator("#start").wait_for(state="hidden")
        landed = seek(video, 30.20)
        assert abs(landed - 30.20) < .04
        before = video.evaluate("v => v.getVideoPlaybackQuality().totalVideoFrames")
        video.evaluate("v => {v.muted = true; return v.play()}")
        video.evaluate("""v => new Promise(resolve => {
            function checkTime() {
                if (v.currentTime > 30.55) {
                    v.removeEventListener('timeupdate', checkTime);
                    resolve();
                }
            }
            v.addEventListener('timeupdate', checkTime);
            checkTime();
        })""")
        frames = video.evaluate("v => v.getVideoPlaybackQuality().totalVideoFrames") - before
        assert frames > 0 and video.evaluate("v => !v.error")
        assert abs(seek(video, 79.60) - 79.60) < .04
        assert not page.locator("#response").is_visible()
        video.evaluate("v => v.play()")
        page.locator("#after").wait_for(state="visible")
        assert video.evaluate("v => v.ended")
        assert page.locator("#after").evaluate("el => el === document.activeElement")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.locator("#first-evening").fill("  ")
        page.locator("#export").click()
        assert not page.locator("form").evaluate("form => form.checkValidity()")
        assert page.locator("#status").inner_text() == ""
        ids = ["first-evening", "delivery", "last-morning"]
        examples = {key: f"Synthetic QA response for {key}" for key in ids}
        for key, text in examples.items():
            page.locator("#" + key).fill("  " + text + "  ")
        page.locator("#moment").fill('Synthetic line one\n"Synthetic line two"')
        page.locator("#clarity").select_option("3")

        def export():
            with page.expect_download() as event:
                page.locator("#export").click()
            download = event.value
            assert download.suggested_filename == "eight-bars-response.json"
            target = scratch / "synthetic-test-only.json"
            download.save_as(target)
            data = json.loads(target.read_text())
            assert set(data) == {"format", "film", "factual", "optional"}
            assert data["format"] == "eight-bars-audience-response-v1"
            assert data["film"] == {"title": "Eight Bars", "sha256": film_sha}
            return data

        sample = export()
        assert sample["factual"] == examples
        assert sample["optional"] == {"moment": 'Synthetic line one\n"Synthetic line two"', "clarity_1_to_5": 3}
        page.locator("#clear").click()
        assert page.locator("#viewing").is_visible()
        assert not page.locator("#response").is_visible()
        assert video.evaluate("v => v.paused && v.currentTime < .05")
        page.locator("#watched").click()
        assert all(page.locator("#" + key).input_value() == "" for key in ids + ["moment", "clarity"])
        for key in ids:
            page.locator("#" + key).fill("Unsure")
        blank_optional = export()
        assert blank_optional["optional"] == {"moment": None, "clarity_1_to_5": None}
        assert blank_optional["factual"] == dict.fromkeys(ids, "Unsure")
        # A new visit must not recover the previous viewer's fields.
        page.reload()
        page.locator("#watched").click()
        assert all(page.locator("#" + key).input_value() == "" for key in ids + ["moment", "clarity"])
        assert not errors and not unexpected, (errors, unexpected)
        for method, request_url, payload in requests:
            assert method == "GET" and payload is None, (method, request_url)
            assert "Synthetic" not in request_url and "Unsure" not in request_url
        return {
            "transport": "file" if not allowed_host else "loopback",
            "viewport": [width, height],
            "emulated_touch": mobile,
            "duration_s": 80.25,
            "seek_landed_s": landed,
            "video_frames_advanced": frames,
            "native_ended_opened_questions": True,
            "local_json_downloads_parsed": 2,
            "reset_and_reload_clear_answers": True,
            "requests_carrying_answers": 0,
            "external_requests": unexpected,
            "page_errors": errors,
        }
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loopback", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    endpoint = urlsplit(args.loopback)
    if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("The HTTP test requires a loopback URL.")
    film_sha = hashlib.sha256(FILM.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="eight-bars-card-qa-") as work, sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", args=[
            "--disable-background-networking", "--disable-gpu", "--disable-accelerated-video-decode",
            "--autoplay-policy=no-user-gesture-required",
        ])
        entries = [(HERE / "index.html").as_uri(), args.loopback.rstrip("/") + "/projection/audience/"]
        rows = [check(browser, entry, mobile, film_sha, Path(work)) for entry in entries for mobile in (False, True)]
        chrome = browser.version
        browser.close()
    (HERE / "ui-check.json").write_text(json.dumps({
        "kind": "Automated UI QA with synthetic temporary exports. No audience responses.",
        "film_sha256": film_sha, "chrome": chrome, "checks": rows,
    }, indent=2) + "\n")
    print("Four local player configurations passed. Eight synthetic JSON exports parsed.")


if __name__ == "__main__":
    main()
