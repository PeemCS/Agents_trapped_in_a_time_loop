"""Two frozen local single-choice pairs. They do not continue any complete crew take."""
import hashlib
import json
from pathlib import Path

import post
from prove import acts, day
from shoot import query, validate, atomic_json, MODEL, utc

HERE=post.HERE
PROBE=HERE/'probes'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def draw(name,messages,choices,seed):
    files=[]
    for retry in range(2):
        path=PROBE/(name+f'-{retry}.json')
        # An existing raw response is a resumable observation at exactly this checkpoint.
        if path.exists():
            sample=json.loads(path.read_bytes())
        else:
            try:
                sample=query(messages,choices,seed+retry)
            except OSError as error:
                atomic_json(path,{'error':str(error),'messages':messages,'seed':seed+retry,'utc':utc()})
                return {'status':'incomplete','error':str(error),'files':[{'file':path.name,'sha256':sha(path)}]}
            atomic_json(path,sample)
        files.append({'file':path.name,'sha256':sha(path)})
        if 'error' in sample:
            return {'status':'incomplete','error':sample['error'],'files':files}
        req=sample['request']
        assert req['messages']==messages and req['format']['properties']['action']['enum']==choices and req['options']['seed']==seed+retry
        value=''.join(c['message']['content'] for c in sample['chunks'])
        try:
            if sample['chunks'][-1].get('done_reason')!='stop':
                raise ValueError('Generation did not stop normally.')
            return {'status':'complete','decision':validate(value,choices),'files':files}
        except (ValueError,TypeError) as exc:
            if retry:
                return {'status':'incomplete','error':str(exc),'files':files}
            messages=messages+[{'role':'assistant','content':value},{'role':'user','content':'Return one listed action and three short, complete JSON strings.'}]


def replace_menu(messages, menu):
    data=json.loads(messages[1]['content'])
    data['physical_choices']=menu
    return [messages[0],{'role':'user','content':json.dumps(data,ensure_ascii=False,indent=1)}]


def main():
    PROBE.mkdir(exist_ok=True)
    root=HERE/'runs'/'2402-accept'
    archive=root/'d1-afternoon-reporter-0.json'
    old=json.loads(archive.read_bytes())['request']
    before=old['messages']; menu=json.loads(before[1]['content'])['physical_choices']
    after=dict(menu)
    after['take_coach']='Ride to Pittsburgh without the slip. At night you can call your sister, sleep, or wait at the terminal.'
    after[post.CARRY]='Ride to Pittsburgh with Alma’s slip. At night you can file the reply, call your sister, sleep, or wait at the terminal.'
    seed=old['options']['seed']
    plain=draw('phil-original',before,list(menu),seed)
    compact=draw('phil-explicit-coach-options',replace_menu(before,after),list(menu),seed)
    assert json.loads((PROBE/'phil-original-0.json').read_bytes())['request']==old
    source_turn=json.loads((root/'take.json').read_bytes())['days'][0]['afternoon']
    for variant in (plain,compact):
        if variant['status']=='complete':
            cast={role:turn['decision'] for role,turn in source_turn.items()}
            cast['reporter']=variant['decision']
            next_local=post.resolve_afternoon(cast,post.dawn(post.empty_post(),'accept',1))
            variant.update(effect=next_local['effects']['reporter'],slip_carried=next_local['carried'],location=next_local['positions']['reporter'])
    phil={'anchor':str(archive.relative_to(HERE)),'anchor_sha256':sha(archive),'original_recorded_decision':json.loads((root/'take.json').read_bytes())['days'][0]['afternoon']['reporter']['decision'],
          'seed':seed,'edited_descriptions':{k:{'original':menu[k],'explicit':after[k]} for k in menu if menu[k]!=after[k]},
          'baseline':plain,'explicit_evening_options':compact}
    prior=day(post.empty_post(),'accept',1,acts(post.CARRY,'visit_party','keep_battery'),acts(post.FILE,'take_evening_off','go_home'))['outside']
    seed=1930000+2402*91+2*17+3+post.ROLES.index('producer')
    rita={}
    for answer in ('accept','decline'):
        bulletin=post.dawn(prior,answer,2)
        local=post.resolve_afternoon(acts('stay_in_bed','interview_Alma','film_party'),bulletin)
        source,_=post.messages('producer','evening',bulletin,local,[],seed)
        available=post.menu('producer','evening',bulletin,local)
        common=['go_dancing','go_to_party_for_work','take_evening_off']
        names=common+[a for a in available if a not in common]
        messages=replace_menu(source,{a:available[a] for a in names})
        pick=draw('rita-signed-'+answer,messages,names,seed)
        if pick['status']=='complete':
            root_choices=acts('go_to_bed',pick['decision']['action'],'go_home')
            root_choices['producer']=pick['decision']
            ending=post.resolve_evening(root_choices,bulletin,local,prior)
            pick.update(effect=ending['effects']['producer'],delivered=ending['delivered'],settlement=ending['settled'],next_dawn=post.dawn(ending['outside'],answer,3))
        rita[answer]=pick
    result={'provenance':'Four supplementary local single-choice probes. Archived Phil checkpoint and constructed, reachable Rita checkpoint.',
            'model':MODEL,'probe_protocol_sha256':sha(HERE/'probe-protocol.md'),'phil':phil,'rita_seed':seed,'rita':rita}
    atomic_json(HERE/'probe-results.json',result)
    for name,p in [('phil-baseline',plain),('phil-explicit',compact),*rita.items()]:
        print(name,p['status'],p.get('decision',{}).get('action'),p.get('settlement'))


if __name__=='__main__':
    main()
