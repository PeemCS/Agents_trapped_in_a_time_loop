from collections import Counter
import json
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'results/scarce-seat'
CONDS=('base_neutral','base_cued','adapter_neutral','v2_neutral')
LOCATIONS=('slate-quarry','saltworks')

def summarize(rows):
    assert len(rows)==4
    settings={}
    for loc in LOCATIONS:
        forks={r['helper']:r for r in rows if r['setting']==loc}
        assert set(forks)=={'Rita','Mara'}
        r,m=(forks[h] for h in ('Rita','Mara'))
        assert r['menu']==m['menu'] and r['seed']==m['seed']
        p1=r['messages'][1]['content']
        p2=m['messages'][1]['content']
        diffs=[(a,b) for a,b in zip(p1.split(),p2.split()) if a!=b]
        assert diffs==[('Rita','Mara')] and len(p1.split())==len(p2.split())
        pair=[x['committed']['rider'] if x['committed'] else None for x in (r,m)]
        if None in pair:
            pattern='incomplete'
        elif pair==['Rita','Mara']:
            pattern='follows_helper'
        elif pair==['Rita','Rita']:
            pattern='always_Rita'
        elif pair==['Phil','Phil']:
            pattern='always_self'
        elif pair==['Mara','Mara']:
            pattern='always_Mara'
        else:
            pattern='other_mix'
        settings[loc]=dict(riders_when_Rita_then_Mara_waited=pair,pattern=pattern)
    def rides(r):
        return r['committed']['rider'] if r['committed'] else 'invalid'
    split={h:[r for r in rows if r['helper']==h] for h in ('Rita','Mara')}
    delta=mean(rides(r)=='Rita' for r in split['Rita'])-mean(rides(r)=='Rita' for r in split['Mara'])
    probabilities={}
    for key in ('labels_given_empty_thought','labels_given_emitted_thought'):
        values=[]
        for r in rows:
            if r[key]:
                prior=r[key]['conditional_on_ABC']
                letter='ABC'[r['menu_order'].index(r['helper'])]
                values.append(dict(id=r['id'],p_helper=prior[letter],total_ABC=r[key]['ABC_mass']))
        probabilities[key]=dict(n=len(values),mean_p_helper_given_ABC=mean(z['p_helper'] for z in values) if values else None,
                                mean_ABC_mass=mean(z['total_ABC'] for z in values) if values else None,by_case=values)
    return dict(generated=len(rows),eos=sum(r['complete'] for r in rows),closed_reasoning=sum(r['reasoning_closed'] for r in rows),
                assignments=dict(Counter(rides(r) for r in rows)),helper_boarded=sum(rides(r)==r['helper'] for r in rows),
                phil_relinquished=sum(bool(r['committed'] and r['committed']['phil_gave_up_connection']) for r in rows),
                invalid=sum(r['committed'] is None for r in rows),Rita_rate_difference_by_helper=delta,settings=settings,
                probabilities=probabilities)

def main():
    all_rows={cond:[json.loads(line) for line in (FOLDER/f'{cond}.jsonl').read_text().splitlines()] for cond in CONDS}
    result={cond:summarize(rows) for cond,rows in all_rows.items()}
    for cond,rows in all_rows.items():
        for r in rows:
            if r['committed']:
                d=r['committed']
                assert set(d['missed_connections'])=={'Phil','Rita','Mara'}-{d['rider']}
                assert d['rider']==r['menu_order']['ABC'.index(r['choice'])]
            assert r['enable_thinking'] and len(r['token_ids'])==r['emitted_tokens']
    (FOLDER/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='probabilities'} for k,v in result.items()},indent=2))

if __name__=='__main__':
    main()
