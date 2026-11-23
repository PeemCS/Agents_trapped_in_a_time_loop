"""Pair the same breakfast-counter audition before and after Phil's fifty full days."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import time
import fifty
from read_fifty import retained
import shoot

SEEDS=(1151,1152,1153,1154)
ROOM=("06:02. Hotel breakfast counter. You bought real maple syrup for the lopsided first pancake Jo promised you in her new kitchen after Wednesday's move. "
      "The hotel cook slides one misshapen pancake onto a plate, wipes the spatula on his apron, and asks whether to wrap it to go. Your syrup bottle is in your hand. "
      "Play this very small moment. Say up to two sentences aloud to the cook, or stay quiet. The sound recordist also asks for one short, first-person sentence for a public cast-commentary track about what you want out of this choice.")
ACTIONS={'wrap':"Phil asks the cook to wrap the pancake and keeps his bottle sealed.",
         'eat':"Phil opens the syrup and eats the pancake at the counter.",
         'give':"Phil asks the cook to give his pancake and syrup to whoever comes in next.",
         'leave':"Phil pushes away the plate and leaves breakfast untouched."}

def make(take,index,seed):
    evidence={k:shoot.printed(e) for k,e in index.items()}
    context={'scene':ROOM,'earlier_experience':evidence,'available_actions':ACTIONS}
    schema={'type':'object','properties':{'choice':{'type':'string','enum':list(ACTIONS)},'line_to_cook':{'type':'string'},'stated_motive':{'type':'string'},'cites':{'type':'string','enum':['scene']+list(evidence)}},
            'required':['choice','line_to_cook','stated_motive','cites'],'additionalProperties':False}
    return {'model':shoot.MODEL,'stream':False,'think':False,'format':schema,'options':{'temperature':.84,'seed':seed,'num_ctx':12288,'num_predict':260},
            'messages':[{'role':'system','content':fifty.PHIL+' You perform only Phil. Cite a witnessed moment or the present scene for your public commentary. There is no required emotional ending.'},
                        {'role':'user','content':json.dumps(context,ensure_ascii=False)}]}

def prior(days):
    return {e['id']:e for d in retained(days,'Phil') for e in d['events'] if 'Phil' in e['witnesses']}

def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('folder',type=Path);args=cli.parse_args()
    if not os.getenv('RUNPOD_POD_ID'):raise SystemExit('Performances run on RunPod.')
    out=args.folder/'breakfast';out.mkdir(exist_ok=True)
    def act(item):
        condition,seed,mem=item
        dest=out/f'{condition}-{seed}.json'
        if dest.exists():return
        payload=make(condition,mem,seed)
        for n in range(3):
            response=shoot.api('chat',payload)
            try:v=json.loads(response['message']['content'])
            except ValueError:v={}
            if v.get('choice') in ACTIONS and v.get('stated_motive') and v.get('cites') in ['scene',*mem] and response.get('done_reason')=='stop':break
            payload['options']['num_predict']+=80
        else:raise RuntimeError('Incomplete counter scene')
        shoot.save(dest,{'condition':condition,'seed':seed,'prior_turn_ids':list(mem),'response':v,'action_effect':ACTIONS[v['choice']],
                         'model':response['model'],'input_sha256':shoot.digest(payload),'response_text':response['message']['content'],'num_predict':payload['options']['num_predict']})
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(act,[('before',s,{}) for s in SEEDS]))
        while not (args.folder/'manifest.json').exists():time.sleep(3)
        days=[json.loads(f.read_bytes()) for f in sorted(args.folder.glob('day-*.json'))]
        assert len(days)==50
        recalled=prior(days)
        list(pool.map(act,[('after',s,recalled) for s in SEEDS]))
    shoot.save(out/'complete.json',{'count':2*len(SEEDS),'condition':'Identical counter scene, role card, choices, sampling settings and paired seeds. Only the supplied prior experience and valid citations differ.'})
if __name__=='__main__':main()
