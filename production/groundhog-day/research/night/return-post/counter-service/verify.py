"""Check the fresh wire archives, eligible denominators, timing and consent branches."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json

import counters as world

HERE=world.HERE


def canonical(object_):
    return hashlib.sha256(json.dumps(object_,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def reject(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('Unexpectedly accepted an unreachable action.')


def exercise(context):
    paths=Counter()
    for sign in ('accept','decline'):
        for ready in (False,True):
            c={**context,'recording_available_at_checkout':ready}
            start=world.initial()
            reject(lambda: world.next_morning(start,c,sign))
            reject(lambda: world.apply(start,'terminal',world.FILE,c))
            for a in world.available('ticket',c):
                s=deepcopy(start);world.apply(s,'ticket',a,c)
                if s['stage']=='end':
                    assert s['published'] is None and not s['settlement']
                    paths[(sign,ready,s['ending'])]+=1;continue
                for b in world.available('terminal',c):
                    t=deepcopy(s);world.apply(t,'terminal',b,c)
                    assert t['published'] is None
                    if t['stage']=='end':
                        assert not t['settlement'];paths[(sign,ready,t['ending'])]+=1;continue
                    world.next_morning(t,c,sign)
                    if t['stage']=='end':
                        assert sign=='accept' and not ready;paths[(sign,ready,t['ending'])]+=1;continue
                    for d in world.available('desk',c,sign):
                        u=deepcopy(t);world.apply(u,'desk',d,c,sign)
                        assert u['transmitted']==(sign=='accept' and ready and d==world.SEND)
                        assert bool(u['settlement'])==(d!=world.SHUTTLE)
                        paths[(sign,ready,u['ending'])]+=1
                    other=world.DECLINE if sign=='accept' else world.SEND
                    reject(lambda: world.apply(deepcopy(t),'desk',other,c,sign))
    return [{'sign':sign,'ready':ready,'ending':ending,'path_count':n} for (sign,ready,ending),n in sorted(paths.items())]


def main():
    totals={s:Counter() for s in ('accept','decline')}; rows=[]; requests=defaultdict(dict);raws=[]
    paths=sorted((HERE/'runs').glob('*/take.json'))
    assert len(paths)==8
    for path in paths:
        t=json.loads(path.read_bytes());sign=t['authored_answer'];micro=t['micro_seed'];source=t['source_context']
        assert t['protocol_sha256']==world.sha(HERE/'protocol.md') and source==world.source_context(source['root'],sign)
        st=world.initial();counts=totals[sign];counts['enrolled']+=1
        for idx,stage in enumerate(('ticket','terminal','desk')):
            if st['stage']=='overnight': world.next_morning(st,source,sign)
            if st['stage']=='end':
                assert stage not in t['turns'];continue
            assert st['stage']==stage
            turn=t['turns'][stage]; seed=micro*31+3*idx
            m,choices=world.prompt(stage,source,seed,sign if stage=='desk' else None)
            for ix,f in enumerate(turn['attempts']):
                file=path.parent/f['file'];assert world.sha(file)==f['sha256']
                sample=json.loads(file.read_bytes());req=sample['request'];chunks=sample['chunks'];last=chunks[-1]
                assert req['messages']==m and req['options']['seed']==seed+ix and req['model']==world.MODEL and req['format']['properties']['action']['enum']==choices
                req_hash=canonical(req)
                requests[(micro,stage)][sign]=req_hash
                raw_text=''.join(k['message']['content'] for k in chunks)
                raws.append({'file':str(file.relative_to(HERE)),'sha256':f['sha256'],'request_sha256':req_hash,'input_tokens':last['prompt_eval_count'],'output_tokens':last['eval_count'],'stop':last['done_reason']})
                if ix<len(turn['attempts'])-1:
                    m += [{'role':'assistant','content':raw_text},{'role':'user','content':'Return one listed action and three short, complete JSON strings.'}]
            if turn['status']!='complete':
                st.update(stage='end',ending='invalid_'+stage);break
            assert last['done_reason']=='stop' and world.validate(raw_text,choices)==turn['decision']
            world.apply(st,stage,turn['decision']['action'],source,sign if stage=='desk' else None)
        assert st==t['state']
        counts['envelope_taken']+=st['envelope_taken'];counts['terminal_opportunities']+='terminal' in t['turns'];counts['reply_filed']+=st['pending_reply']
        counts['published_next_morning']+=st['published'] is not None;counts['eligible_desk_choices']+='desk' in t['turns']
        counts['settled']+=st['settlement'] is not None;counts['left_at_ticket_counter']+=st['ending']=='left_at_ticket_counter';counts['walked_past_post']+=st['ending']=='walked_past_post'
        row={'root':source['root'],'micro_seed':micro,'daughter_answer':sign,'source_day':source['day'],'following_recording_at_patch':source['recording_available_at_checkout'],
             'choices':{stage:turn.get('decision',{}).get('action') for stage,turn in t['turns'].items()},'ending':st['ending'],'next_date':t['next_date_after_following_shift'],'take_sha256':world.sha(path)}
        rows.append(row)
    pairs=[(key,by_sign) for key,by_sign in requests.items() if key[1] in ('ticket','terminal') and len(by_sign)==2]
    assert all(d['accept']==d['decline'] for _,d in pairs)
    out={'provenance':'Eight conditional forks over real ordinary coach choices from two sources. The local model selected each micro-action. Source shifts are held fixed.',
         'rows':rows,'counts_by_sign':totals,'paired_prepublication_identical_requests':len(pairs),
         'total_native_calls':len(raws),'usage':{'input_tokens':sum(v['input_tokens'] for v in raws),'output_tokens':sum(v['output_tokens'] for v in raws)},
         'engineered_paths':exercise(source),'wire':raws}
    world.atomic_json(HERE/'results.json',out)
    print({s:dict(v) for s,v in totals.items()},len(raws),out['usage'])


if __name__=='__main__':
    main()
