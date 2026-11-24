"""Check the exact screen, held-out split, loss geometry and policy boundaries."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from learn import fit, legal, policy_checks, read_labels, sigmoid
from rehearsal import FEATURES, HELD_OUT, TASKS, deck, packet, run

BASE = Path(__file__).resolve().parent


class LabTests(unittest.TestCase):
    def test_blind_screen_and_receipt(self):
        root = BASE / 'archive'
        receipt = json.loads((root / 'receipt.json').read_text())
        for name, info in receipt['files'].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), info['byte_sha256'])
        self.assertEqual(packet(), json.loads((root / 'packet.json').read_text()))
        self.assertEqual(len(read_labels(root / 'ratings-agent.json')['ratings']), 45)
        self.assertTrue(all(set(row) == {'id','situation','A','B'} for row in packet()['comparisons']))
        self.assertEqual(len({row[0] for row in deck()}), 45)

    def test_whole_tasks_reserved_in_every_family(self):
        for mode in {t.mode for t in TASKS}:
            self.assertEqual(sum(t.mode==mode and t.key in HELD_OUT for t in TASKS), 1)
            self.assertEqual(sum(t.mode==mode and t.key not in HELD_OUT for t in TASKS), 2)
        self.assertEqual(sum(task.key in HELD_OUT for _,task,*_ in deck()), 15)

    def test_score_flip_and_indifference(self):
        # A numeric likelihood check independent of the authored screen and its rater.
        x = np.array([[1.,0],[-1,0],[0,1],[0,-1]])
        y = np.array([1.,0.,.5,.5])
        w = fit(x,y)
        self.assertGreater(w[0],0)
        self.assertAlmostEqual(w[1],0.)
        self.assertTrue(np.allclose(fit(-x,1-y), w))
        self.assertTrue(np.allclose(sigmoid(x @ w) + sigmoid(-x @ w),1.))

    def test_deadlines_without_consent_leakage(self):
        arch = next(t for t in TASKS if t.key=='negative')
        self.assertEqual(run(arch,'pa').features,(0.,1,1,0,0))
        self.assertEqual(run(arch,'ag').features,(0.,1,0,0,0))
        self.assertIn('too late',run(arch,'ag').clip)
        self.assertFalse(legal(arch, 'ww'))
        self.assertEqual(policy_checks(np.array([2.,3.,4.,100.,5.]))['refused_or_revoked_case_zero_mass_on_crossing'], 18)

    def test_blind_cli_resumes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            toy = {'instructions':'Interface fixture', 'comparisons':[
                {'id':str(i), 'situation':'fixture','A':'first','B':'second'} for i in range(2)]}
            screen = root / 'fixture.json'
            screen.write_text(json.dumps(toy))
            ratings = root / 'fixture-ratings.json'
            args = [sys.executable,str(BASE/'label.py'),str(screen),'--out',str(ratings),'--rater','test fixture','--type','agent']
            subprocess.run(args, input='skip\nquit\n', text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(ratings.read_text())['ratings'],{'0':'skip','1':''})
            subprocess.run(args, input='tie\n', text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(ratings.read_text())['ratings'],{'0':'skip','1':'tie'})


if __name__ == '__main__':
    unittest.main()
