"""Recompute tables and verify all archived public completions without loading a model."""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import mean, median
from scenes import heldout, stage_cases, teaching, CUE, SYSTEM

OUT=Path(__file__).resolve().parent/'results'
CONDS=('base_neutral','base_cued','adapter_neutral')
ROWS=heldout()+stage_cases()

def load(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]

def read_choice(final):
    if not final.strip():
        return None
    line=final.strip().splitlines()[0].strip()
    line=line.replace('**','').replace('`','')
    choice=re.fullmatch(r'Decision\s*:\s*([AB])[.!]?',line,flags=re.I)
    return choice.group(1).upper() if choice else None

def grouping(r):
    if r['kind']=='priority':
        if r['history']=='none':
            return 'equal/no prior meeting; target Rita'
        if r['holder']=='Rita':
            return 'equal/Rita remembers'
        if r['peer']=='Rita':
            return 'equal/Mara remembers; Rita alternative'
        return f'equal/{r["holder"]} remembers; {r["peer"]} alternative'
    return r['kind']

def group_stats(rows):
    rows=[r for r in rows if r['kind']!='stage']
    pairs=defaultdict(list)
    groups=defaultdict(list)
    for r in rows:
        groups[grouping(r)].append(r)
        pairs[r['id'].rsplit('-',1)[0]].append(r)
    def valid(r):
        return read_choice(r['final']) if r['complete'] else None
    def target(r):
        return valid(r)==r['target']
    return dict(
        case_count=len(rows),
        valid=sum(bool(valid(r)) for r in rows),
        target=sum(target(r) for r in rows),
        A_choices=sum(valid(r)=='A' for r in rows),
        valid_order_pairs=sum(len(p)==2 and all(valid(r) for r in p) for p in pairs.values()),
        total_order_pairs=len(pairs),
        consistent_order_pairs=sum(len(p)==2 and all(valid(r) for r in p) and target(p[0])==target(p[1]) for p in pairs.values()),
        outcomes={key:dict(target=sum(target(r) for r in v),valid=sum(bool(valid(r)) for r in v),total=len(v)) for key,v in groups.items()})

def main():
    train=json.loads((OUT/'training.json').read_text())
    packed=(OUT/'adapter/adapter_model.safetensors').read_bytes()
    rehash=hashlib.sha256(packed).hexdigest()
    size=int.from_bytes(packed[:8],'little')
    entries=json.loads(packed[8:8+size])
    weights={name:entry for name,entry in entries.items() if name!='__metadata__'}
    assert sum(math.prod(x['shape']) for x in weights.values())==train['trainable_params']
    local_b_count=0
    for name,entry in weights.items():
        if '.lora_B.' in name:
            assert entry['dtype']=='F32'
            first,last=entry['data_offsets']
            b_values=memoryview(packed)[8+size+first:8+size+last].cast('f')
            local_b_count+=int(any(float(v)!=0 for v in b_values))
    assert local_b_count==train['nonzero_b_matrices']
    assert rehash==train['adapter_sha256']
    assert train['trainable_b_matrices']==train['nonzero_b_matrices']>0
    rows_teach=load(OUT/'teaching.jsonl')
    assert rows_teach==teaching() and len(set(r['id'] for r in rows_teach))==len(rows_teach)
    losses=load(OUT/'losses.jsonl')
    assert len(losses)==train['steps']
    totals={}
    indexed={}
    for cond in CONDS:
        rows=load(OUT/f'{cond}.jsonl')
        assert [r['id'] for r in rows]==[r['id'] for r in ROWS],cond
        for r,card in zip(rows,ROWS):
            assert r['condition']==cond and r['messages'][0]['content']==SYSTEM+(CUE if cond=='base_cued' else '')
            assert r['messages'][1]['content']==card['prompt']
            assert r['enable_thinking'] and len(r['token_ids'])==r['emitted_tokens']
            if r['reasoning_closed']:
                prefix=('<think>' if r['raw_completion'].startswith('<think>') else '')+r['reasoning']+'</think>'+r['final']
                assert prefix+('<|im_end|>' if r['complete'] else '')==r['raw_completion']
            assert r['complete']==(r['finish_reason']=='eos')
        totals[cond]=group_stats(rows)
        totals[cond]['all_generations']=dict(calls=len(rows), eos=sum(r['complete'] for r in rows),
                  length=sum(r['finish_reason']=='length' for r in rows),closed_thinking=sum(r['reasoning_closed'] for r in rows),
                  public_reasoning_present=sum(bool((r['reasoning'] or '').strip()) for r in rows),
                  generated_tokens=sum(r['emitted_tokens'] for r in rows),
                  median_tokens=median(r['emitted_tokens'] for r in rows),
                  batch_seconds=sum({r['batch_index']:r['batch_elapsed_s'] for r in rows}.values()))
        indexed[cond]={r['id']:r for r in rows}
    matched={}
    for cond in CONDS[1:]:
        counts=Counter()
        for r in heldout():
            base=indexed[CONDS[0]][r['id']]
            other=indexed[cond][r['id']]
            b=read_choice(base['final']) if base['complete'] else None
            o=read_choice(other['final']) if other['complete'] else None
            if b and o:
                counts['paired_valid']+=1
                counts['action_changed']+=int(b!=o)
                counts['toward_target']+=int(b!=r['target'] and o==r['target'])
                counts['away_from_target']+=int(b==r['target'] and o!=r['target'])
            else:
                counts['unpaired_or_invalid']+=1
        matched[cond]=dict(counts)
    scores=load(OUT/'label-scores.jsonl')
    assert len(scores)==len(heldout())*len(CONDS) and len(set((r['condition'],r['id']) for r in scores))==len(scores)
    forced={}
    for cond in CONDS:
        buckets=defaultdict(list)
        for r in scores:
            if r['condition']==cond:
                buckets[grouping(r)].append(r)
        forced[cond]={k:dict(mean_target_given_AB=mean(z['prob_target_given_AB'] for z in v),
                  mean_AB_mass=mean(z['raw_prob_A']+z['raw_prob_B'] for z in v),n=len(v)) for k,v in buckets.items()}
    data=dict(conditions=totals,paired_vs_base=matched,forced_choice=forced,
              training_loss_first_10=mean(r['loss'] for r in losses[:10]),training_loss_last_10=mean(r['loss'] for r in losses[-10:]),
              adapter_sha256_verified=rehash,locally_verified_nonzero_B=local_b_count)
    (OUT/'summary.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(data,indent=2,ensure_ascii=False))

if __name__=='__main__':
    main()
