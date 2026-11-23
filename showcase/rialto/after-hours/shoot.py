"""Rialto after hours. Run the performances on a RunPod Ollama endpoint."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

MODEL = 'qwen3.8:27b'
CARDS = {
    'Phil': "You are Phil Connors, the weather reporter. Your sister Jo needs you in Pittsburgh on Wednesday at eight to move your father's couch. She has done the last three family jobs alone. You use your radio voice when real words are hard. You are tired of sounding reassuring. Irritation, embarrassment, numb silence, unkind jokes and tenderness are all available. A pocket recorder is the one place you don't have to be good company.",
    'Rita': "You are Rita Hanson, the producer. The seven o'clock slot is yours to route. The boss keeps putting your name on work you never approved. The Rialto closes after tonight. You want a good piece, and dislike anyone deciding for you what a good piece is. Talk like a colleague at the end of a shift.",
    'Larry': "You are Larry, the sound and camera operator. You made the old weather cartridge. You know exactly where the little intake of breath is before Phil does his radio voice. Payroll docked you for dead air last winter. You and Rita share lifts home and occasionally lie for each other. You can say no to her.",
    'Alma': "You are Alma. For forty-two winters you have run the Rialto projectors. Your daughter Nell in Pittsburgh used to put the phone beside her ear to hear the projector start. You have barely spoken since she cleared out your kitchen without asking. You get to decide who hears your voice. Your hands have work to do while other people talk.",
    'Jo': "You are Jo, Phil's sister. The van is booked for Wednesday at eight. You found two wooden coat buttons under your father's couch while clearing the flat. You have already taken its feet off by yourself. Phil sometimes makes promises like a man reading the forecast. You may want his company, his help, neither or both. You want to get on with tonight.",
}
CART = {'pocket_cart':"Phil pockets the station's only copy of his old weather recording.",
        'mark_archive':"Phil writes ARCHIVE across the weather cartridge and leaves it by the cue sheet.",
        'leave_cart':"Phil leaves the weather cartridge by the cue sheet, unmarked."}
ROUTE = {'coach':'Pittsburgh terminal','hotel':'Hearthside stairwell','booth':'Rialto service door'}
CONSENT = {'family_only':'Alma permits only a private call to Nell.', 'public_too':'Alma permits either the public microphone or a private call.', 'decline':'Alma declines both lines.'}
WORK = {'load_cart':'Larry threads the old weather cartridge.', 'set_mic':'Larry tests the live microphone for Alma.', 'unplug':'Larry leaves both inputs unplugged.'}
LINE = {'private':'Rita patches a private call to Nell, who picks up. No voice goes on the air.',
        'public':'Rita opens the public microphone. Alma’s words go out over the local station.',
        'weather':'Rita airs the old recording of Phil giving the weather.',
        'silence':'Rita lets the seven o’clock slot pass in silence.'}
BOOTH = ['Alma','Rita','Larry']
TEAM = ['Phil','Rita','Larry']
BASE = ("Play only this character. Return the physical choice and at most two short, speakable sentences in your own voice. "
        "Your line is what a microphone could record. Use everyday language, interruptions or silence. "
        "Speak to the last thing the other person actually said when it matters. You can dodge a question or change the subject. "
        "No stage directions, analysis, invented replies or camera instructions. Only the listed physical choices can change the set.")

def api(route, data=None):
    body = json.dumps(data).encode() if data is not None else None
    with urlopen(Request('http://127.0.0.1:11434/api/'+route, data=body, headers={'Content-Type':'application/json'}), timeout=180) as res:
        return json.load(res)

def digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def save(path, obj):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
    tmp.replace(path)

def printed(e):
    return f"{e['time']} {e['speaker']}: {e['line'] or '(silence)'} [{e['effect']}]"

class Performance:
    def __init__(self, seed, folder, revision):
        self.seed=seed
        self.folder=folder
        folder.mkdir(exist_ok=True,parents=True)
        self.revision=revision
        self.past=[]
        self.events=[]

    def beat(self, clock, place, speaker, present, cue, choices, *, kind='dialogue', force=None, fix=None):
        idx=len(self.events)
        eid=f'd{self.day:02}-b{idx+1:02}'
        seed=self.seed*100000+self.day*10000+int(clock.replace(':',''))
        seen=[e for e in self.events if speaker in e['witnesses']]
        known = ['You remember reaching Pittsburgh, calling Jo about the van, then waking back in the hotel on Tuesday.'] if speaker=='Phil' else []
        if speaker=='Phil':
            for day in self.past:
                known += [printed(e) for e in day if 'Phil' in e['witnesses']]
        data={'clock':clock,'place':place,'in_earshot':present,'role':speaker,'situation':cue,
              'remembered_before_today':known,'witnessed_today':[printed(e) for e in seen],'choices':choices}
        schema={'type':'object','properties':{'choice':{'type':'string','enum':list(choices)},'line':{'type':'string'}},'required':['choice','line'],'additionalProperties':False}
        payload={'model':MODEL,'stream':False,'think':False,'messages':[{'role':'system','content':CARDS[speaker]+' '+BASE},{'role':'user','content':json.dumps(data,ensure_ascii=False)}],
                 'format':schema,'options':{'temperature':.92,'seed':seed,'num_ctx':12288,'num_predict':230}}
        record={'id':eid,'time':clock,'place':place,'speaker':speaker,'witnesses':present,'kind':kind,
                'seen':[e['id'] for e in seen],'prior_days':len(self.past) if speaker=='Phil' else 0,'cue':cue,'choices':choices,'sample_seed':seed,'input_sha256':digest(payload)}
        if fix is not None:
            assert fix['input_sha256']==record['input_sha256']
            line,choice,origin=fix['line'],fix['choice'],'shared recorded prefix'
        elif force:
            choice,line=force,''
            origin='silent experimental intervention'
        else:
            for attempt in range(3):
                reply=api('chat',payload)
                if reply.get('done_reason')=='stop':
                    try:
                        value=json.loads(reply['message']['content'])
                        choice,line=value['choice'],value['line'].strip()
                        if choice in choices and isinstance(line,str): break
                    except (KeyError, ValueError, AttributeError): pass
                payload['options']['num_predict']+=120
            else: raise ValueError(f'Incomplete performance in {eid}')
            origin='generated'
            record.update(input_sha256=digest(payload), answer_sha256=digest(reply['message']['content']), model_output=reply['message']['content'], elapsed_ns=reply.get('total_duration'))
        record.update(choice=choice,line=line,effect=choices[choice],origin=origin)
        self.events.append(record)
        return choice

    def play_day(self, day, intervention=None, prefix=None):
        self.day=day
        self.events=[]
        beat=self.beat
        beat('06:00','Hearthside room','Phil',['Phil'],"The radio clicks on. Tuesday, February 2. Your clean shirt is folded exactly as the hotel left it. Record a voice memo nobody else can hear. It can be for Jo, for tomorrow's you, or for nobody at all.",{'record':'Phil records a private voice memo.','quiet':'Phil lets the recorder pick up the room noise.'},kind='voice memo',fix=prefix)
        cart=beat('07:20','Hearthside lobby','Phil',TEAM,"Rita and Larry wait at the cue sheet. Beside it is the only weather cartridge: your own cheerful voice doing an old forecast, down to a small breath before your first word. At seven, it can substitute for you on air. Do something with it while they can see. They can hear anything you say.",CART,force=intervention)
        beat('07:21','Hearthside lobby','Rita',TEAM,'You just saw Phil at the cue sheet. Speak to him or to Larry, or let the moment go.',{'tear_carbon':'Rita gives Phil the yellow carbon copy of the cue sheet.','keep_carbon':'Rita clips the yellow carbon back under her sheet.'})
        beat('07:22','Hearthside lobby','Larry',TEAM,"You're beside Rita. Phil can hear you. You can answer either one. The crew still has to get the equipment across the street.",{'take_case':'Larry picks up the equipment case.','set_down':'Larry sets the equipment case on the floor.'})
        route=beat('12:54','coach stop','Phil',['Phil'],"The coach door is open. The projection booth across the street has a service door. There is a stairwell at the hotel where the radio can't be heard. Go where you actually want to go. You can speak under your breath.",ROUTE)
        beat('13:07','locked Rialto booth','Alma',BOOTH,"The door is shut. Only Rita and Larry are with you. You have the key; the last reel has eight minutes left. They can bring a microphone, give you one private line to Nell, or pack up. You have not given permission. Open the conversation however you like.",{'stop_motor':'Alma cuts the projector motor.','keep_running':'Alma leaves the projector turning.'})
        beat('13:08','locked Rialto booth','Larry',BOOTH,"Speak to Alma or Rita. They were not both at the hotel desk. You decide what to repeat, if anything. You have a pencil and an empty reel box.",{'write_label':'Larry turns the reel box over and writes on its blank label.','put_down':'Larry puts down his pencil.'})
        beat('13:09','locked Rialto booth','Rita',BOOTH,"Alma and Larry are here with you. Their words are still in the room. There is exactly one line at seven. Ask for something you actually need, or refuse what's being asked.",{'draw_chair':'Rita pulls a chair over to Alma.','stay_door':'Rita stays by the closed door.'})
        consent=beat('13:10','locked Rialto booth','Alma',BOOTH,"Answer the people here. You can reserve your voice for Nell, let people hear it publicly as well, or withhold it altogether. Their jobs do not oblige you to help.",CONSENT)
        beat('13:11','locked Rialto booth','Larry',BOOTH,"One last thing you could say to either of them before the reel runs out.",{'hold_door':'Larry holds the door for Alma.','stay_put':'Larry stays by the projector.'})
        loc=ROUTE[route]
        call=beat('16:40',loc,'Phil',['Phil'],"There is a telephone here. You can ring Jo in Pittsburgh, or let her have the afternoon to herself. If you call, say what she hears when she picks up. If you leave it alone, keep the line empty.",{'dial':'Jo answers the call.','walk_past':'Phil walks past the phone.'})
        if call=='dial':
            # Each end witnesses the direct telephone exchange, but Jo cannot see Phil's surroundings.
            self.events[-1]['witnesses'].append('Jo')
            beat('16:41','telephone line','Jo',['Phil','Jo'],"Phil is on the telephone. You don't see his surroundings. One couch foot is still stuck. Answer him as you please.",{'stay':'Jo stays on the line for another beat.','hang_up':'Jo hangs up.'})
        else:
            beat('16:41',"Jo's flat",'Jo',['Jo'],"You are alone with the couch and the van booking. You haven't heard from Phil this afternoon. Say something out loud, or don't.",{'ring_neighbor':'Jo rings a neighbor’s bell.','fit_foot':'Jo tries the couch foot again.'})
        wire=beat('18:48',loc,'Phil',['Phil'],"A town phone directory gives the regional station's desk number. You can call Rita there, tape something for yourself or stay quiet. If you call, she picks up; your line is the only part heard at the other end.",{'call_desk':'Rita picks up the station telephone.','memo':'Phil keeps this recording to himself.','put_down':'Phil puts the handset back.'})
        if wire=='call_desk':
            self.events[-1]['witnesses'].append('Rita')
            beat('18:49','telephone line','Rita',['Rita','Phil'],"Phil called your desk. He cannot see the booth or the board. Your answer can be as short as it needs to be.",{'end_call':'Rita hangs up after her reply.'})
        beat('18:52','regional control room','Rita',BOOTH,"The phone is back on its cradle. Larry needs to know what to set up. Tell him what you want, or let him choose. He can still refuse.",{'clear_space':'Rita clears a space beside the patch.','leave_space':'Rita keeps her hands in her pockets.'})
        options=dict(WORK)
        if cart=='pocket_cart':del options['load_cart']
        work=beat('18:55','regional control room','Larry',BOOTH,"You have time to prepare one input. Answer the people in this room. The old recording is usable only if it is here.",options)
        choices={'silence':LINE['silence']}
        if work=='load_cart':choices['weather']=LINE['weather']
        if work=='set_mic' and consent!='decline':choices['private']=LINE['private']
        if work=='set_mic' and consent=='public_too':choices['public']=LINE['public']
        line=beat('19:00','regional control room','Rita',BOOTH,"Seven o'clock. Make the patch or let the slot go. Anything you say is to Larry and Alma inside the control room.",choices)
        if line in ('public','private'):
            beat('19:01','regional control room','Alma',BOOTH,"The microphone is live. "+("Nell has picked up at home. Only she and the two people at the board can hear you." if line=='private' else "Your voice is going over local AM. You cannot know who is listening."),{'speak':'Alma has the live microphone.'},kind='on the line')
        else:
            beat('19:01','regional control room','Alma',BOOTH,"The slot is gone. Say what you want Rita and Larry to hear before you take your coat.",{'leave':'Alma takes her coat.'})
        air={'public':('The AM radio carries Alma saying: '+self.events[-1]['line']), 'private':'The regional frequency carries room tone. You cannot tell why.', 'silence':'The regional frequency carries room tone. You cannot tell why.', 'weather':'You hear your own old voice on AM, right down to the intake of breath.'}[line]
        beat('22:16',loc,'Phil',['Phil'],"At seven you tuned to the regional frequency. What you heard: "+air+" Now, hours later, the pocket recorder clicks on in your hand. Leave a private voice memo for morning about the part of today you can still hear. Speak as Phil, or play out the silence.",{'keep':'Phil lets the last recording play to the end.','cut':'Phil cuts the recording short.'},kind='voice memo')
        result={'day':day,'cart':cart,'route':route,'consent':consent,'equipment':work,'wire':line,'events':self.events}
        self.past.append(self.events)
        save(self.folder/f'day-{day:02}.json',result)
        print(self.folder.name,day,line,flush=True)
        return result

def run(seed, out, rev):
    shoot=Performance(seed,out/f'take-{seed}',rev)
    for day in range(1,5):
        shoot.play_day(day)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if not os.getenv('RUNPOD_POD_ID'):raise SystemExit('Performances run on RunPod.')
    rev=next(x['digest'] for x in api('tags')['models'] if x['name']==MODEL)
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda seed:run(seed,out,rev),(901,902,903)))
    opening=json.loads((out/'take-901/day-01.json').read_bytes())['events'][0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        def branch(cart):
            shoot=Performance(901,out/('fork-'+cart),rev)
            shoot.play_day(1,intervention=cart,prefix=opening)
        list(pool.map(branch,('pocket_cart','leave_cart')))
    save(out/'manifest.json',{'model':MODEL,'revision':rev,'thinking':False,'takes':[901,902,903],'days_per_take':4,'forks':['pocket_cart','leave_cart'],'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
if __name__=='__main__':main()
