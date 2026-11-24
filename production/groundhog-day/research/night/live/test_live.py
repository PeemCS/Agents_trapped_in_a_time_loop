"""Exercise the loopback feed and real playback across interrupted/replaced files."""
import argparse
import json
import os
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

from director import Handler, Source


def write_take(path, take, count, status="partial"):
    frame = {**take, "status": status, "events": take["events"][:count]}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(frame))
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("take", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright
    take = json.loads(args.take.read_text())
    assert len(take["events"]) >= 4
    started = time.monotonic()
    metrics = {}
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
        path = Path(tmp) / "take.json"
        http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        http.source = Source(path, 0)
        server = threading.Thread(target=http.serve_forever, daemon=True)
        server.start()
        browser = playwright.chromium.launch(channel="chrome", args=["--disable-background-timer-throttling"])
        errors = []
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 810})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{http.server_port}")
            status = page.locator("#status")
            status.get_by_text("Waiting for the source file").wait_for(timeout=10000)
            write_take(path, take, 1)
            town = next(frame for frame in page.frames if "/visual/index.html" in frame.url)
            state = "window.TuesdayTown.getState()"
            town.wait_for_function(state+".total===1 && "+state+".mode==='replay'")
            town.wait_for_function(state+".progress>0")
            first_epoch = http.source.epoch
            write_take(path, take, 3)
            town.wait_for_function(state+".total===3")
            # Break the writer while the projector is running. It must retain the last good take.
            path.write_text("{")
            status.get_by_text("Holding last committed frame", exact=False).wait_for()
            assert town.evaluate(state)["total"] == 3
            write_take(path, take, 4)
            town.wait_for_function(state+".total===4")
            assert http.source.epoch == first_epoch
            page.locator("#toggle").click()
            write_take(path, take, 5)
            assert status.inner_text() == "Feed paused"
            page.locator("#toggle").click()
            town.wait_for_function(state+".total===5")
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(args.screenshot))
            # Same cast/seed, changed committed suffix. A client should switch epochs and discard stale frames.
            replacement = json.loads(json.dumps(take))
            replacement["events"][0]["decision"]["words"] = "Replaced source for renderer test"
            write_take(path, replacement, 2, "complete")
            town.wait_for_function(state+".total===2")
            assert http.source.epoch == first_epoch + 1
            status.get_by_text("complete", exact=False).wait_for()
            metrics["replacement_epoch_changed"] = True
            metrics["witnessed_counts"] = [1,3,4,5,2]
            metrics["held_during_malformed_write"] = True
            metrics["played_initial_chunk"] = True
            metrics["browser"]=browser.version
            sub = http.source.slice(first_epoch, 99)
            assert sub["from"] == 0 and len(sub["events"]) == 2
            serialized = json.dumps(sub)
            assert all(token not in serialized for token in ('"messages"', '"inference"', '"intention"', '"world_before"'))
            metrics["presentation_projection_excluded_private_fields"] = True
            assert not errors, errors
            metrics["page_errors"] = errors
        finally:
            browser.close()
            http.shutdown()
            http.server_close()
    metrics["wall_seconds"] = round(time.monotonic()-started, 2)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, indent=2)+"\n")
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
