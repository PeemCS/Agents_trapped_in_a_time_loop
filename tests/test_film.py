from copy import deepcopy
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import math
import re
import unittest

from loopday.film import build_film, build_teaser, subtitles
from loopday.film_depth import RasterBuffer
from loopday.film_follow import FollowSource
from loopday.film_stage import build_bundle
from loopday.render_film import JavaScriptCore, _projector
from loopday.simulation import FixtureDirector, Simulation
from loopday.viewer import export_html, viewer_handler


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.ids = []
        self.scripts = {}

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if "id" in fields:
            self.ids.append(fields["id"])
        if tag == "script":
            self.current = fields["type"]
            self.scripts[self.current] = ""

    def handle_endtag(self, tag):
        if tag == "script":
            self.current = None

    def handle_data(self, value):
        if self.current:
            self.scripts[self.current] += value


def recorded_run():
    events = [
        {"loop": 1, "tick": 0, "type": "day_start", "positions": {"phil": "inn", "ned": "main_st"}},
        {"loop": 1, "tick": 0, "type": "anchor", "anchor": "radio", "location": "inn"},
        {"loop": 1, "tick": 1, "type": "puddle", "actor": "phil", "location": "main_st",
         "state": "wet", "text": "Phil steps into the puddle."},
        {"loop": 1, "tick": 35, "type": "pencil", "actor": "phil", "location": "inn",
         "state": "broken", "text": "Phil breaks the pencil."},
        {"loop": 2, "tick": 0, "type": "anchor", "anchor": "radio", "location": "inn"},
        {"loop": 2, "tick": 0, "type": "test_result", "actor": "phil", "location": "inn",
         "text": "Whole again.", "action_evidence": "e3", "state": "whole", "agrees_with_prediction": True},
        {"loop": 2, "tick": 1, "type": "decision", "actor": "phil", "location": "inn", "action": "avoid_puddle",
         "text": "I know which corner to avoid.", "recalled": ["e5"], "stated_support": ["e5"]},
        {"loop": 2, "tick": 1, "type": "position", "actor": "phil", "location": "main_st", "moving_from": "inn",
         "text": "Phil goes to Main Street."},
        {"loop": 2, "tick": 1, "type": "puddle", "actor": "phil", "location": "main_st",
         "state": "dry", "text": "Phil goes around the puddle."},
        {"loop": 2, "tick": 26, "type": "performance", "actor": "phil", "location": "hotel",
         "text": "Phil plays a song."},
        {"loop": 2, "tick": 30, "type": "invitation", "actor": "phil", "location": "hotel",
         "text": "Would you stay?", "to": "rita"},
        {"loop": 2, "tick": 0, "type": "day_two", "text": "February 3. Rita reaches over to switch off the radio."},
    ]
    for index, event in enumerate(events):
        event["id"] = "e" + str(index)
        event["time"] = "06:30" if event["tick"] == 1 else "06:00"
    return {
        "meta": {"mode": "fixture", "complete": True, "ending": "day_two"},
        "events": events,
        "cast": {"phil": {"name": "Phil", "goal": "Remember what happened."}, "ned": {"name": "Ned"}},
        "locations": {
            "inn": {"label": "Inn", "x": -5, "z": 5}, "main_st": {"label": "Main Street", "x": 0, "z": 2},
            "hotel": {"label": "Hotel", "x": 4, "z": 0},
        },
    }


def fetch_from_handler(handler, path, headers=None):
    request = object.__new__(handler)
    request.path = path
    request.headers = headers or {}
    request.wfile = BytesIO()
    result = {"headers": {}}
    request.send_response = lambda code: result.update(code=code)
    request.send_error = lambda code, message=None: result.update(code=code, message=message)
    request.send_header = lambda key, value: result["headers"].update({key: value})
    request.end_headers = lambda: None
    request.do_GET()
    result["body"] = request.wfile.getvalue()
    return result


