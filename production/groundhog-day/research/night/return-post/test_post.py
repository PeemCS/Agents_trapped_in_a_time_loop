"""Specific regressions at the publication boundary and the two after-the-fact probes."""
from copy import deepcopy
from pathlib import Path
import json
import unittest

import post
from prove import acts, day


class PostTests(unittest.TestCase):
    def setUp(self):
        self.open=post.empty_post()
        self.first=post.dawn(self.open,'accept',1)
        self.am=acts(post.CARRY,'visit_party','keep_battery')
        self.pm=acts(post.FILE,'go_dancing','go_home')
        self.filed=day(self.open,'accept',1,self.am,self.pm)['outside']

    def test_hidden_sign_and_immutability_through_evening(self):
        local=post.resolve_afternoon(self.am,self.first)
        old=deepcopy(local)
        before=[post.messages(r,'evening',self.first,local,[],9) for r in post.ROLES]
        for night in (self.pm,acts('call_sister','take_evening_off','go_home')):
            post.resolve_evening(night,self.first,local,self.open)
        self.assertEqual(local,old)
        self.assertEqual(self.open,post.empty_post())
        self.assertEqual(before,[post.messages(r,'evening',post.dawn(self.filed,'decline',1),local,[],9) for r in post.ROLES])
        self.assertEqual(post.dawn(self.filed,'decline',2)['reply'],'decline')
        self.assertEqual(post.dawn(self.filed,'decline',3)['reply'],'decline')

    def test_cleared_recording_and_private_master_have_different_rights(self):
        pm=acts('go_to_bed',post.SEND,'deliver_reel')
        am=acts('stay_in_bed','visit_party','film_party')
        self.assertFalse(day(self.filed,'accept',2,am,pm)['delivered'])
        with self.assertRaises(ValueError):
            day(self.filed,'decline',2,am,pm)
        for closer in (post.RETURN,post.LOG):
            end=day(self.filed,'decline',2,am,acts('go_to_bed',closer,'go_home'))
            self.assertFalse(end['delivered'])
            self.assertEqual(post.dawn(end['outside'],'decline',3)['date'],'Wednesday')
            with self.assertRaises(ValueError):
                post.menu('producer','afternoon',post.dawn(end['outside'],'decline',3))

    def test_checkpoint_preserves_every_other_phil_input(self):
        def request(name):
            return json.loads((post.HERE/'probes'/name).read_bytes())['request']
        original=request('phil-original-0.json'); explicit=request('phil-explicit-coach-options-0.json')
        self.assertEqual(original,json.loads((post.HERE/'runs/2402-accept/d1-afternoon-reporter-0.json').read_bytes())['request'])
        body0=json.loads(original['messages'][1]['content']);body1=json.loads(explicit['messages'][1]['content'])
        m0,m1=body0.pop('physical_choices'),body1.pop('physical_choices')
        self.assertEqual(body0,body1)
        self.assertEqual(list(m0),list(m1))
        self.assertEqual({a for a in m0 if m0[a]!=m1[a]},{post.CARRY,'take_coach'})
        self.assertEqual(original['messages'][0],explicit['messages'][0])
        self.assertEqual({k:v for k,v in original.items() if k!='messages'}, {k:v for k,v in explicit.items() if k!='messages'})

    def test_rita_pair_matches_checkpoints_except_rights(self):
        def request(ans):
            return json.loads((post.HERE/'probes'/f'rita-signed-{ans}-0.json').read_bytes())['request']
        a,b = request('accept'),request('decline')
        self.assertEqual(a['options'],b['options'])
        self.assertEqual(a['messages'][0],b['messages'][0])
        aa,bb=[json.loads(v['messages'][1]['content']) for v in (a,b)]
        self.assertEqual(aa['what_you_observe'][1:],bb['what_you_observe'][1:])
        self.assertEqual(aa['your_own_prior_receipts'],bb['your_own_prior_receipts'])
        common={'go_dancing','go_to_party_for_work','take_evening_off'}
        self.assertEqual([(k,v) for k,v in aa['physical_choices'].items() if k in common],[(k,v) for k,v in bb['physical_choices'].items() if k in common])
        self.assertEqual(set(aa['physical_choices'])-common,{post.SEND})
        self.assertEqual(set(bb['physical_choices'])-common,{post.RETURN,post.LOG})


if __name__=='__main__':
    unittest.main()
