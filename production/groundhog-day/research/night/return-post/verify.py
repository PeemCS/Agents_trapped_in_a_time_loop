"""Independently reconstruct observations, legal decisions, state transitions and paired outcomes."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import median

import post
from shoot import MODEL, validate, atomic_json

HERE=post.HERE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_run(path):
    take=json.loads(path.read_bytes())
    assert take['model']==MODEL and sha(HERE/'protocol.md')==take['protocol_sha256']
    outside=post.empty_post();history=[];rows=[];calls=[];fingerprints={}
    count=Counter()
    for d in take['days']:
        n=d['day']; public=post.dawn(outside,take['authored_daughter_answer'],n)
        assert public==d['morning']
        local=None; acts={}; choices={}
        for i,phase in enumerate(('afternoon','evening')):
            if phase=='evening' and 'local' not in d:
                assert take['status']=='incomplete'
                break
            acts[phase]={}; choices[phase]={}
            for j,role in enumerate(post.ROLES):
                if role not in d[phase]:
                    assert take['status']=='incomplete'
                    continue
                turn=d[phase][role]
                seed=1930000+take['root']*91+n*17+i*3+j
                m, actions=post.messages(role,phase,public,local,history,seed)
                for ix, fil in enumerate(turn['attempts']):
                    wire=path.parent/fil['file']
                    assert sha(wire)==fil['sha256']
                    sample=json.loads(wire.read_bytes()); req=sample['request']; chunks=sample['chunks']
                    assert req['model']==MODEL and req['messages']==m and req['format']['properties']['action']['enum']==actions
                    assert req['think'] is False and req['options']['seed']==seed+ix
                    text=''.join(c['message']['content'] for c in chunks)
                    final=chunks[-1]
                    calls.append({'file':str(wire.relative_to(HERE)),'sha256':sha(wire),'stop':final.get('done_reason'),
                                  'input_tokens':final.get('prompt_eval_count',0),'output_tokens':final.get('eval_count',0),'wall_s':sample['wall_s']})
                    if ix<len(turn['attempts'])-1:
                        m=m+[{'role':'assistant','content':text},{'role':'user','content':'Return one listed action and three short, complete JSON strings.'}]
                assert final.get('done_reason')=='stop' and validate(text,actions)==turn['decision']
                fingerprints[(n,phase,role)]=hashlib.sha256(json.dumps(req,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                acts[phase][role]=turn['decision']; choices[phase][role]=turn['decision']['action']
            if phase=='afternoon' and len(acts[phase])==3:
                local=post.resolve_afternoon(acts[phase],public)
                assert local==d['local']
        if 'ending' not in d:
            assert take['status']=='incomplete'
            continue
        end=post.resolve_evening(acts['evening'],public,local,outside)
        assert end==d['ending']
        outside=end['outside']
        rows.append({'day':n,'morning_reply':public['reply'],'afternoon':choices['afternoon'],'evening':choices['evening'],
                     'recording_at_night':end['available_recording'],'settlement':end['settled'],'delivered':end['delivered']})
        count['morning_with_slip_offered']+=public['reply'] is None
        count['slip_carried']+=choices['afternoon']['reporter']==post.CARRY
        count['plain_coach']+=choices['afternoon']['reporter']=='take_coach'
        count['sister_called']+=choices['evening']['reporter']=='call_sister'
        count['reply_filed']+=choices['evening']['reporter']==post.FILE
        count['signed_mornings']+=public['reply'] is not None
        count['settled']+=end['settled'] is not None
        count['transmitted_with_acceptance']+=end['delivered']
        count['available_interviews']+=end['available_recording']
        count['fare_envelope_taken']+=local['fare_cash']
        history.append({'own_afternoon':local['effects']['reporter'],'own_evening':end['effects']['reporter']})
    if take['status']=='complete':
        assert post.dawn(outside,take['authored_daughter_answer'],len(rows)+1)==take['final_dawn']
    result={'run':path.parent.name,'model_digest':take['model_digest'],'take_sha256':sha(path),'status':take['status'],
            'finished_utc':take['finished_utc'],'started_utc':take['started_utc'],'counts':dict(count),'days':rows,'final_dawn':take.get('final_dawn'),'calls':calls}
    return result,fingerprints


def main():
    results={};fingerprints={}
    for path in sorted((HERE/'runs').glob('*/take.json')):
        results[path.parent.name],fingerprints[path.parent.name]=check_run(path)
    assert len(results)==4
    pairs={}
    for root in (2401,2402):
        a=results[f'{root}-accept'];b=results[f'{root}-decline']
        am=fingerprints[a['run']];bm=fingerprints[b['run']]
        same={key for key in am if key in bm and am[key]==bm[key]}
        paired_choices=sum(a['days'][day-1][phase][role]==b['days'][day-1][phase][role] for day,phase,role in same)
        pairs[str(root)]={'matched_slots':len(am.keys() & bm.keys()),'identical_full_requests':len(same),'identical_choices_on_those_requests':paired_choices}
    calls=[c for run in results.values() for c in run['calls']]
    totals=sum((Counter(r['counts']) for r in results.values()),Counter())
    keys=sorted({k for r in results.values() for k in r['counts']})
    summary={'provenance':'Native local 0.6B actor calls. Daughter answer, costs, and reset/settlement rules authored.',
             'runs':results,'paired_root_evidence':pairs,'totals':{k:totals[k] for k in keys},
             'primary_usage':{'calls':len(calls),'complete_takes':sum(r['status']=='complete' for r in results.values()),
             'distinct_model_revisions':sorted({r['model_digest'] for r in results.values()}),'input_tokens':sum(c['input_tokens'] for c in calls),
             'output_tokens':sum(c['output_tokens'] for c in calls),'median_wall_seconds':median(c['wall_s'] for c in calls),
             'stop_reasons':dict(Counter(c['stop'] for c in calls))}}
    atomic_json(HERE/'results.json',summary)
    print(summary['primary_usage']);print(summary['totals']);print(pairs)


if __name__=='__main__':
    main()
