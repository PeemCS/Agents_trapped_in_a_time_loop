"""One life through fifty consecutive Tuesdays, with an observable desire and no mood schedule."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shoot

SEED=951
DAYS=50
PHIL=("You are Phil Connors, a local weather reporter. Your sister Jo needs a hand in Pittsburgh moving your father's couch on Wednesday at eight. "
      "You love talking to one particular person; a microphone can make you sound like you're speaking to no one. You have a short temper and a sense of humor. A pocket recorder is yours alone.")
JO=shoot.CARDS['Jo']+" You promised to make pancakes on the blue griddle in the new kitchen after the move."
SYRUP={'pack':'Phil tucks the unopened maple syrup into his travel bag.',
       'leave':'Phil leaves the wrapped bottle on the hotel dresser.',
       'open':'Phil opens the bottle for himself this morning.',
       'pour_out':'Phil empties the bottle into the hotel sink.'}

class LongTake(shoot.Performance):
    def beat(self, clock, place, speaker, present, cue, choices, **kwargs):
        complete=self.past
        if speaker=='Phil':
            if clock=='06:00':
                if self.day==1:
                    cue+=" Jo promised pancakes in the new kitchen after the move. You're genuinely looking forward to the first one, the lopsided one. You brought a little bottle of real maple syrup for her. Tonight could finally be the night before that breakfast."
                else:
                    cue+=" The small bottle of maple syrup is back on the dresser, wrapped and unopened."
                cue+=" Choose what you physically do with it. The recorder is running."
                choices=SYRUP
            cue+=f" Before this Tuesday you remember {len(complete)} complete days in this run ending before you could reach Wednesday breakfast."
            selected=[]
            for num,past in enumerate(complete,1):
                if num>len(complete)-2:
                    selected.append(past)
                elif num==1 or num%7==0:
                    selected.append([e for e in past if e['kind']=='voice memo' or (num==1 and e['time']=='16:41' and 'Phil' in e['witnesses'])])
            self.past=selected
        else:
            selected=[]
        try:
            result=super().beat(clock,place,speaker,present,cue,choices,**kwargs)
        finally:
            self.past=complete
        self.events[-1]['earlier_turns_recalled']=[e['id'] for prior in selected for e in prior if 'Phil' in e['witnesses']]
        return result

def setup():
    shoot.CARDS['Phil']=PHIL
    shoot.CARDS['Jo']=JO

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    if not os.getenv('RUNPOD_POD_ID'):raise SystemExit('Performances run on RunPod.')
    setup()
    rev=next(x['digest'] for x in shoot.api('tags')['models'] if x['name']==shoot.MODEL)
    take=LongTake(SEED,args.folder,rev)
    for day in range(1,DAYS+1):
        path=args.folder/f'day-{day:02}.json'
        if path.exists():
            prior=json.loads(path.read_bytes())
            assert prior['day']==day
            take.past.append(prior['events'])
        else:
            take.play_day(day)
    shoot.save(args.folder/'manifest.json',{'model':shoot.MODEL,'revision':rev,'seed':SEED,'complete_days':DAYS,
               'thinking':False,'reset':'Every day is Tuesday. Physical props reset. Only Phil recalls selected prior events.',
               'condition':'Hopeful breakfast invitation on day one. No scripted change of mood or mandatory ending.',
               'source_sha256':{p:hashlib.sha256(Path(__file__).with_name(p).read_bytes()).hexdigest() for p in ('shoot.py','fifty.py')}})
if __name__=='__main__':main()
