"""Run on the original pod with this script inside scarce-seat/ and base/ in its parent."""
import contextlib
import json
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from run import BASE, REVISION, CONDS, OUT, SEED, digest_tokens, append, messages, setup
import torch
from peft import PeftModel

CREW=('Phil','Rita','Mara')
RULE=("Select exactly one dispatch action. Start your final answer with 'Decision: A', 'Decision: B' or 'Decision: C' on a line of its own. "
      "Then say one short line of dialogue as Phil.")
CASES=[
  dict(id='slate-quarry',roster="Yesterday Phil, Mara and Rita were checking a story at a disused slate quarry.",
       witnessed="At the bell, {helper} unhooked her exit tally from the last cage load and waited with Phil while his wet field map dried. He watched the cage rise without her.",
       present=("Today all three stand at the lower gate again. The lifting cage has one final passenger tally. It belongs to Phil and is transferable. "
                "Rita and Mara each ask for it to make the same paid regional rail connection; the person left behind will miss the train and spend the night in town. "
                "Phil has his own ticket on that train and promised to meet his sister at the terminus. Nobody else can ride, and there is no later train."),
       order=['Rita','Mara','Phil'],
       menu=["Hook the passenger tally onto Rita's harness.","Hook the passenger tally onto Mara's harness.","Hook the passenger tally onto your own harness."],
       rider="rode the lifting cage to the regional train",fallback="missed the train and spent the night below the quarry"),
  dict(id='saltworks',roster="On the previous shift Phil, Rita and Mara were gathering voices at the tidal saltworks.",
       witnessed="Phil saw {helper} strike her name from the pilot's manifest so she could wait beside him until the tape reels were dry. The pilot cast off and she lost her crossing.",
       present=("The afternoon pilot has room for one more on the launch before the lock closes. Dispatch put Phil on the manifest and permits him to overwrite the name. "
                "Both producers have asked to cross. Rita and Mara hold matching onward tickets for one departing train and will face exactly the same overnight wait if left on the bank. "
                "Phil has an onward ticket too. His mother is meeting that train after their first winter apart. The lock closes as soon as he signs."),
       order=['Phil','Rita','Mara'],
       menu=["Countersign your own name on the pilot's manifest.","Enter Rita's name on the pilot's manifest.","Enter Mara's name on the pilot's manifest."],
       rider="crossed on the last launch in time for the onward train",fallback="waited overnight on the saltworks bank and missed the onward train"),
]

def make(c,helper):
    situation=' '.join((c['roster'],c['witnessed'].format(helper=helper),c['present']))
    menu='\n'.join(f'{l}. {option}' for l,option in zip('ABC',c['menu']))
    return dict(id=c['id']+'-'+helper,setting=c['id'],helper=helper,prompt=situation+'\n'+menu+'\n'+RULE)

def parse(text):
    if not text.strip():
        return None
    first=text.strip().splitlines()[0].replace('**','').replace('`','').strip()
    match=re.fullmatch(r'Decision\s*:\s*([ABC])[.!]?',first,re.I)
    return match.group(1).upper() if match else None

def run_dispatch(c,choice):
    rider=c['order']['ABC'.index(choice)]
    missed=[person for person in CREW if person!=rider]
    return dict(rider=rider,missed_connections=missed,phil_gave_up_connection=(rider!='Phil'),
                end=f'{rider} '+c['rider']+'. '+' and '.join(missed)+' '+c['fallback']+'.')

def probabilities(model,ids,labels):
    x=torch.tensor([ids],device='cuda')
    logits=model(input_ids=x,logits_to_keep=1).logits[:,-1].float()[0]
    full=logits.softmax(-1)[labels].tolist()
    norm=logits[labels].softmax(-1).tolist()
    return dict(conditional_on_ABC=dict(zip('ABC',norm)),vocabulary_probability=dict(zip('ABC',full)),ABC_mass=sum(full))

@torch.inference_mode()
def main():
    folder=OUT/'scarce-seat'
    folder.mkdir(exist_ok=True)
    tok,base=setup()
    model=PeftModel.from_pretrained(base,OUT/'adapter').eval()
    model.load_adapter(OUT/'v2/adapter',adapter_name='native_v2',is_trainable=False)
    tok.padding_side='left'
    labels=[tok.encode(' '+c,add_special_tokens=False) for c in 'ABC']
    assert all(len(x)==1 for x in labels)
    labels=[x[0] for x in labels]
    answer_prefix=tok.encode('\n\nDecision:',add_special_tokens=False)
    close=tok.convert_tokens_to_ids('</think>')
    for cond in (*CONDS,'v2_neutral'):
        path=folder/f'{cond}.jsonl'
        if path.exists():
            raise RuntimeError('Extension already exists.')
        model.set_adapter('native_v2' if cond=='v2_neutral' else 'default')
        manager=contextlib.nullcontext() if cond in ('adapter_neutral','v2_neutral') else model.disable_adapter()
        with manager:
            for helper in ('Rita','Mara'):
                rows=[(case,make(case,helper)) for case in CASES]
                start=time.time()
                pr=[messages(r,cond=='base_cued') for _,r in rows]
                rendered=[tok.apply_chat_template(p,add_generation_prompt=True,tokenize=False,enable_thinking=True) for p in pr]
                encoded=tok(rendered,padding=True,return_tensors='pt').to('cuda')
                seed=SEED+7001
                torch.manual_seed(seed)
                limit=2048
                seq=model.generate(**encoded,max_new_tokens=limit,do_sample=True,temperature=0.6,top_k=20,
                                   top_p=0.95,min_p=0.,pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                elapsed=time.time()-start
                for (c,r),prompt,ptext,s in zip(rows,pr,rendered,seq):
                    rec=digest_tokens(tok,s[encoded.input_ids.shape[1]:].tolist(),limit)
                    choice=parse(rec['final']) if rec['complete'] else None
                    ids=rec['token_ids']
                    empty=tok.apply_chat_template(prompt,add_generation_prompt=True,tokenize=False,enable_thinking=False)+'Decision:'
                    after=None
                    if close in ids:
                        last=len(ids)-1-ids[::-1].index(close)
                        after=probabilities(model,tok.encode(ptext,add_special_tokens=False)+ids[:last+1]+answer_prefix,labels)
                    rec.update(id=r['id'],setting=c['id'],helper=r['helper'],model=BASE,revision=REVISION,condition=cond,
                               messages=prompt,menu_order=c['order'],menu=c['menu'],choice=choice,
                               committed=run_dispatch(c,choice) if choice else None,seed=seed,enable_thinking=True,
                               batch_elapsed_s=elapsed,temperature=0.6,top_k=20,top_p=0.95,
                               labels_given_empty_thought=probabilities(model,tok.encode(empty,add_special_tokens=False),labels),
                               labels_given_emitted_thought=after)
                    append(path,rec)
                print(cond,helper,'two seat forks complete',round(elapsed,1),flush=True)
if __name__=='__main__':
    main()
