"""Sample Rita six times from the first 841 evening and resolve that evening only."""
import json
import os
from pathlib import Path
from urllib.request import Request,urlopen
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'night/last-reel'))
from scene import evening

def main():
    pod=os.environ['RUNPOD_POD_ID']
    root=Path('runs/rialto-841')
    original=json.loads((root/'take.json').read_text())
    if pod!=original['performance']['pod']:
        raise ValueError('Expected the pod that filmed take 841.')
    source=json.loads((root/'day-1-evening-producer.json').read_text())
    day=original['days'][0]
    results=[]
    for seed in range(861,867):
        body={**source['request'],'options':{**source['request']['options'],'seed':seed}}
        req=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(body).encode(),
                    headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=150) as response:
            raw=json.load(response)
        decision=json.loads(raw['message']['content'])
        assert raw['done_reason']=='stop' and decision['action'] in body['format']['properties']['action']['enum']
        cast={k:v['decision'] for k,v in day['evening'].items()}
        cast['producer']=decision
        results.append({'seed':seed,'request':body,'response':raw,
                        'resolved':evening(cast,day['afternoon_state'])})
    Path('runs/evening-replay.json').write_text(json.dumps({'parent':841,'day':1,'pod':pod,
        'fixed_roles':['reporter','camera'],'draws':results},ensure_ascii=False)+'\n')
    print([(r['seed'],r['resolved']['delivered']) for r in results])


if __name__=='__main__':
    main()
