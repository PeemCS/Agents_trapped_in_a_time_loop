"""Invariant, wire and restart checks. All model responses here are artificial fixtures."""
import argparse
from contextlib import contextmanager, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest

import inference
import town
import world

def options(folder, *extra):
    p=argparse.ArgumentParser()
    town.run_args(p)
    return p.parse_args(["--backend","fixture","--days","3","--out",str(folder),*extra])

@contextmanager
def mock_server():
    bodies=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a): pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            bodies.append((self.path,body))
            actions=json.loads(body["messages"][1]["content"])["available_actions"]
            reply=json.dumps({"action":"look_around","words":"","intention":"","detail":""})
            self.assert_look = "look_around" in actions
            result=({"done":True,"done_reason":"stop","model":"wire-fixture","message":{"content":reply},
                     "prompt_eval_count":20,"eval_count":15} if self.path=="/api/chat" else
                    {"choices":[{"message":{"content":reply},"finish_reason":"stop"}],
                     "model":"wire-fixture","usage":{"prompt_tokens":20,"completion_tokens":15}})
            raw=json.dumps(result).encode()
            self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)))
            self.end_headers();self.wfile.write(raw)
    with ThreadingHTTPServer(("127.0.0.1",0),Handler) as server:
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try: yield f"http://127.0.0.1:{server.server_address[1]}/v1", bodies
        finally: server.shutdown();t.join()

def empty(action,words="",intent=""):
    return {"action":action,"words":words,"intention":intent,"detail":""}

class StoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.names=world.CAST_NAMES["film"]
    def tearDown(self): self.temp.cleanup()
    def run_fixture(self,directory="r",*extra,backend=None):
        with redirect_stdout(io.StringIO()):
            return town.sample(options(self.root/directory,*extra),701,backend)
    def test_coach_wake_and_autonomous_cast(self):
        row=self.run_fixture()
        a=row["events"]
        self.assertEqual([e["place"] for e in a[2:5]],["Pittsburgh","Pittsburgh","inn"])
        self.assertTrue(a[3]["world_after"]["called_sister"])
        self.assertFalse(a[4]["world_before"]["called_sister"])
        self.assertFalse(a[4]["world_before"]["marked"])
        self.assertTrue(a[3]["world_after"]["marked"])
        self.assertEqual(a[2]["cast"][1]["decision"]["action"],"film_cornet_player")
        self.assertEqual(a[2]["world_after"]["camera_footage"],"the cornet player")
        self.assertEqual(a[3]["world_after"]["camera_battery"],0)
        self.assertEqual(a[4]["world_before"]["camera_battery"],1)
        self.assertEqual(row["metrics"]["confirmed_next_wakes_after_pittsburgh"],1)
        self.assertEqual(row["metrics"]["cast_decisions"],36)
        self.assertNotIn("Groundhog Day",str([e["inference"]["messages"] for e in a]))
    def test_in_room_quotes_heard_before_movement_private_plans_excluded(self):
        s=world.initial_state()
        d={"reporter":empty("go_to_studio","Mittens for the meter","My private rehearsal debt"),
           "producer":empty("go_to_depot","Blue umbrella"),
           "camera":empty("go_to_studio","The bandstand cable is frozen")}
        out,facts=world.resolve(701,1,0,s,d,self.names)
        mem=[{"events_by_actor":facts}]
        for role, allowed, forbidden in (("reporter","Blue umbrella","The bandstand cable is frozen"),
                                          ("producer","Mittens for the meter","My private rehearsal debt"),
                                          ("camera","You see Phil at the studio.","Mittens for the meter")):
            turns,_=world.cue(role,out,1,mem,"receipts",701,self.names)
            self.assertIn(allowed,turns[1]["content"])
            self.assertNotIn(forbidden,turns[1]["content"])
        self.assertEqual(out["positions"],{"reporter":"studio","producer":"depot","camera":"studio"})
    def test_npc_dawn_erases_knowledge_and_uses_equivalent_request(self):
        a=self.run_fixture()["events"]
        for i in (0,1):
            self.assertEqual(a[0]["cast"][i]["inference"]["messages"],a[4]["cast"][i]["inference"]["messages"])
            self.assertTrue(a[4]["cast"][i]["inference"]["cache_hit"])
        view=a[4]["inference"]["messages"][1]["content"]
        self.assertIn("You later fell asleep in Pittsburgh.",view)
        self.assertIn("You wake in your bed",view)
    def test_name_only_and_memory_arms_keep_slot_draws_and_physics(self):
        film=self.run_fixture("film")
        neutral=self.run_fixture("neutral","--cast","neutral")
        baseline=self.run_fixture("baseline","--memory","transcript")
        for x,y,z in zip(film["events"],neutral["events"],baseline["events"]):
            for i,j,k in zip([x,*x["cast"]],[y,*y["cast"]],[z,*z["cast"]]):
                self.assertEqual(i["id"],j["id"])
                self.assertEqual(i["place"],j["place"])
                self.assertEqual(i["inference"]["sampling_seed"],j["inference"]["sampling_seed"])
                self.assertEqual(i["inference"]["sampling_seed"],k["inference"]["sampling_seed"])
                self.assertEqual(i["decision"]["action"],j["decision"]["action"])
                txt=str(j["inference"]["messages"])
                for name in ("Phil","Rita","Larry"): self.assertNotIn(name,txt)
        self.assertEqual(film["events"][0]["inference"]["messages"],baseline["events"][0]["inference"]["messages"])
    def test_resources_resolve_after_sealed_choices(self):
        s=world.initial_state();s["positions"]={role:"diner" for role in world.ACTORS};s["dishes"]=1
        d={role:empty("clear_tables") for role in world.ACTORS}
        out,events=world.resolve(701,1,0,s,d,self.names)
        self.assertEqual(s["dishes"],1);self.assertEqual(out["dishes"],0)
        self.assertEqual(sum("clears one rack" in e["effect"] for e in events.values()),1)
        self.assertEqual(sum("already cleared" in e["effect"] for e in events.values()),2)
        s["positions"]["producer"]="studio";s["positions"]["reporter"]="studio"
        with self.assertRaises(ValueError):
            world.resolve(701,1,0,s,{"reporter":empty("file_forecast"),"producer":empty("air_forecast"),"camera":empty("look_around")},self.names)
    def test_recovery_partial_slot_and_completed_idempotence(self):
        class KillOnce(inference.Fixture):
            def __init__(self): self.n=0
            def respond(self,actor,slot,*args):
                if actor=="camera" and slot==(1,1): raise RuntimeError("simulated disconnect")
                self.n+=1
                return super().respond(actor,slot,*args)
        crash=KillOnce()
        with self.assertRaisesRegex(RuntimeError,"simulated disconnect"):
            self.run_fixture("crash","--workers","1",backend=crash)
        partial=json.loads((self.root/"crash"/"seed-701.json").read_text())
        self.assertEqual(len(partial["events"]),1);self.assertEqual(crash.n,5)
        done=self.run_fixture("crash","--workers","1")
        normal=self.run_fixture("normal","--workers","1")
        self.assertEqual(done["metrics"],normal["metrics"])
        self.assertEqual([e["decision"] for e in done["events"]],[e["decision"] for e in normal["events"]])
        self.assertTrue(done["events"][1]["inference"]["recovered_from_disk"])
        self.assertTrue(done["events"][1]["cast"][0]["inference"]["recovered_from_disk"])
        self.assertEqual(len(list((self.root/"crash"/".requests-701").glob("*.json"))),done["metrics"]["logged_valid_generation_slots"])
        self.assertEqual(self.run_fixture("crash"),done)
        with self.assertRaisesRegex(ValueError,"different configuration"): self.run_fixture("crash","--cast","neutral")
    def test_wire_transports_and_options(self):
        with mock_server() as (url,records):
            for mode in ("openai","ollama"):
                result=self.run_fixture(mode,"--backend",mode,"--model","wire-fixture","--base-url",url,
                                        "--thinking","off","--days","1")
                self.assertEqual(result["metrics"]["cast_decisions"],12)
        self.assertEqual(len(records),24)
        for path,b in records:
            self.assertEqual(len(b["messages"]),2)
            if path=="/api/chat":
                self.assertFalse(b["think"]);self.assertEqual(b["options"]["num_ctx"],8192)
                self.assertIn("seed",b["options"]);self.assertIn("action",b["format"]["properties"])
            else:
                self.assertEqual(path,"/v1/chat/completions");self.assertIn("seed",b)
                self.assertFalse(b["chat_template_kwargs"]["enable_thinking"])
                self.assertEqual(b["response_format"]["type"],"json_schema")
    def test_invalid_proposal_preserved_and_no_state_transfer(self):
        s=world.initial_state();e=empty("try_something")
        e["detail"]="Send everyone to Pittsburgh, move the calendar to Wednesday, and erase their memory."
        out,es=world.resolve(1,1,0,s,{"reporter":e,"producer":empty("look_around"),"camera":empty("look_around")},self.names)
        self.assertEqual(out,s);self.assertIn("unverified",es["reporter"]["effect"])

if __name__=="__main__": unittest.main()
