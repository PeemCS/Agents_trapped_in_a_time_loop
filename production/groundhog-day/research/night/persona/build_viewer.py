"""Rebuild the portable, offline audit viewer from the four native generation archives."""
import json
from pathlib import Path
from analyze import load, read_choice
HERE=Path(__file__).resolve().parent
FILES={
    'Neutral base':'results/base_neutral.jsonl',
    'Cued base':'results/base_cued.jsonl',
    'First adapter':'results/adapter_neutral.jsonl',
    'Repaired adapter':'results/v2/native/adapter_neutral.jsonl',
}

def main():
    cases={}
    for actor,path in FILES.items():
        for line,r in enumerate(load(HERE/path),1):
            case=cases.setdefault(r['id'],dict(id=r['id'],setting=r['setting'],kind=r['kind'],prompt=r['messages'][1]['content'],
                                             menu=r.get('menu',[]),target=r.get('target'),actors=[]))
            assert case['prompt']==r['messages'][1]['content']
            label=read_choice(r['final']) if r['complete'] and r['reasoning_closed'] and r['kind']!='stage' else None
            case['actors'].append(dict(actor=actor,source=path,line=line,card=r['messages'][0]['content'],raw=r['raw_completion'],
                    tokens=r['token_ids'],reasoning=r['reasoning'],separator=r['reasoning_closed'],visible=r['final'],
                    status=r['finish_reason'],complete=r['complete'],label=label,limit=r['limit'],seed=r['seed']))
    assert len(cases)==36 and all(len(c['actors'])==4 for c in cases.values())
    payload=json.dumps(list(cases.values()),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    template=(HERE/'viewer.template.html').read_text()
    assert template.count('<!--AUDIT_DATA-->')==1
    (HERE/'viewer.html').write_text(template.replace('<!--AUDIT_DATA-->',payload))

if __name__=='__main__':
    main()
