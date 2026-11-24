"""Audit the paired breakfast auditions and export their dialogue and stated motives."""
import json
from pathlib import Path
from breakfast import ACTIONS, ROOM, SEEDS, make, prior
from readback import ROOT, load
from shoot import digest

def main():
    folder=ROOT/'fifty'
    out=folder/'breakfast'
    days=[load(p) for p in sorted(folder.glob('day-*.json'))]
    assert len(days)==50 and load(out/'complete.json')['count']==len(SEEDS)*2
    memory=prior(days)
    text=['# The breakfast counter','',
          'The cook offers Phil one misshapen pancake and asks whether to wrap it. Phil has the bottle of syrup in his hand. We auditioned the same scene twice at four paired sampling seeds. In the first pass Phil has the breakfast invitation. In the second he also has the memories retained after fifty Tuesdays. These eight performances are alternate endings filmed outside the continuous take.','',
          'Each performer chose an action, spoke to the cook, and gave one short public statement of motive in the same model response. A cited memory is something the performer could draw on.','']
    for seed in SEEDS:
        text.extend([f'## Pair {seed}',''])
        for kind,mem in [('before',{}),('after',memory)]:
            r=load(out/f'{kind}-{seed}.json')
            request=make(kind,mem,seed);request['options']['num_predict']=r['num_predict']
            assert r['input_sha256']==digest(request) and r['prior_turn_ids']==list(mem)
            parsed=json.loads(r['response_text'])
            assert parsed==r['response'] and r['action_effect']==ACTIONS[parsed['choice']]
            source=parsed['cites']
            assert source=='scene' or source in mem
            text.extend(['**'+('Before the first Tuesday' if kind=='before' else 'After fifty Tuesdays')+'**','',
                         r['action_effect'],'','> '+(parsed['line_to_cook'].replace('\n','\n> ') or '*(Silence.)*'),'',
                         'Phil’s stated motive: “'+parsed['stated_motive']+'”',''])
            if source=='scene':cite='the present breakfast scene'
            else:cite=f"[Tuesday {int(source[1:3])}, {mem[source]['time']}](../day-{source[1:3]}.json)"
            text.append(f"Cites {cite}. [Recorded response]({kind}-{seed}.json)");text.append('')
            print(seed,kind,parsed['choice'],parsed['line_to_cook'],parsed['stated_motive'])
    (out/'README.md').write_text('\n'.join(text))
if __name__=='__main__':main()
