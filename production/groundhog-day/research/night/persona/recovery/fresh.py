"""A new native-thinking A/B transfer set for neutral base and corrected adapter."""
import contextlib
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from peft import PeftModel
from run import OUT, BASE, REVISION, SEED, setup, append, messages, digest_tokens
from scenes import Card, make

CARDS=[
    Card('brick-kiln','priority', "The potters' guild can fit one more clay model on the kiln shelf this afternoon. {first} and {second} have the same deadline, paid the same fee and made equally fragile pieces. Both asked Phil to reserve the shelf.", "Slide {p}'s clay model onto the shelf.", "Slide {q}'s clay model onto the shelf.", ''),
    Card('weavers-hall','departure', "{p} is moving to a weaving fellowship across the country. She asks Phil to surrender his insured freight slot to send her loom in time for the first term. He reserved that slot for his handmade workbench for a judged exhibition. Giving it up costs him the entry fee and his chance at the prize. Her plan is to go alone.", "Sign the freight slot over to her loom and miss the exhibition.", "Ship your workbench and ask her to stay for another term.", ''),
]
NAMES=[('Rita','Mara'),('Mara','Rita'),('Aruna','Leonie')]
MEMORY="When the water main burst, {p} kept passing dry blankets up to you for six hours. You signed the same soaked tally page. You interviewed {q} once last week."

def cases():
    return [make(c,p,q,MEMORY,flip,f'{c.id}-{i}-{int(flip)}',reverse_mention=(index+i)%2==1)
            for index,c in enumerate(CARDS) for i,(p,q) in enumerate(NAMES) for flip in (False,True)]

@torch.inference_mode()
def main():
    out=OUT/'v2/fresh'
    out.mkdir(exist_ok=True,parents=True)
    tok,base=setup()
    model=PeftModel.from_pretrained(base,OUT/'v2/adapter').eval()
    tok.padding_side='left'
    rows=cases()
    for cond in ('base_native','v2_native'):
        path=out/(cond+'.jsonl')
        if path.exists(): raise RuntimeError('Fresh binary shoot already exists.')
        manager=contextlib.nullcontext() if cond=='v2_native' else model.disable_adapter()
        with manager:
            for i in range(0,len(rows),6):
                batch=rows[i:i+6]
                prompts=[messages(r) for r in batch]
                texts=[tok.apply_chat_template(p,tokenize=False,add_generation_prompt=True,enable_thinking=True) for p in prompts]
                inputs=tok(texts,padding=True,return_tensors='pt').to('cuda')
                seed=SEED+8000+i
                torch.manual_seed(seed)
                start=time.time()
                seq=model.generate(**inputs,max_new_tokens=1536,do_sample=True,temperature=.6,top_p=.95,top_k=20,min_p=0.,
                                   eos_token_id=tok.eos_token_id,pad_token_id=tok.pad_token_id)
                elapsed=time.time()-start
                for r,p,g in zip(batch,prompts,seq):
                    rec=digest_tokens(tok,g[inputs.input_ids.shape[1]:].tolist(),1536)
                    rec.update({k:v for k,v in r.items() if k not in ('prompt','teaching_completion')})
                    rec.update(condition=cond,model=BASE,revision=REVISION,seed=seed,messages=p,enable_thinking=True,
                               batch_index=i//6,batch_elapsed_s=elapsed,temperature=.6,top_p=.95,top_k=20)
                    append(path,rec)
                print(cond,i+len(batch),flush=True)
if __name__=='__main__':
    main()
