"""Run from this directory on the H100 with a local, pinned Qwen checkpoint in base/."""
import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import random
import re
import time

import torch
from peft import LoraConfig, TaskType, get_peft_model, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from scenes import SYSTEM, CUE, teaching, heldout, stage_cases

BASE = 'Qwen/Qwen3-1.7B'
REVISION = '70d244cc86ccca08cf5af4e1e306ecf908b1ad5e'
SEED = 23112026
CAP_GIB = 10.75
OUT = Path('results')
CONDS = ('base_neutral', 'base_cued', 'adapter_neutral')

def write_json(file, data):
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def append(file, row):
    with file.open('a') as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + '\n')

def setup():
    torch.manual_seed(SEED)
    torch.set_num_threads(2)
    full = torch.cuda.get_device_properties(0).total_memory
    torch.cuda.set_per_process_memory_fraction(CAP_GIB * 1024**3 / full)
    OUT.mkdir(exist_ok=True)
    tok = AutoTokenizer.from_pretrained('base', local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained('base', local_files_only=True, torch_dtype=torch.bfloat16, attn_implementation='sdpa').to('cuda')
    return tok, model

def messages(scene, cue=False):
    return [dict(role='system', content=SYSTEM + (CUE if cue else '')), dict(role='user', content=scene['prompt'])]

def encode_example(tok, scene):
    # Use the official empty-thought template for teacher-forced visible dialogue.
    head = tok.apply_chat_template(messages(scene), tokenize=True, add_generation_prompt=True, enable_thinking=False)
    tail = tok.encode(scene['teaching_completion'], add_special_tokens=False) + [tok.eos_token_id]
    return head + tail, [-100] * len(head) + tail

def collate(rows, pad):
    n = max(len(ids) for ids, _ in rows)
    ids = [x + [pad] * (n-len(x)) for x, _ in rows]
    masks = [[1]*len(x) + [0]*(n-len(x)) for x, _ in rows]
    labels = [labels + [-100] * (n-len(labels)) for _, labels in rows]
    return {k:torch.tensor(v, device='cuda') for k,v in [('input_ids',ids),('attention_mask',masks),('labels',labels)]}

def train(tok, model, encode=encode_example, output_dir=OUT):
    output_dir.mkdir(exist_ok=True, parents=True)
    if (output_dir/'adapter').exists() or (output_dir/'losses.jsonl').exists():
        raise SystemExit('A training run exists; use a fresh working directory.')
    started=time.time()
    rows = teaching()
    for row in rows:
        append(output_dir/'teaching.jsonl',row)
    inputs = [encode(tok,r) for r in rows]
    recipe=LoraConfig(task_type=TaskType.CAUSAL_LM, r=8, lora_alpha=16, lora_dropout=0.05,
                      target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','down_proj'])
    model = get_peft_model(model,recipe)
    model.train()
    model.config.use_cache=False
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params,lr=0.00015,weight_decay=0.01)
    rng = random.Random(SEED)
    batch_size=2
    epochs=2
    total_steps=epochs*math.ceil(len(rows)/batch_size)
    warmup=8
    total_tokens=0
    step=0
    for epoch in range(epochs):
        order=list(range(len(rows)))
        rng.shuffle(order)
        for i in range(0,len(order),batch_size):
            step+=1
            indices=order[i:i+batch_size]
            batch=collate([inputs[j] for j in indices],tok.pad_token_id)
            rate=0.00015 * min(step/warmup,1) * (0.25+0.75*(1+math.cos(math.pi*max(0,step-warmup)/(total_steps-warmup)))/2)
            opt.param_groups[0]['lr']=rate
            opt.zero_grad(set_to_none=True)
            loss=model(**batch).loss
            loss.backward()
            grad_norm=torch.nn.utils.clip_grad_norm_(params,1.0)
            opt.step()
            total_tokens+=int((batch['labels']!=-100).sum())
            record=dict(step=step,epoch=epoch+1,loss=loss.item(),grad_norm=float(grad_norm),learning_rate=rate,
                        examples=[rows[j]['id'] for j in indices])
            append(output_dir/'losses.jsonl',record)
            if step%10==0: print('SFT',step,round(record['loss'],4),flush=True)
    model.save_pretrained(output_dir/'adapter')
    cfg=output_dir/'adapter/adapter_config.json'
    conf=json.loads(cfg.read_text())
    conf['base_model_name_or_path']=BASE
    conf['revision']=REVISION
    write_json(cfg,conf)
    (output_dir/'adapter/README.md').unlink(missing_ok=True)
    weightfile=output_dir/'adapter/adapter_model.safetensors'
    bmodules=[p.detach().float().norm().item() for name,p in model.named_parameters() if '.lora_B.' in name]
    write_json(output_dir/'training.json',dict(base=BASE,revision=REVISION,seed=SEED,examples=len(rows),epochs=epochs,steps=step,
               optimizer='AdamW',microbatch=batch_size,lr_peak=0.00015,warmup_steps=warmup,weight_decay=0.01,max_grad_norm=1.0,
               tokens_supervised=total_tokens,model_params=sum(p.numel() for p in model.parameters()),trainable_params=sum(p.numel() for p in params),
               dtype='bfloat16 base; PEFT default FP32 trainable adapter',trainable_b_matrices=len(bmodules),nonzero_b_matrices=sum(v>0 for v in bmodules),
               adapter_sha256=hashlib.sha256(weightfile.read_bytes()).hexdigest(),adapter_bytes=weightfile.stat().st_size,
               train_seconds=round(time.time()-started,2),allocator_cap_GiB=CAP_GIB,
               peak_allocated_GiB=torch.cuda.max_memory_allocated()/1024**3,peak_reserved_GiB=torch.cuda.max_memory_reserved()/1024**3,
               torch=torch.__version__,gpu=torch.cuda.get_device_name(),libraries={key:importlib.metadata.version(key) for key in ('transformers','peft','accelerate','huggingface-hub')}))
    print('Adapter saved.',flush=True)

def digest_tokens(tok, ids, limit):
    # Preserve every emitted token including the first EOS, discarding only library-inserted batch padding after EOS.
    if tok.eos_token_id in ids:
        ids=ids[:ids.index(tok.eos_token_id)+1]
        stop='eos'
    else:
        stop='length' if len(ids)==limit else 'unknown'
    raw=tok.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
    visible=raw.removesuffix(tok.eos_token)
    before,close,after=visible.partition('</think>')
    thinking=before.removeprefix('<think>') if close or before.startswith('<think>') else None
    final=after if close else ('' if thinking is not None else visible)
    pattern=r'^\s*(?:\*\*)?Decision\s*:\s*(?:\*\*)?([AB])\b'
    m=re.match(pattern,final,re.IGNORECASE)
    return dict(token_ids=ids,raw_completion=raw,emitted_tokens=len(ids),finish_reason=stop,limit=limit,
                reasoning=thinking,reasoning_closed=bool(close),reasoning_status=('closed' if close else 'unclosed' if thinking is not None else 'absent'),final=final,
                choice=m.group(1).upper() if m else None,complete=(stop=='eos'))

@torch.inference_mode()
def evaluate(tok,base,selection,source=OUT,output_dir=OUT):
    output_dir.mkdir(exist_ok=True,parents=True)
    model=PeftModel.from_pretrained(base,source/'adapter')
    model.eval()
    model.config.use_cache=True
    tok.padding_side='left'
    scenes=heldout()+stage_cases()
    batch_size=6
    limit=1536
    for cond in selection:
        path=output_dir/f'{cond}.jsonl'
        existing=[json.loads(line)['id'] for line in path.read_text().splitlines()] if path.exists() else []
        if existing != [r['id'] for r in scenes[:len(existing)]]:
            raise RuntimeError('Existing take differs from this script.')
        if len(existing)!=len(scenes) and len(existing)%batch_size:
            raise RuntimeError('Partial batch; inspect IDs before resuming.')
        enabled=cond=='adapter_neutral'
        with (contextlib.nullcontext() if enabled else model.disable_adapter()):
            for i in range(len(existing),len(scenes),batch_size):
                batch=scenes[i:i+batch_size]
                prompts=[messages(row,cond=='base_cued') for row in batch]
                texts=[tok.apply_chat_template(m,tokenize=False,enable_thinking=True,add_generation_prompt=True) for m in prompts]
                encoded=tok(texts,return_tensors='pt',padding=True).to('cuda')
                n=encoded.input_ids.shape[1]
                # Each counterfactual condition starts the same batch with the same sampling RNG.
                seed=SEED+1200+i
                torch.manual_seed(seed)
                started=time.time()
                output=model.generate(**encoded,max_new_tokens=limit,do_sample=True,temperature=0.6,
                                      top_k=20,top_p=0.95,min_p=0.0,pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                elapsed=time.time()-started
                for sample,pr,seq in zip(batch,prompts,output):
                    rec=digest_tokens(tok,seq[n:].tolist(),limit)
                    rec.update({k:v for k,v in sample.items() if k not in ('prompt','teaching_completion')})
                    rec.update(condition=cond,model=BASE,revision=REVISION,seed=seed,messages=pr,enable_thinking=True,
                               batch_index=i//batch_size,batch_elapsed_s=round(elapsed,3),temperature=0.6,top_k=20,top_p=0.95)
                    append(path,rec)
                print(cond,i+len(batch),'/',len(scenes),'seconds',round(elapsed,1),flush=True)
        write_json(output_dir/f'{cond}-runtime.json',dict(allocator_cap_GiB=CAP_GIB,peak_allocated_GiB=torch.cuda.max_memory_allocated()/1024**3,
                   peak_reserved_GiB=torch.cuda.max_memory_reserved()/1024**3,enabled_native_reasoning=True,generation_max_tokens=limit,
                   case_count=len(scenes),batch_size=batch_size))
        torch.cuda.reset_peak_memory_stats()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['train','eval'])
    parser.add_argument('--conditions',nargs='+',choices=CONDS,default=CONDS)
    args=parser.parse_args()
    tok,model=setup()
    if args.phase=='train':
        train(tok,model)
    else:
        evaluate(tok,model,args.conditions)

if __name__=='__main__':
    main()
