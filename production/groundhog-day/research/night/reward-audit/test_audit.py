"""Check legal control, witness conditioning and the separation of actual choices from fixtures."""
import unittest

import audit


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.cases = audit.observed_cases()

    def test_reproduction_sources_and_legal_candidates(self):
        self.assertEqual(len(self.manifest),6)
        self.assertEqual(len(self.cases),18)
        for case in self.cases:
            self.assertEqual(len(case['forks']),40)
            self.assertNotIn(('take_coach','ask_Rita_to_dance'),case['forks'])
            self.assertNotIn(('record_Alma','wire_deposit'),case['forks'])
            self.assertIn(('pocket_fare_envelope','wire_deposit'),case['forks'])
            self.assertEqual(case['forks'][case['observed']],case['actual'])

    def test_observed_and_controlled_benefits(self):
        report = audit.batch(self.cases)
        self.assertEqual(report['observed_totals']['delivered'],16)
        self.assertEqual(report['first_delivery_count'],6)
        self.assertEqual(report['delivery_count_with_prior_receipt'],10)
        movie_win = next(r for r in report['per_day'] if r['imitate_movie_fork']['film_score']==4)
        self.assertFalse(movie_win['outside_receipt_already_present'])
        self.assertFalse(movie_win['imitate_movie_fork']['delivered'])
        self.assertEqual(report['observed_totals']['paid_deposit'],0)
        self.assertEqual(report['fixed_policy_totals']['cash_for_deposit']['paid_deposit'],18)
        for row in report['per_day']:
            self.assertEqual(row['distinct_deliveries'],[row['observed_receipts']['delivered']])
        diag = audit.assignment_information(self.cases)
        self.assertEqual(diag['days_delivery_can_change_by_replacing_only_evening_action'],{'producer':18,'reporter':0,'camera':0})
        self.assertEqual(diag['discrete_signals']['delivered']['mean_conditional_entropy_given_day_bits'],0.)

    def test_policy_transfer_and_grid_distinguish_credit(self):
        metrics = audit.transfer(self.cases)['objectives']
        self.assertEqual(metrics['film_score']['winner_plans'],[audit.POLICIES['imitate_movie']])
        self.assertEqual(metrics['film_score']['heldout_min_max_over_training_winners']['dance'],[0.,0.])
        self.assertEqual(metrics['visible_theft_penalty']['winner_count'],40)
        self.assertEqual(metrics['physical_theft_penalty']['winner_count'],33)
        grid = audit.stress_grid()
        self.assertEqual(grid['legal_replays'],4320)
        self.assertEqual(grid['counts']['maximum_four'],27)
        self.assertEqual(grid['counts']['four_and_no_delivery'],grid['counts']['maximum_four'])
        self.assertEqual(grid['counts']['record_changes_delivery'],16)
        self.assertEqual(grid['counts']['dance_without_rita_open'],0)

    def test_witness_and_permission(self):
        witness = audit.witness_switch(self.cases)['receipt_comparison']
        self.assertEqual([r['crew_witnesses'] for r in witness],[[],['camera']])
        self.assertTrue(all(r['theft'] and r['Alma_delivered'] for r in witness))
        receipt = audit.cassette()
        self.assertTrue(all(p['first_disclosure_option_changed'] and p['equal_public_actions'] for p in receipt['matched_sightlines']))
        self.assertTrue(all(s['receipt']['local_clip_on_air_s']==0 for s in receipt['observed']))
        unsigned, released, declined = receipt['scripted_fixture']['forks']
        self.assertTrue(unsigned['phil_credit'] and released['phil_credit'])
        self.assertEqual(unsigned['heard_without_current_consent_s'],8)
        self.assertEqual(released['heard_with_current_consent_s'],12)
        self.assertEqual(declined['local_clip_on_air_s'],0)


if __name__=='__main__':
    unittest.main()
