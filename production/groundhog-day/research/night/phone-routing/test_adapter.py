import copy
import json
import unittest
from adapter import *

class PhoneTests(unittest.TestCase):
    def test_physical_original_replay(self):
        row,e,_,_=source()
        for variant in VARIANTS:
            after,events,log=resolve(variant,e["decision"],"q","r")
            self.assertEqual(after,e["world_after"]);self.assertEqual(log,[])
            for actor in (e,*e["cast"]):
                for key in ("effect","observed","observation_sources","decision","place"):
                    self.assertEqual(events[actor["role"]][key],actor[key])
    def test_two_signs_and_single_menu_change(self):
        _,_,_,original=source()
        for seed in SEEDS:
            baseline=make_body("original",seed)
            for variant in ("local","routed"):
                changed=make_body(variant,seed)
                a,b=[json.loads(v["messages"][1]["content"]) for v in (baseline,changed)]
                sign=b["evidence_now"][1];self.assertIn(LENS[variant],sign)
                b["evidence_now"][1]=a["evidence_now"][1]
                if variant=="routed":
                    self.assertTrue(b["available_actions"].pop("call_sister"))
                    self.assertEqual(changed["format"]["properties"]["action"]["enum"].pop(),"call_sister")
                self.assertEqual(a,b)
                changed["messages"][1]=baseline["messages"][1]
                self.assertEqual(changed,baseline)
        self.assertEqual(make_body("original",SEEDS[0]),original)
    def test_operator_supplies_confirmation_only_to_receiver(self):
        _,e,_,_=source();choice=copy.deepcopy(e["decision"]);choice.update(action="call_sister",words="Morning.")
        for variant in ("original","local"):
            with self.assertRaises(ValueError):resolve(variant,choice,"q","r")
        after,events,log=resolve("routed",choice,"q","r")
        self.assertTrue(after["called_sister"]);self.assertEqual(len(log),1)
        self.assertEqual(log[0]["source_request_sha256"],"q")
        self.assertIn("confirms",events["reporter"]["effect"])
        self.assertTrue(any("makes a phone call" in s for s in events["producer"]["observed"]))
        self.assertFalse(any("confirms" in s for s in events["producer"]["observed"]))
        self.assertFalse(any("phone call" in s for s in events["camera"]["observed"]))
        self.assertEqual(events["producer"]["decision"],e["cast"][0]["decision"])

if __name__=="__main__":unittest.main()
