#!/usr/bin/env python3
"""Compare actor, location and visible prop states to a real take at each cut boundary."""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from edit import verify, write_json


def check(trace, edl, stage, out, chrome):
    data = json.loads(trace.read_text())
    cut = json.loads(edl.read_text())
    verify(trace, cut)
    observations = []
    with sync_playwright() as browser_engine:
        browser = browser_engine.chromium.launch(
            headless=True, executable_path=chrome, args=["--disable-background-networking"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 568}, device_scale_factor=1)
        page.goto(stage.resolve().as_uri())
        page.evaluate("r=>TuesdayTown.loadTrace(r)", data)
        page.evaluate("TuesdayTown.setCinematic(true,{captions:false})")
        for shot in cut["shots"]:
            slot = data["events"][shot["event_index"]]
            active = next(r for r in [slot, *slot["cast"]] if r["actor"] == shot["focus"])
            page.evaluate(
                "c=>TuesdayTown.setCamera(c)",
                {"actor": active["role"], "framing": shot.get("framing", "street")},
            )
            dawn = shot["view"] == "morning"
            position = shot["end"]
            truth = slot["world_before" if dawn else "world_after"]
            state = page.evaluate("([i,p])=>TuesdayTown.seek(i,p)", [shot["event_index"], position])
            props = state["worldFacts"]
            assert state["eventId"] == slot["id"] and state["cameraActor"] == active["actor"]
            assert state["place"] == slot["origin" if dawn else "place"]
            for key in (
                "marked",
                "weather_tape",
                "aired",
                "band_recorded",
                "called_sister",
                "dishes",
                "camera_battery",
                "camera_footage",
            ):
                assert props.get(key) == truth.get(key), (slot["id"], key, props.get(key), truth.get(key))
            observations.append(
                {
                    "event_id": slot["id"],
                    "view": shot["view"],
                    "camera_actor": active["actor"],
                    "at": state["place"],
                    "framing": state["framing"],
                    "props": props,
                }
            )
        browser.close()
    write_json(
        out,
        {
            "source_sha256": cut["source_sha256"],
            "checked_shots": len(observations),
            "observations": observations,
        },
    )
    return len(observations)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("trace", "edl", "stage", "out"):
        p.add_argument(arg, type=Path)
    p.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    print("Checked", check(**vars(p.parse_args())), "shot boundaries")
