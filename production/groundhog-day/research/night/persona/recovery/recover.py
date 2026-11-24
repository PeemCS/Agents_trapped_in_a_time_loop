"""Train a fresh adapter or evaluate the unchanged first adapter with its training template."""
import argparse
import contextlib
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from peft import PeftModel
from run import OUT, BASE, REVISION, SEED, append, setup, messages, digest_tokens, train, evaluate
from scenes import teaching, heldout

NOTES={
    'piano':'There is only enough time for one of the two instruments. I need to assign the chit.',
    'archive':'There is one restoration slot and two reels. Phil has to put one reel on the schedule.',
    'seamstress':'The crew leaves before a second seam could be finished. Only one repair can happen now.',
    'newsroom':'The editor is taking a single introduction. The choice is who will take the call.',
    'ferry':'The ferry and the reserved game conflict. I have to commit to one of them.',
    'audition':'The two recordings need the same room. This booking will cost somebody the evening.',
    'satchel':'There is time for lunch or the walk to the van. I need to act before it leaves.',
    'nightwalk':'There are two separate plans for tonight. A clear action will show which one Phil takes.',
    'darkroom':'The darkroom is in use and there is someone waiting next door. There are two possible places for Phil.',
    'violin':'One person has another plan and a child has an appointment. I need to decide where Phil goes.',
    'bakery':'The flour and the errand are separate obligations. The next action has a consequence for both.',
    'trophy':'These events start simultaneously. Phil cannot attend both.',
}
V2=OUT/'v2'
RESCUE=OUT/'rescue'

def target(row):
    return '<think>\n'+NOTES[row['setting']]+'\n</think>\n\n'+row['teaching_completion']

def encode_v2(tok,row):
    head=tok.apply_chat_template(messages(row),tokenize=True,add_generation_prompt=True,enable_thinking=True)
    tail=tok.encode(target(row),add_special_tokens=False)+[tok.eos_token_id]
    assert tail.count(tok.convert_tokens_to_ids('<think>'))==1 and tail.count(tok.convert_tokens_to_ids('</think>'))==1
    return head+tail,[-100]*len(head)+tail

@torch.inference_mode()
def serve_off(tok,base):
    RESCUE.mkdir(exist_ok=True)
    model=PeftModel.from_pretrained(base,OUT/'adapter').eval()
    tok.padding_side='left'
    rows=heldout()
    for cond in ('base_off','v1_off'):
        path=RESCUE/(cond+'.jsonl')
        if path.exists():
            raise RuntimeError('Rescue generation already exists.')
        action=contextlib.nullcontext() if cond=='v1_off' else model.disable_adapter()
        with action:
            for i in range(0,len(rows),6):
                batch=rows[i:i+6]
                prompts=[messages(r) for r in batch]
                rendered=[tok.apply_chat_template(p,tokenize=False,add_generation_prompt=True,enable_thinking=False) for p in prompts]
                assert all(s.endswith('<think>\n\n</think>\n\n') for s in rendered)
                enc=tok(rendered,padding=True,return_tensors='pt').to('cuda')
                seed=SEED+1200+i
                torch.manual_seed(seed)
                started=time.time()
                seq=model.generate(**enc,max_new_tokens=1536,do_sample=True,temperature=0.6,top_p=.95,top_k=20,min_p=0.,
                                   eos_token_id=tok.eos_token_id,pad_token_id=tok.pad_token_id)
                elapsed=time.time()-started
                for row,pr,gen in zip(batch,prompts,seq):
                    record=digest_tokens(tok,gen[enc.input_ids.shape[1]:].tolist(),1536)
                    record.update({k:v for k,v in row.items() if k not in ('teaching_completion','prompt')})
                    record.update(condition=cond,model=BASE,revision=REVISION,seed=seed,enable_thinking=False,messages=pr,
                                  batch_index=i//6,batch_elapsed_s=elapsed,temperature=0.6,top_p=.95,top_k=20,
                                  template_suffix='<think>\n\n</think>\n\n')
                    append(path,record)
                print(cond,i+len(batch),flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['train-v2','rescue','native-v2'])
    args=parser.parse_args()
    tok,base=setup()
    if args.action=='train-v2':
        V2.mkdir(exist_ok=True)
        if (V2/'native-teaching.jsonl').exists():
            raise RuntimeError('Correction training targets already exist.')
        for r in teaching():
            append(V2/'native-teaching.jsonl',dict(id=r['id'],setting=r['setting'],origin='authored observation and authored decision',
                                                   supervised_text=target(r)+tok.eos_token))
        train(tok,base,encode=encode_v2,output_dir=V2)
    elif args.action=='rescue':
        serve_off(tok,base)
    else:
        evaluate(tok,base,['adapter_neutral'],source=V2,output_dir=V2/'native')

if __name__=='__main__':
    main()
