import copy
import json
import math
import unittest

from analyze import ARCHIVE, OTHER, PRESENT, UNKNOWN, analyze, gain, primary_events, scores


class RuleNotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = analyze()

    def test_one_trial_and_a_missing_trial(self):
        def trial(index, state, advanced):
            return {"day_just_ended":index,"exposure":{"h":state},"advanced":advanced}
        dataset = [trial(0,UNKNOWN,True),trial(1,OTHER,False),trial(2,PRESENT,False)]
        fit = scores(dataset,"h")
        self.assertEqual(fit["scored_wakes"],2)
        self.assertEqual(fit["unknown"],1)
        self.assertAlmostEqual(fit["bayes_factor"],1/9)
        self.assertAlmostEqual(fit["posterior"],.1)
        self.assertAlmostEqual(fit["loss_prequential_mixture_nats"],-math.log(.9)-math.log(.5))
        self.assertAlmostEqual(gain(.5),.5310044064107189)

    def test_each_day_appears_once_despite_cumulative_diary(self):
        for p in self.data["paths"].values():
            self.assertEqual([e["day_just_ended"] for e in p["wakes"]],[0,1,2,3])
            self.assertFalse(any(e["advanced"] for e in p["wakes"]))
            self.assertEqual(sum(e["recipient_confirmation_at_wake"]=="first_visible" for e in p["wakes"]),1)
        d = self.data["paths"]["721-library"]["rule_beliefs"]["coach"]
        self.assertEqual(d["observed_triggers"],4)
        self.assertAlmostEqual(d["posterior"],1/(1+9**4))
        self.assertAlmostEqual(d["one_affirmative_exposure_only_posterior"],.1)

    def test_false_positives_require_physical_confirmation(self):
        paths = self.data["paths"]
        party = paths["731-uncued"]["wakes"][3]
        self.assertEqual(party["exposure"]["dance"],UNKNOWN)
        performance = paths["731-library"]["wakes"][3]
        self.assertEqual(performance["exposure"]["dance"],UNKNOWN)
        self.assertEqual(performance["exposure"]["public_piano"],PRESENT)
        self.assertEqual(performance["exposure"]["rehearsal"],OTHER)
        repaired = paths["731-library"]["rule_beliefs"]["driver"]
        self.assertEqual(repaired["trigger_then_reset"],1)
        for p in paths.values():
            self.assertEqual(p["rule_beliefs"]["dance"]["observed_triggers"],0)
            self.assertEqual(p["rule_beliefs"]["station_ack"]["unknown"],4)

    def test_irrelevant_private_and_evaluator_data_cannot_change_observations(self):
        name = "731-uncued"
        data = json.loads((ARCHIVE/"runs"/name/"take.json").read_text())
        edited = copy.deepcopy(data)
        for day in edited["days"]:
            for f in ("ending","evening","afternoon_state"):
                day[f] = {"malicious_test_value":"They danced and tomorrow is Wednesday"}
            for role in ("producer","camera"):
                day["afternoon"][role] = {"forbidden":"Phil would never see this"}
            day["afternoon"]["reporter"]["decision"] = {"invalid_as_source":True}
        edited["reporter_memory"] = ["The global record says Wednesday"]
        edited["external_receipt"] = ["A receipt Phil cannot observe"]
        self.assertEqual(primary_events(data,name),primary_events(edited,name))

    def test_no_spurious_trials_from_repeated_receipt_and_epilogue(self):
        perf = self.data["paths"]["721-hypothesis"]
        arrivals = perf["dated_receipt_assumption_sensitivity"]
        self.assertEqual(arrivals["first_visible_after_days"],[2])
        closed, alternate = [self.data["matched_epilogue"][k] for k in ("tuesday","wednesday")]
        for branch in (closed, alternate):
            self.assertEqual(branch["source_run"],"721-hypothesis")
            self.assertEqual(branch["source_day"],2)
            self.assertEqual(branch["actor_wake"]["exposure"],perf["wakes"][2]["exposure"])
        self.assertFalse(closed["actor_wake"]["advanced"])
        self.assertTrue(alternate["actor_wake"]["advanced"])
        self.assertAlmostEqual(closed["posterior_with_same_prior_prefix"]["coach"],1/82)
        self.assertAlmostEqual(alternate["posterior_with_same_prior_prefix"]["coach"],.5)


if __name__ == "__main__":
    unittest.main()