class FilmTests(unittest.TestCase):
    def test_film_preserves_event_order_and_world_result(self):
        run = recorded_run()
        film = build_film(run)
        keys = [shot["event_index"] for shot in film["shots"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(film["source"]["mode"], "fixture")
        self.assertEqual(film["shots"][0]["title"], "February 2")
        self.assertEqual(film["shots"][-1]["title"], "February 3")
        self.assertEqual(film["duration_ms"], sum(shot["duration_ms"] for shot in film["shots"]))
        for shot in film["shots"]:
            self.assertEqual(shot["event_id"], run["events"][shot["event_index"]]["id"])
        self.assertLess(keys.index(3), keys.index(5))
        self.assertEqual(build_film(deepcopy(run)), film)
        self.assertIn("Phil: Would you stay?", subtitles(film, vtt=True))
        preview = build_teaser(film, run["events"])
        self.assertLess(preview["duration_ms"], film["duration_ms"])
        self.assertIn(2, [shot["event_index"] for shot in preview["shots"]])
        self.assertIn(8, [shot["event_index"] for shot in preview["shots"]])

    def test_partial_run_does_not_invent_an_ending(self):
        run = recorded_run()
        run["events"] = run["events"][:1]
        run["meta"].update(complete=False, ending="unknown")
        film = build_film(run)
        self.assertFalse(film["full_length"])
        self.assertEqual(film["source"]["ending"], "unknown")
        self.assertEqual([shot["title"] for shot in film["shots"]], ["February 2"])

    def test_stages_translate_actions_and_strip_private_fields(self):
        run = recorded_run()
        event = run["events"][6]
        event["completion"] = "Private completion"
        event["policy_observation"] = {"input": "Private prompt"}
        event["model_metadata"] = {"model_trace": "Local optional trace", "projection_z": {"warmth": .1},
                                   "debug": {"Authorization": "Possibly private value"}}
        bundle = build_bundle(run)
        self.assertEqual(bundle["stages"][3]["pencil"], "broken")
        self.assertEqual(bundle["stages"][5]["pencil"], "whole")
        self.assertEqual(bundle["stages"][7]["positions"]["phil"], "main_st")
        self.assertTrue(bundle["stages"][2]["splash"])
        self.assertFalse(bundle["stages"][8]["splash"])
        self.assertTrue(bundle["stages"][11]["switch_radio"])
        public = bundle["run"]["events"][6]
        self.assertNotIn("completion", public)
        self.assertNotIn("policy_observation", public)
        self.assertNotIn("model_trace", public["model_metadata"])
        self.assertEqual(public["model_metadata"]["debug"], {})
        self.assertEqual(public["model_metadata"]["projection_z"]["warmth"], .1)
        local = build_bundle(run, model_traces=True)["run"]["events"][6]
        self.assertIn("model_trace", local["model_metadata"])
        self.assertNotIn("completion", local)

    def test_portable_html_data_remains_inert(self):
        run = recorded_run()
        run["events"][2]["text"] = "</script><img src=x onerror=alert(1)>"
        bundle = build_bundle(run)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "loopday.html"
            export_html(bundle, path)
            html = path.read_text(encoding="utf-8")
        self.assertNotIn("</script><img", html)
        self.assertNotIn('src="/viewer.js"', html)
        self.assertIn("connect-src 'none'", html)
        parsed = Scripts()
        parsed.feed(html)
        decoded = json.loads(parsed.scripts["application/json"])
        self.assertEqual(decoded["run"]["events"][2]["text"], run["events"][2]["text"])
        self.assertIn("class ReplayViewer", parsed.scripts["module"])
        self.assertTrue(hasattr(viewer_handler(bundle), "do_HEAD"))

    def test_projected_faces_move_and_are_finite(self):
        data = build_bundle(recorded_run())
        try:
            with _projector(data) as project:
                first = project(2, .20, 480, 270)
                impact = project(2, .48, 480, 270)
                calm = project(8, .48, 480, 270)
        except RuntimeError as error:
            if "install Node.js" in str(error):
                self.skipTest("A JavaScript runtime is required to project the scene")
            raise
        self.assertGreater(len(impact["faces"]), 10)
        self.assertNotEqual(first["faces"], impact["faces"])
        self.assertNotEqual(calm["faces"], impact["faces"])
        self.assertTrue(all(math.isfinite(c) and point[2] >= .08
                            for _, polygon in impact["faces"] for point in polygon for c in point))

    def test_native_depth_keeps_near_geometry_in_front(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is required for offline video rendering")
        raster = RasterBuffer(64, 64)
        if raster.run is None:
            self.skipTest("The optional native depth rasterizer could not be compiled")
        surface = Image.new("RGB", (64, 64), "black")
        near = ["rgb(222,33,13)", [[4., 4., 2.], [52., 4., 2.], [4., 52., 2.]]]
        far = ["rgb(45,62,201)", [[2., 2., 8.], [60., 2., 8.], [2., 60., 8.]]]
        self.assertEqual(raster.draw(surface, [near, far]).getpixel((12, 12)), (222, 33, 13))
        self.assertEqual(raster.draw(surface, [far, near]).getpixel((12, 12)), (222, 33, 13))

    def test_browser_app_without_a_browser_process(self):
        run = recorded_run()
        alternate = deepcopy(run)
        alternate["events"][6].update(action="take_shortcut", model_metadata={"projection_z": {"warmth": .7}})
        bundle = build_bundle(run)
        bundle.update(comparison={"label": "Memory withheld", **build_bundle(alternate)}, compare_tick=1)
        with TemporaryDirectory() as directory:
            file = Path(directory) / "index.html"
            export_html(bundle, file)
            parsed = Scripts()
            parsed.feed(file.read_text(encoding="utf-8"))
        try:
            engine = JavaScriptCore()
        except RuntimeError:
            self.skipTest("JavaScriptCore is required for this launch-free browser smoke test")
        harness = Path(__file__).with_name("film_dom.js").read_text(encoding="utf-8")
        app = re.split(r"\nstartReplay\(\)\.catch", parsed.scripts["module"])[0]
        with engine:
            engine.evaluate(harness + "\n" + app)
            result = engine.evaluate("runChecks(" + parsed.scripts["application/json"] + ","
                                     + json.dumps(parsed.ids) + ")")
        self.assertEqual(result, "passed")

    def test_follow_source_reload_uses_committed_snapshot_and_hides_private_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run.json"
            checkpoint = root / "checkpoint.json"
            source = FollowSource(run)
            handler = viewer_handler(source=source)
            waiting = fetch_from_handler(handler, "/follow.json")
            self.assertEqual(json.loads(waiting["body"])["status"], "waiting")
            self.assertIn(b'<body data-follow="true">', fetch_from_handler(handler, "/")["body"])
            self.assertNotIn(b'data-follow="true"', fetch_from_handler(handler, "/replay.html")["body"])
            (root / ".calls.json").write_text('{"secret":"private call journal"}', encoding="utf-8")
            fixture = Simulation(FixtureDirector())
            fixture.advance_tick(36)
            first = fixture.checkpoint()
            first["events"][0]["completion"] = "raw provider completion"
            checkpoint.write_text(json.dumps({"format": 2, "config": {"mode": "fixture"}, "world": first,
                                              "provider": {"secret": "private provider metadata"}}), encoding="utf-8")
            current = fetch_from_handler(handler, "/follow.json")
            body = json.loads(current["body"])
            self.assertEqual(body["status"], "in_progress")
            self.assertEqual(body["mode"], "fixture")
            self.assertEqual(body["committed"], len(first["events"]))
            self.assertNotIn(b"raw provider completion", current["body"])
            self.assertNotIn(b"private provider metadata", current["body"])
            self.assertEqual(fetch_from_handler(handler, "/.calls.json")["code"], 404)
            self.assertEqual(fetch_from_handler(handler, "/checkpoint.json")["code"], 404)
            etag = current["headers"]["ETag"]
            self.assertEqual(fetch_from_handler(handler, "/follow.json", {"If-None-Match": etag})["code"], 304)
            reopened = json.loads(fetch_from_handler(viewer_handler(source=FollowSource(run)), "/follow.json")["body"])
            self.assertEqual(reopened, body)
            fixture.advance_tick(36)
            second = fixture.checkpoint()
            temporary = root / "checkpoint.tmp"
            temporary.write_text(json.dumps({"format": 2, "config": {"mode": "fixture"}, "world": second}), encoding="utf-8")
            temporary.replace(checkpoint)
            resumed = fetch_from_handler(handler, "/follow.json", {"If-None-Match": etag})
            self.assertEqual(resumed["code"], 200)
            self.assertGreater(json.loads(resumed["body"])["committed"], body["committed"])
            # A previous partial artifact must not replace a newer committed prefix.
            stale = {"meta": {"mode": "fixture", "complete": False}, "events": first["events"]}
            run.write_text(json.dumps(stale), encoding="utf-8")
            self.assertEqual(source.load()["status"], "in_progress")
            final = {"meta": {"mode": "fixture", "complete": True, "ending": "repeat"}, "events": second["events"]}
            run.write_text(json.dumps(final), encoding="utf-8")
            self.assertEqual(source.load()["status"], "complete")
            checkpoint.write_text("{invalid", encoding="utf-8")
            self.assertEqual(fetch_from_handler(handler, "/follow.json")["code"], 503)

    def test_follow_view_draws_newly_committed_choice_and_labels_source(self):
        record = recorded_run()
        record["meta"].update(mode="local_policy", complete=False)
        record["events"][6]["mode"] = "local_policy"
        first = {"status": "in_progress", "mode": "local_policy", "committed": 6,
                 "bundle": build_bundle({**record, "events": record["events"][:6]})}
        second = {"status": "in_progress", "mode": "local_policy", "committed": 7,
                  "bundle": build_bundle({**record, "events": record["events"][:7]})}
        with TemporaryDirectory() as directory:
            file = Path(directory) / "index.html"
            export_html(second["bundle"], file)
            parsed = Scripts()
            parsed.feed(file.read_text(encoding="utf-8"))
        try:
            engine = JavaScriptCore()
        except RuntimeError:
            self.skipTest("JavaScriptCore is required for this launch-free browser smoke test")
        harness = Path(__file__).with_name("film_dom.js").read_text(encoding="utf-8")
        app = re.split(r"\nstartReplay\(\)\.catch", parsed.scripts["module"])[0]
        with engine:
            engine.evaluate(harness + "\n" + app)
            result = engine.evaluate("checkFollow(..." + json.dumps([first, second, parsed.ids]) + ")")
        self.assertEqual(result, "passed")


if __name__ == "__main__":
    unittest.main()
