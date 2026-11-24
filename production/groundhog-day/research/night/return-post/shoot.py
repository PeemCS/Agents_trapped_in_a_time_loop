"""Sequential real local actors. All outputs and errors stay in this experiment."""
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import post

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'understudy'))
from run import HOST, MODEL, query, validate, atomic_json

assert HOST=='http://127.0.0.1:11434' and MODEL=='qwen3:0.6b'


def utc():
    return datetime.now(timezone.utc).isoformat()


def actor(folder,root,day,phase,role,bulletin,local,history):
    seed=1930000+root*91+day*17+('afternoon','evening').index(phase)*3+post.ROLES.index(role)
    messages, choices=post.messages(role,phase,bulletin,local,history,seed)
    attempts=[]
    for attempt in range(2):
        path=folder/f'd{day}-{phase}-{role}-{attempt}.json'
        try:
            sample=query(messages,choices,seed+attempt)
        except OSError as exc:
            atomic_json(path,{'messages':messages,'choices':choices,'seed':seed+attempt,'error':str(exc),'utc':utc()})
            raise
        atomic_json(path,sample)
        attempts.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        text=''.join(c['message']['content'] for c in sample['chunks'])
        try:
            if not sample['chunks'] or sample['chunks'][-1].get('done_reason')!='stop':
                raise ValueError('Incomplete generation.')
            return {'decision':validate(text,choices),'attempts':attempts}
        except (ValueError,TypeError) as exc:
            if attempt==1:
                raise ValueError(f'{path.name}: {exc}') from exc
            messages=messages+[{'role':'assistant','content':text},{'role':'user','content':'Return one listed action and three short, complete JSON strings.'}]


def shoot(root,answer,tag):
    folder=HERE/'runs'/f'{root}-{answer}'
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'take.json'
    if path.exists():
        return
    data={'study':'new return-post rule','root':root,'authored_daughter_answer':answer,'model':MODEL,'model_digest':tag['digest'],
          'protocol_sha256':hashlib.sha256((HERE/'protocol.md').read_bytes()).hexdigest(),'started_utc':utc(),'status':'running','days':[]}
    outside=post.empty_post(); history=[]
    try:
        for day in range(1,4):
            bulletin=post.dawn(outside,answer,day)
            record={'day':day,'morning':bulletin,'afternoon':{},'evening':{}}
            data['days'].append(record)
            for role in post.ROLES:
                record['afternoon'][role]=actor(folder,root,day,'afternoon',role,bulletin,None,history)
            local=post.resolve_afternoon({k:v['decision'] for k,v in record['afternoon'].items()},bulletin)
            record['local']=local
            for role in post.ROLES:
                record['evening'][role]=actor(folder,root,day,'evening',role,bulletin,local,history)
            ending=post.resolve_evening({k:v['decision'] for k,v in record['evening'].items()},bulletin,local,outside)
            record['ending']=ending
            outside=ending['outside']
            history.append({'own_afternoon':local['effects']['reporter'],'own_evening':ending['effects']['reporter']})
            if ending['settled']:
                break
        data['status']='complete'
        data['final_dawn']=post.dawn(outside,answer,day+1)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        data.update(status='incomplete',error=str(exc))
    data['finished_utc']=utc()
    atomic_json(path,data)
    print(root,answer,data['status'],len(data['days']),data.get('final_dawn',{}),flush=True)


if __name__=='__main__':
    with urllib.request.urlopen(HOST+'/api/tags',timeout=8) as reply:
        tag=next(m for m in json.load(reply)['models'] if m['name']==MODEL)
    assert tag['size']<650_000_000
    for root in (2401,2402):
        for answer in ('accept','decline'):
            shoot(root,answer,tag)
