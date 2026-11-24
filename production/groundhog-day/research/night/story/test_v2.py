import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

import v2
import world
import world_v2 as w

def d(a,words="",signal=""):return {"action":a,"words":words,"intention":"","detail":signal}
N=world.CAST_NAMES["film"]
def decide(s,p="spend_time_here",r="spend_time_here",l="spend_time_here",tick=3,words="hello",sig=None):
    sig=sig or {}
    ds={a:d(v,words,sig.get(a,"")) for a,v in zip(world.ACTORS,(p,r,l))}
    return w.resolve(711,1,tick,s,ds,N,"move","bulletin")

class SecondProtocol(unittest.TestCase):
    def test_words_do_not_consume_move_or_make_trip(self):
        s=w.initial()
        self.assertFalse(any(a.startswith("talk_to_") for a in w.actions("reporter",s,0,N,"move","bulletin")))
        self.assertIn("talk_to_Rita",w.actions("reporter",s,0,N,"talk-action","bulletin"))
        a,events=decide(s,p="go_to_studio",tick=0,words="I'm heading to Pittsburgh.")
        self.assertEqual(a["positions"]["reporter"],"studio")
        self.assertIn("Phil says: I'm heading to Pittsburgh.",events["producer"]["observed"])
        self.assertNotIn("Phil says: I'm heading to Pittsburgh.",events["camera"]["observed"])
    def test_voluntary_signals_never_observe_simultaneous_request(self):
        s=w.initial()
        a,es=decide(s,tick=0,sig={"producer":"invite_reporter","reporter":"accept_assignment"})
        self.assertEqual(es["reporter"]["signal_status"],"unavailable")
        self.assertEqual(a["assignments"]["reporter"]["status"],"invited")
        self.assertFalse(es["camera"]["radio_heard"])
        b,es=decide(a,tick=1,p="go_to_depot",sig={"reporter":"accept_assignment"})
        self.assertEqual(b["assignments"]["reporter"]["status"],"accepted")
        self.assertEqual(b["assignments"]["reporter"]["invite_id"],"d01-t00-producer")
        self.assertEqual(b["positions"]["reporter"],"depot")
    def test_afternoon_invite_can_be_accepted_and_delivered_at_seven(self):
        s=w.initial()
        last,_=decide(s,p="take_coach_to_Pittsburgh",tick=2,sig={"producer":"invite_reporter"})
        self.assertIn("accept_assignment",w.signal_menu("reporter",last,3,"bulletin"))
        self.assertEqual(w.signal_menu("producer",last,3,"bulletin"),[""])
        after,es=decide(last,p="call_live_report",r="patch_reporter_line",sig={"reporter":"accept_assignment"})
        self.assertEqual(after["bulletin"]["delivered_assignments"],["reporter"])
        self.assertEqual(after["assignments"]["reporter"]["event_id"],es["reporter"]["id"])
        self.assertEqual(after["bulletin"]["source_place"],"Pittsburgh")
        no,_=decide(s,p="call_live_report",r="patch_reporter_line",sig={"reporter":"accept_assignment"})
        self.assertEqual(no["bulletin"]["delivered_assignments"],[])
    def test_independent_patch_and_contribution(self):
        s=w.initial()
        a,_=decide(s,p="take_coach_to_Pittsburgh",tick=2)
        self.assertEqual(a["positions"]["reporter"],"Pittsburgh")
        b,e=decide(a,p="call_live_report",r="patch_reporter_line",words="I'm home.")
        self.assertEqual(b["bulletin"]["channel"],"live_report")
        self.assertEqual(b["bulletin"]["source_place"],"Pittsburgh")
        self.assertEqual(b["bulletin"]["source_ids"],["d01-t03-producer","d01-t03-reporter"])
        self.assertIn("live report from Pittsburgh",e["reporter"]["effect"])
        c,_=decide(a,p="call_live_report",r="spend_time_here")
        self.assertEqual(c["bulletin"]["channel"],"station_ident")
        e,_=decide(a,p="spend_time_here",r="patch_reporter_line")
        self.assertEqual(e["bulletin"]["channel"],"empty_selected_return")
        f,_=decide(a,p="call_live_report",r="patch_reporter_line",words="")
        self.assertEqual(f["bulletin"]["channel"],"silent_live_reporter_line")
    def test_filed_and_camera_source_provenance(self):
        s=w.initial();s["positions"]["reporter"]="studio"
        a,_=decide(s,p="file_forecast",l="film_cornet_player",tick=2)
        b,_=decide(a,r="patch_camera_line",l="send_camera_take")
        self.assertEqual(b["bulletin"]["footage"],"the cornet player")
        self.assertIn("d01-t02-camera",b["bulletin"]["source_ids"])
        c,_=decide(a,r="play_filed_forecast")
        self.assertTrue(c["aired"])
        self.assertEqual(c["bulletin"]["source_ids"],["d01-t03-producer","d01-t02-reporter"])
        self.assertNotIn("air_forecast",w.actions("producer",a,3,N,"move","bulletin"))
    def test_morning_and_memory_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=v2.run_args(argparse.ArgumentParser());args=p.parse_args(["--backend","fixture","--days","6","--out",tmp])
            with redirect_stdout(io.StringIO()): row=v2.sample(args,711)
            self.assertEqual(len(row["events"]),24)
            morning=row["events"][4]
            self.assertEqual(morning["origin"],"inn")
            self.assertEqual(morning["world_before"]["bulletin"],None)
            self.assertFalse(morning["world_before"]["assignments"])
            obs=json.loads(morning["inference"]["messages"][1]["content"])
            self.assertIn("fell asleep in Pittsburgh",json.dumps(obs["remembered_experiences"]))
            for other in morning["cast"]:
                obs=json.loads(other["inference"]["messages"][1]["content"])
                self.assertEqual(obs["remembered_experiences"],[])
            self.assertEqual(v2.sample(args,711),row)
    def test_grouped_old_family_anchor_is_preserved(self):
        s=w.initial(); records=[]
        for day in range(1,8):
            s=w.initial()
            for tick in range(4):
                act="take_coach_to_Pittsburgh" if day==2 and tick==2 else "call_sister" if day==2 and tick==3 else "spend_time_here"
                ds={"reporter":d(act),"producer":d("spend_time_here"),"camera":d("spend_time_here")}
                s,events=w.resolve(711,day,tick,s,ds,N,"move","bulletin")
                records.append(events["reporter"])
        memory=json.dumps(w.memory(records,"reporter","wakes"))
        self.assertIn("confirms the moving van is booked for Wednesday",memory)
        self.assertIn("fell asleep in Pittsburgh",memory)
    def test_ordinary_arm_supplies_no_switch_or_signals(self):
        s=w.initial()
        self.assertNotIn("patch_reporter_line",w.actions("producer",s,3,N,"move","ordinary"))
        self.assertEqual(w.signal_menu("producer",s,1,"ordinary"),[""])
        v,actions=w.cue("reporter",s,0,[],"wakes",711,N,"move","ordinary")
        self.assertNotIn("seven o'clock bulletin",v[1]["content"])
        self.assertNotIn("Groundhog Day",str(v))
if __name__=="__main__":unittest.main()
