"""Verify the recorded choices, nightly transmission, alternate draws and film quotations."""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent / "night/last-reel"))
from scene import afternoon, evening


def read(path):
    return json.loads(path.read_text())


def key(payload):
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def main():
    takes = {}
    initial = {}
    for seed in range(841,847):
        folder = HERE / "runpod" / f"rialto-{seed}"
        take = read(folder/"take.json")
        assert take['status']=='complete' and len(take['days'])==3
        assert take['performance']['model']=='qwen3.8:27b'
        assert len(list(folder.glob('day-*.json')))==19
        for path in folder.glob('day-*.json'):
            _,n,period,role=path.stem.split('-')
            rec = take['last_alarm'] if period=='alarm' else take['days'][int(n)-1][period][role]
            raw=read(path)
            request,response=raw['request'],raw['response']
            assert response['done_reason']=='stop'
            assert rec['key']==key(request) and raw['revision']==take['performance']['digest']
            assert rec['messages']==request['messages']
            parsed=json.loads(response['message']['content'])
            assert parsed==rec['decision'] and parsed['action'] in request['format']['properties']['action']['enum']
            if n=='1' and period=='afternoon':
                condition=(take['condition'],role)
                assert initial.setdefault(condition,request['messages'])==request['messages']
        for d in take['days']:
            state=afternoon({r:t['decision'] for r,t in d['afternoon'].items()})
            assert state==d['afternoon_state']
            assert evening({r:t['decision'] for r,t in d['evening'].items()},state)==d['ending']
        takes[seed]=take

    parent=takes[841]['days'][0]
    raw=read(HERE/'runpod/rialto-841/day-1-evening-producer.json')['request']
    branches=read(HERE/'runpod/evening-replay.json')['draws']
    assert len(branches)==6 and len({b['seed'] for b in branches})==6
    for b in branches:
        assert b['request']=={**raw,'options':{**raw['options'],'seed':b['seed']}}
        replacement=json.loads(b['response']['message']['content'])
        cast={r:t['decision'] for r,t in parent['evening'].items()}
        cast['producer']=replacement
        assert b['resolved']==evening(cast,parent['afternoon_state'])

    summary = read(HERE / 'results.json')
    for row in summary['takes']:
        take = takes[row['take']]
        assert row['decisions'] == 19
        assert row['premise'] == take['condition']
        assert row['daily_delivery'] == [d['ending']['delivered'] for d in take['days']]
        assert row['phil_evenings'] == [d['evening']['reporter']['decision']['action'] for d in take['days']]
    assert {row['take'] for row in summary['takes']} == set(takes)
    fork = summary['same_evening_replay']
    assert fork['original_action'] == parent['evening']['producer']['decision']['action']
    assert fork['original_delivery'] == parent['ending']['delivered']
    assert fork['draws'] == len(branches)
    assert fork['deliveries'] == sum(b['resolved']['delivered'] for b in branches)

    earlier = read(HERE / 'earlier-721.json')
    assert earlier['take'] == 721 and earlier['day'] == 1
    assert earlier['afternoon']['reporter']['action'] == 'rehearse_piano'
    assert earlier['evening']['reporter']['action'] == 'sit_at_depot'
    assert earlier['evening']['producer']['action'] == 'go_dancing'
    assert earlier['afternoon_state'] == afternoon(earlier['afternoon'])
    assert earlier['ending'] == evening(earlier['evening'], earlier['afternoon_state'])

    edit=read(HERE/'cut.json')
    assert sum(s['seconds'] for s in edit)==180
    for s in edit:
        if not s['voice'] or s['voice']=='Narrator':continue
        match=re.fullmatch(r'(\d+)/(\d+)/(afternoon|evening)/(\w+)',s['source'])
        seed,day,period,role=match.groups()
        assert s['text'] in takes[int(seed)]['days'][int(day)-1][period][role]['decision']['words']
    alarm=json.loads(takes[841]['last_alarm']['messages'][1]['content'])
    assert any("I know that voice. Play it again." in line for line in alarm['what_you_observe'])
    print('6 complete takes · 114 recorded decisions · 6 matched replays · all nightly outcomes and voiced character lines verified')


if __name__=='__main__':
    main()
