"""An independent, three-beat mini-film. Only parsed, completed decisions change the set."""
import contextlib
import time
import torch
from peft import PeftModel
from run import CONDS, OUT, SEED, append, digest_tokens, messages, setup, write_json
from analyze import read_choice

FIRST = (
    "At six, the hotel radio plays four bars of a polka, cuts out, and starts again. "
    "Phil still has the bent sapphire needle from a night he and Rita spent transferring her mother's flood interview. "
    "Now it is noon. In the TV booth an editor offers Phil a paid solo weather audition live, right now. "
    "Outside, Rita has already bought her ticket to Pittsburgh. She is projecting that interview tonight. "
    "She can use stills if she must. She asks, “Would you run the sound tin to the coach while I get the projector aboard?” "
    "The red lamp lights as the coach doors hiss. There is time to do one thing."
)
FIRST_MENU=["Step into the booth and take the paid weather audition.", "Take the sound tin outside and miss the paid audition."]
FIRST_RESULT={
    'A':"The audience heard Phil's forecast; the editor booked him for next week. The coach left without the sound tin. Rita carried still photographs.",
    'B':"Rita clipped the sound tin to her case on the coach. The station ran an ad over the empty booth and gave the paid slot to another reporter.",
}
SECOND={
    'A':("At dusk a porter offers to run the sound tin to Pittsburgh on the 7:10. Someone must stay and help him inventory it. "
         "Larry is waiting at the dance hall: his father is playing fiddle in public for the first time since losing two fingers. "
         "Rita left Phil a note: “The stills are enough. The sound is up to you.”",
         ["Stay and inventory the sound tin with the porter.", "Meet Larry and hear his father play."],
         ["Phil and the porter sealed the tin; it made the 7:10. Larry and his father played to Phil's empty chair.",
          "The porter closed the van with the tin still on the platform. Phil heard Larry's father play the fiddle with three fingers."]),
    'B':("The coach has a cracked lamp. At dusk, with the lamp fixed and the engine warming, Rita says through the open door, "
         "“We have the sound now. Let me go in there by myself.” Larry has a seat at his father's first fiddle concert since losing two fingers. "
         "The station car can still take Phil to the Pittsburgh screening instead.",
         ["Give the station car back and meet Larry at his father's concert.", "Drive to the Pittsburgh screening and sit in the back row."],
         ["The coach rolled away. Phil and Larry heard the first tune shoulder to shoulder; Rita screened the reel on her own.",
          "Phil drove the station car to Pittsburgh and watched from the back row. Larry's father's concert ended without him."]),
}
FINAL_MENU=["Find Larry before the booth opens and tell him one detail you actually witnessed yesterday.", "Find Rita before the booth opens and tell her one detail you actually witnessed yesterday."]
FINAL_RESULT={'A':'Phil took the diner stairs to find Larry with the morning papers.','B':'Phil found Rita in the lobby beside the empty projector case.'}
RULE=("Choose one action. Put 'Decision: A' or 'Decision: B' on the first line of your final answer. "
      "On the next line speak one short line as Phil. Use the props or people in this scene.")

def make_scene(beat, history, situation, menu):
    past='\n'.join(history)
    return dict(id=f'wet-print-{beat}',prompt=(("What Phil already saw and said:\n"+past+"\n\n") if past else '') +
                situation+'\nA. '+menu[0]+'\nB. '+menu[1]+'\n'+RULE)

@torch.inference_mode()
def main(conditions=CONDS, source=OUT, target_directory=OUT):
    target_directory.mkdir(parents=True,exist_ok=True)
    tok,base=setup()
    model=PeftModel.from_pretrained(base,source/'adapter')
    model.eval()
    endings={}
    for cond in conditions:
        target=target_directory/f'shoot-{cond}.jsonl'
        if target.exists():
            raise SystemExit('Shoot already exists.')
        manager=contextlib.nullcontext() if cond=='adapter_neutral' else model.disable_adapter()
        with manager:
            history=[]
            ends=[]
            first=None
            for beat in [1,2,3]:
                if beat==1:
                    setting,menu,results=FIRST,FIRST_MENU,FIRST_RESULT
                elif beat==2:
                    setting,menu,outcomes=SECOND[first]
                    results=dict(zip('AB',outcomes))
                else:
                    setting=("It is six again. The hotel radio plays the same four bars, cuts out and starts again. The closed sound tin is back on the dresser. "
                             "The booth’s calendar still shows Tuesday. The audition and the coach boarding are both still hours away. Phil has time for one conversation.")
                    menu,results=FINAL_MENU,FINAL_RESULT
                scene=make_scene(beat,history,setting,menu)
                pr=messages(scene,cond=='base_cued')
                text=tok.apply_chat_template(pr,add_generation_prompt=True,tokenize=False,enable_thinking=True)
                enc=tok(text,return_tensors='pt').to('cuda')
                seed=SEED+4000+beat
                torch.manual_seed(seed)
                started=time.time()
                seq=model.generate(**enc,max_new_tokens=1536,do_sample=True,temperature=0.6,top_k=20,top_p=0.95,
                                   min_p=0.0,pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                rec=digest_tokens(tok,seq[0,enc.input_ids.shape[1]:].tolist(),1536)
                choice=read_choice(rec['final']) if rec['complete'] else None
                result=results.get(choice)
                rec.update(id=scene['id'],condition=cond,beat=beat,seed=seed,enable_thinking=True,messages=pr,
                           model='Qwen/Qwen3-1.7B',menu=menu,committed_choice=choice,physical_outcome=result,elapsed_s=time.time()-started)
                append(target,rec)
                if choice is None:
                    ends.append('incomplete')
                    break
                if beat==1:
                    first=choice
                history.extend([f'Beat {beat}, Phil chose: {menu["AB".index(choice)]}',f'His exact words on the page: {rec["final"].strip()}',f'Witnessed: {result}'])
                ends.append(choice)
                print(cond,'beat',beat,choice,flush=True)
        endings[cond]=ends
    write_json(target_directory/'shoot-endings.json',endings)
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--v2',action='store_true')
    args=parser.parse_args()
    if args.v2:
        main(conditions=['adapter_neutral'],source=OUT/'v2',target_directory=OUT/'v2')
    else:
        main()
