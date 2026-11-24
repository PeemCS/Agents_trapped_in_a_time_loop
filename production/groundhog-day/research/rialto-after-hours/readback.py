"""Verify and transcribe the recorded performances without contacting the model."""
from pathlib import Path
import argparse
import hashlib
import json

from shoot import BASE, BOOTH, CARDS, CART, MODEL, printed, digest

ROOT=Path(__file__).resolve().parent

def load(path):
    return json.loads(path.read_bytes())

def assert_input(take, days, day, e):
    clock, role = e['time'],e['speaker']
    present=e['witnesses']
    if clock in ('16:40','18:48'):
        present=['Phil']  # The number is dialled after the choice.
    seen=[x for x in day['events'] if x['time']<clock and role in x['witnesses']]
    assert e['seen']==[x['id'] for x in seen]
    prior=[]
    if role=='Phil':
        prior.append('You remember reaching Pittsburgh, calling Jo about the van, then waking back in the hotel on Tuesday.')
        for past in days:
            prior.extend(printed(x) for x in past['events'] if role in x['witnesses'])
    assert e['prior_days']==(len(days) if role=='Phil' else 0)
    data={'clock':clock,'place':e['place'],'in_earshot':present,'role':role,'situation':e['cue'],
          'remembered_before_today':prior,'witnessed_today':[printed(x) for x in seen],'choices':e['choices']}
    schema={'type':'object','properties':{'choice':{'type':'string','enum':list(e['choices'])},'line':{'type':'string'}},'required':['choice','line'],'additionalProperties':False}
    seed=take*100000+day['day']*10000+int(clock.replace(':',''))
    assert e['sample_seed']==seed
    payload={'model':MODEL,'stream':False,'think':False,'messages':[{'role':'system','content':CARDS[role]+' '+BASE},{'role':'user','content':json.dumps(data,ensure_ascii=False)}],
             'format':schema,'options':{'temperature':.92,'seed':seed,'num_ctx':12288,'num_predict':230}}
    for size in (230,350,470):
        payload['options']['num_predict']=size
        if digest(payload)==e['input_sha256']:
            break
    else:
        raise ValueError('Unmatched model input '+e['id'])
    assert e['choice'] in e['choices'] and e['effect']==e['choices'][e['choice']]
    if e['origin']=='generated':
        raw=e['model_output']
        assert digest(raw)==e['answer_sha256']
        value=json.loads(raw)
        assert (value['choice'],value['line'].strip())==(e['choice'],e['line'])
    if e['place']=='locked Rialto booth':
        assert e['witnesses']==BOOTH and role!='Phil'
    if e['kind']=='voice memo':
        assert role=='Phil' and e['witnesses']==['Phil']

def check_day(d):
    events={e['time']:e for e in d['events']}
    assert len(events)==len(d['events'])
    assert list(events)==sorted(events)
    for t,col in [('07:20','cart'),('12:54','route'),('13:10','consent'),('18:55','equipment'),('19:00','wire')]:
        assert events[t]['choice']==d[col]
    assert ('load_cart' in events['18:55']['choices']) == (d['cart'] != 'pocket_cart')
    allowed={'silence'}
    if d['equipment']=='load_cart':allowed.add('weather')
    if d['equipment']=='set_mic' and d['consent']!='decline':allowed.add('private')
    if d['equipment']=='set_mic' and d['consent']=='public_too':allowed.add('public')
    assert set(events['19:00']['choices'])==allowed
    assert events['22:16']['witnesses']==['Phil']
    assert d['wire'] in allowed

def conversation(folder,days):
    rows=[f"# {folder.name.replace('-', ' ').title()}",'',
          'Verbatim dialogue and pocket-recorder performances. Bracketed text records the physical action resolved by the town. The witnesses column identifies who could hear the line.','']
    for day in days:
        rows.extend([f"## Tuesday {day['day']}",''])
        for e in day['events']:
            rows.extend([f"<a id=\"{e['id']}\"></a>",'',
                         f"**{e['time']} · {e['speaker']} · {e['place']}**  ",
                         f"Heard by {', '.join(e['witnesses'])}"+(' · Pocket recorder' if e['kind']=='voice memo' else '')+
                         (' · Matched intervention' if e['origin']=='silent experimental intervention' else ''),'',
                         '> '+(e['line'].replace('\n','\n> ') or '*(Silence.)*'), '',
                         f"[{e['effect']}]",''])
        rows.extend([f"[Source events for Tuesday {day['day']}](day-{day['day']:02}.json)",''])
    (folder/'transcript.md').write_text('\n'.join(rows))

def voice_memos(all_days):
    rows = ['# Phil’s pocket recorder', '',
            'These are performed, private recordings in the fiction. The other characters hear none of them. Each link opens the surrounding dialogue and the action that followed.', '']
    for name, days in all_days.items():
        if not name.startswith('take-'):
            continue
        rows.extend([f"## Take {name[5:]}", ''])
        for d in days:
            rows.extend([f"### Tuesday {d['day']}", ''])
            for e in d['events']:
                if e['kind'] != 'voice memo':
                    continue
                label = 'Hotel alarm' if e['time'] == '06:00' else 'After the radio slot'
                rows.extend([f"**{label}**", '', '> '+(e['line'].replace('\n','\n> ') or '*(Silence.)*'), '',
                             f"[{e['time']} · {e['place']}](performances/{name}/transcript.md#{e['id']})", ''])
    (ROOT/'voice-memos.md').write_text('\n'.join(rows))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transcribe',action='store_true')
    args=parser.parse_args()
    root=ROOT/'performances'
    meta=load(root/'manifest.json')
    assert meta['driver_sha256']==hashlib.sha256((ROOT/'shoot.py').read_bytes()).hexdigest()
    all_days={}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        take=int(folder.name.split('-')[1]) if folder.name.startswith('take') else 901
        days=[]
        for file in sorted(folder.glob('day-*.json')):
            d=load(file)
            assert d['day']==len(days)+1
            check_day(d)
            for e in d['events']:assert_input(take,days,d,e)
            days.append(d)
        assert len(days)==(4 if folder.name.startswith('take') else 1)
        all_days[folder.name]=days
        if args.transcribe:conversation(folder,days)
    assert set(all_days)=={'take-901','take-902','take-903','fork-pocket_cart','fork-leave_cart'}
    forks=[all_days['fork-'+k][0]['events'] for k in ('pocket_cart','leave_cart')]
    opening=all_days['take-901'][0]['events'][0]
    for f in forks:
        assert f[0]['input_sha256']==opening['input_sha256'] and f[0]['line']==opening['line'] and f[0]['choice']==opening['choice']
        assert f[1]['line']=='' and f[1]['origin']=='silent experimental intervention'
        assert f[2]['sample_seed']==all_days['take-901'][0]['events'][2]['sample_seed']
    assert forks[0][1]['input_sha256']==forks[1][1]['input_sha256'] and forks[0][1]['choice']!=forks[1][1]['choice']
    for name,days in all_days.items():
        print(name,len(days),'days,',sum(len(d['events']) for d in days),'turns,',', '.join(d['wire'] for d in days))
    if args.transcribe:voice_memos(all_days)
    print('Checked model input and output hashes, room witnesses, loop memories, consent rules and paired interventions.')
if __name__=='__main__':main()
