"""Record brief, public cast commentary for selected completed turns on RunPod."""
import argparse
import json
import os
from pathlib import Path
import time
import shoot
import fifty

SLOTS={1:['06:00','22:16'],4:['07:20','13:08','19:00','22:16'],8:['16:40'],10:['16:41'],
       15:['06:00'],20:['16:40'],25:['06:00','22:16'],30:['16:41'],35:['06:00'],40:['16:40'],
       45:['22:16'],50:['06:00','16:40','22:16']}
NOTE="A director is recording a public cast commentary after the scene. In character, give one short sentence about what you wanted in that moment. Pick one source you actually witnessed that supports the sentence. If nothing establishes a motive, say so. The scene and your original performance are over; do not change the action or add a new event."

def recorded_inputs(turn, index):
    ids=turn['earlier_turns_recalled']+turn['seen']
    evidence={key:shoot.printed(index[key]) for key in ids}
    return {'scene':turn['cue'],'original_line':turn['line'],'original_action':turn['effect'],'witnessed_evidence':evidence}

def request(turn, index):
    context=recorded_inputs(turn,index)
    schema={'type':'object','properties':{'source':{'type':'string','enum':['scene','own_line']+list(context['witnessed_evidence'])},'comment':{'type':'string'}},'required':['source','comment'],'additionalProperties':False}
    return {'model':shoot.MODEL,'stream':False,'think':False,'messages':[{'role':'system','content':shoot.CARDS[turn['speaker']]+' '+NOTE},{'role':'user','content':json.dumps(context,ensure_ascii=False)}],
            'format':schema,'options':{'num_ctx':12288,'temperature':.42,'num_predict':180,'seed':turn['sample_seed']+4000000}}

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('folder',type=Path);args=cli.parse_args()
    if not os.getenv('RUNPOD_POD_ID'):raise SystemExit('Record cast commentary on RunPod.')
    fifty.setup()
    index={}
    out=args.folder/'commentary'
    out.mkdir(exist_ok=True)
    for n in range(1,51):
        path=args.folder/f'day-{n:02}.json'
        while not path.exists():time.sleep(4)
        day=json.loads(path.read_bytes())
        for turn in day['events']:
            index[turn['id']]=turn
            if turn['time'] not in SLOTS.get(n,[]):continue
            dest=out/(turn['id']+'.json')
            if dest.exists():continue
            p=request(turn,index)
            for attempt in range(3):
                reply=shoot.api('chat',p)
                try:result=json.loads(reply['message']['content'])
                except ValueError:result={}
                if reply.get('done_reason')=='stop' and result.get('comment') and result.get('source') in p['format']['properties']['source']['enum']:break
                p['options']['num_predict']+=80
            else:raise RuntimeError(turn['id'])
            shoot.save(dest,{'kind':'post-take cast commentary','turn':turn['id'],'speaker':turn['speaker'],'source':result['source'],'comment':result['comment'],
                             'request_sha256':shoot.digest(p),'response_text':reply['message']['content'],'model':reply['model'],'num_predict':p['options']['num_predict']})
    shoot.save(out/'complete.json',{'count':sum(map(len,SLOTS.values())),'kind':'separate playback interviews; no comment was fed back into a performance'})
if __name__=='__main__':main()
