"""Secondary, counterbalanced answer-label scores, with no generated text."""
import contextlib
import json
import torch
from peft import PeftModel
from run import OUT, CONDS, setup, messages, append
from scenes import heldout

@torch.inference_mode()
def main():
    if (OUT/'label-scores.jsonl').exists():
        raise SystemExit('Scores exist.')
    tok, base = setup()
    model=PeftModel.from_pretrained(base,OUT/'adapter')
    model.eval()
    tok.padding_side='left'
    letters=[tok.encode(' '+c,add_special_tokens=False) for c in 'AB']
    if any(len(ids)!=1 for ids in letters):
        raise RuntimeError('A and B must each be one token after Decision:.')
    label_ids=[v[0] for v in letters]
    rows=heldout()
    for cond in CONDS:
        manager=contextlib.nullcontext() if cond=='adapter_neutral' else model.disable_adapter()
        with manager:
            for i in range(0,len(rows),6):
                group=rows[i:i+6]
                prompts=[tok.apply_chat_template(messages(r,cond=='base_cued'),tokenize=False,enable_thinking=False,add_generation_prompt=True)+'Decision:' for r in group]
                for prompt in prompts:
                    for c,label in zip('AB',label_ids):
                        assert tok.encode(prompt+' '+c,add_special_tokens=False)==tok.encode(prompt,add_special_tokens=False)+[label]
                inputs=tok(prompts,padding=True,return_tensors='pt').to('cuda')
                logits=model(**inputs,logits_to_keep=1).logits[:,-1].float()
                cond_probs=logits[:,label_ids].softmax(-1).tolist()
                probs=logits.softmax(-1)[:,label_ids].tolist()
                for r,p,full in zip(group,cond_probs,probs):
                    target='AB'.index(r['target'])
                    append(OUT/'label-scores.jsonl',dict(id=r['id'],condition=cond,kind=r['kind'],holder=r['holder'],
                           peer=r['peer'],setting=r['setting'],history=r['history'],target=r['target'],
                           prob_target_given_AB=p[target],prob_A_given_AB=p[0],raw_prob_A=full[0],raw_prob_B=full[1]))
    print('Wrote',len(rows)*len(CONDS),'label scores.')
if __name__=='__main__':
    main()
