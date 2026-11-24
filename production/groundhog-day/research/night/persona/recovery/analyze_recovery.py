"""Summarize deployment repair, native v2 update, fresh transfer and branching trajectories."""
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from analyze import CONDS, OUT, group_stats, load, read_choice
from scenes import heldout, stage_cases

def summarize(rows):
    counts=group_stats(rows)
    counts.update(generated=len(rows),eos=sum(r['complete'] for r in rows),
                  closed_generated_thought=sum(r['reasoning_closed'] for r in rows),
                  nonempty_generated_thought=sum(bool((r['reasoning'] or '').strip()) for r in rows),
                  open_without_close_end=sum(r['complete'] and r['reasoning_status']=='unclosed' for r in rows))
    return counts

def compare(left,right):
    assert [r['id'] for r in left]==[r['id'] for r in right]
    pairs=[]
    for a,b in zip(left,right):
        ac=read_choice(a['final']) if a['complete'] else None
        bc=read_choice(b['final']) if b['complete'] else None
        if ac is not None and bc is not None:
            pairs.append((ac==a['target'],bc==b['target']))
    return dict(n_paired_valid=len(pairs),changed_toward_target=sum(not a and b for a,b in pairs),
                changed_away_from_target=sum(a and not b for a,b in pairs))

def verify_model(path):
    summary=json.loads((path/'training.json').read_text())
    data=(path/'adapter/adapter_model.safetensors').read_bytes()
    assert hashlib.sha256(data).hexdigest()==summary['adapter_sha256']
    n=int.from_bytes(data[:8],'little')
    meta=json.loads(data[8:8+n])
    params=0
    bs=0
    for k,v in meta.items():
        if k=='__metadata__': continue
        params+=math.prod(v['shape'])
        if '.lora_B.' in k:
            start,end=v['data_offsets']
            a=memoryview(data)[8+n+start:8+n+end].cast('f')
            bs+=int(any(p!=0 for p in a))
    assert params==summary['trainable_params'] and bs==summary['nonzero_b_matrices']
    return summary

def main():
    native_v2=load(OUT/'v2/native/adapter_neutral.jsonl')
    base=load(OUT/'base_neutral.jsonl')
    assert [r['id'] for r in native_v2]==[r['id'] for r in base]
    assert all(a['messages']==b['messages'] and a['seed']==b['seed'] for a,b in zip(base,native_v2))
    ab=lambda rows:[r for r in rows if r['kind']!='stage']
    rescue={c:load(OUT/'rescue'/(c+'.jsonl')) for c in ('base_off','v1_off')}
    assert all(a['messages']==b['messages'] and a['seed']==b['seed'] for a,b in zip(*rescue.values()))
    fresh={c:load(OUT/'v2/fresh'/(c+'.jsonl')) for c in ('base_native','v2_native')}
    assert all(a['messages']==b['messages'] and a['seed']==b['seed'] for a,b in zip(*fresh.values()))
    assert len(native_v2)==36 and all(len(a)==34 for a in rescue.values()) and all(len(a)==12 for a in fresh.values())
    for r in ab(native_v2)+fresh['v2_native']:
        if read_choice(r['final']):
            assert r['complete'] and r['reasoning_closed']
    first=verify_model(OUT)
    v2=verify_model(OUT/'v2')
    assert v2['adapter_sha256']!=first['adapter_sha256']
    assert load(OUT/'v2/teaching.jsonl')==load(OUT/'teaching.jsonl')
    assert len(load(OUT/'v2/native-teaching.jsonl'))==104
    losses=load(OUT/'v2/losses.jsonl')
    result=dict(rescue={c:summarize(rows) for c,rows in rescue.items()},
                rescue_change=compare(*rescue.values()),native_v2=summarize(native_v2),
                native_v2_change=compare(ab(base),ab(native_v2)),
                fresh_binary={c:summarize(rows) for c,rows in fresh.items()},
                fresh_change=compare(*fresh.values()),v2_sha256=v2['adapter_sha256'],
                v2_loss_first10=mean(r['loss'] for r in losses[:10]),v2_loss_last10=mean(r['loss'] for r in losses[-10:]))
    (OUT/'v2/recovery-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    main()
