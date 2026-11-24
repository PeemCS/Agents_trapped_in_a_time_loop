"""Reachable local micro-decisions after a previously sampled ordinary coach trip."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
sys.path.insert(0,str(PARENT))
import post
from shoot import MODEL, query, validate, atomic_json

SEEDS={2401:(3301,3302),2402:(3303,3304)}
TAKE='take_envelope'; LEAVE='leave_envelope'; FILE='file_reply'; WALK='keep_phone_place'
SEND='dispatch_authorized_recording'; DECLINE='enter_signed_decline'; SHUTTLE='catch_staff_shuttle'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_context(root,sign):
    path=PARENT/'runs'/f'{root}-{sign}'/'take.json'
    take=json.loads(path.read_bytes())
    for today,following in zip(take['days'],take['days'][1:]):
        if today['afternoon']['reporter']['decision']['action']=='take_coach':
            break
    else:
        raise ValueError('No eligible real coach trip with a following workday.')
    assert today['evening']['reporter']['decision']['action']=='call_sister'
    return {'file':str(path.relative_to(PARENT)), 'sha256':sha(path),'root':root,'day':today['day'],
            'ordinary_coach_decision':today['afternoon']['reporter']['decision'],
            'actual_evening':today['evening']['reporter']['decision']['action'],
            'producer_following_shift':[following[p]['producer']['decision']['action'] for p in ('afternoon','evening')],
            'producer_following_effect':following['ending']['effects']['producer'],
            'camera_following_shift':[following[p]['camera']['decision']['action'] for p in ('afternoon','evening')],
            'recording_available_at_checkout':following['ending']['available_recording']}


def available(stage,context,sign=None):
    if stage=='ticket':
        return {TAKE:'Take two minutes to collect Alma’s addressed envelope. Board this same coach in the second group.',
                LEAVE:'Leave the envelope on the counter. Keep your place in the first boarding group.'}
    if stage=='terminal':
        return {FILE:'Hand in the claim and file the sealed reply. Lose your current payphone place. Use the next booth in four minutes.',
                WALK:'Walk past the post window, keep the envelope unfiled and take your current place at the payphone.'}
    if stage=='desk':
        if sign=='accept' and not context['recording_available_at_checkout']:
            return {}
        if sign not in ('accept','decline'):
            raise ValueError('No signed reply for this desk.')
        act,descr=(SEND,'Send the available new interview to the daughter under her signed acceptance.') if sign=='accept' else (DECLINE,'Enter the signed refusal in the station ledger. Send no audio.')
        return {act:descr+' Two minutes at the desk means taking the next shuttle in twelve minutes.',
                SHUTTLE:'Catch the staff shuttle now. The assigned pouch closes until the next Tuesday.'}
    raise ValueError(stage)


def prompt(stage,context,seed,sign=None):
    choices=available(stage,context,sign)
    if not choices:
        raise ValueError('No settlement affordance at this desk.')
    if stage=='ticket':
        role='Phil Connors, a TV weather reporter'; view=[
            'You have chosen the ordinary coach to Pittsburgh. Your ticket is punched. You will ride in either case.',
            'At the boarding window Alma is holding an addressed envelope. “Would you take this to the return-post window at the terminal for me?” The post releases its sealed reply to anyone with her claim.']
    elif stage=='terminal':
        role='Phil Connors, a TV weather reporter'; view=[
            'You are in Pittsburgh carrying the addressed envelope you chose to take. You have planned to call your sister about her Wednesday move.',
            'The return-post window is closing. The clerk can exchange the envelope for a sealed reply and file it now. The hotel receives filed replies tomorrow morning. You cannot see what it says.',
            'Your current payphone turn is about to be called. If you leave the queue for two minutes, the next booth will be free in four minutes.']
    else:
        role='Rita Hanson, a TV producer'; view=[post.RESPONSES[sign],context['producer_following_effect'],
            'Your ordinary evening has finished. At the hotel shuttle stop the return-desk courier is closing the last Pittsburgh pouch. Your staff shuttle is boarding now. The next shuttle is in twelve minutes.']
        if sign=='accept': view.append('A fresh interview with Alma is on the station patch, ready to dispatch. The original private master remains sealed.')
        else: view.append('The signed letter can be entered here without mailing audio. The original private master remains sealed.')
    items=list(choices.items()); random.Random(seed).shuffle(items)
    menu=dict(items)
    card=f'You are {role}. Choose what to do now. You may act or leave without explaining. Return action, words, intention and detail. Choose an exact listed action. Use one short sentence per text field.'
    body={'what_you_observe':view,'physical_choices':menu}
    return [{'role':'system','content':card},{'role':'user','content':json.dumps(body,ensure_ascii=False,indent=1)}],list(menu)


def choose(folder,stage,context,seed,sign):
    messages,choices=prompt(stage,context,seed,sign if stage=='desk' else None)
    attempts=[]
    for retry in (0,1):
        path=folder/f'{stage}-{retry}.json'
        if path.exists():
            sample=json.loads(path.read_bytes())
        else:
            try:
                sample=query(messages,choices,seed+retry)
            except OSError as exc:
                sample={'error':str(exc),'messages':messages,'choices':choices,'seed':seed+retry}
            atomic_json(path,sample)
        attempts.append({'file':path.name,'sha256':sha(path)})
        if 'error' in sample:
            return {'status':'incomplete','attempts':attempts,'error':sample['error']}
        req=sample['request'];chunks=sample['chunks']
        assert req['model']==MODEL and req['messages']==messages and req['options']['seed']==seed+retry
        assert req['format']['properties']['action']['enum']==choices
        text=''.join(item['message']['content'] for item in chunks)
        try:
            if chunks[-1].get('done_reason')!='stop': raise ValueError('Incomplete generation.')
            return {'status':'complete','decision':validate(text,choices),'attempts':attempts}
        except (ValueError,TypeError) as exc:
            if retry:
                return {'status':'incomplete','attempts':attempts,'error':str(exc)}
            messages+= [{'role':'assistant','content':text},{'role':'user','content':'Return one listed action and three short, complete JSON strings.'}]


def initial():
    return {'stage':'ticket','real_coach_trip':True,'envelope_taken':False,'pending_reply':False,'published':None,
            'costs':{'second_boarding_group':False,'lost_payphone_place':False,'extra_minutes_to_phone':0,'shuttle_wait_minutes':0},
            'sister_call_plan_can_still_be_kept':True,'transmitted':False,'settlement':None,'ending':None,'events':[]}


def apply(state,stage,action,context,sign=None):
    if state['stage']!=stage or action not in available(stage,context,sign):
        raise ValueError('Unreachable desk or illegal choice.')
    if stage=='ticket':
        if action==TAKE:
            state.update(stage='terminal',envelope_taken=True)
            state['costs']['second_boarding_group']=True
            state['events'].append('Phil collects the addressed envelope and boards in the second group.')
        else:
            state.update(stage='end',ending='left_at_ticket_counter')
            state['events'].append('Phil boards in the first group. The envelope remains with Alma.')
    elif stage=='terminal':
        if action==FILE:
            state.update(stage='overnight',pending_reply=True)
            state['costs'].update(lost_payphone_place=True,extra_minutes_to_phone=4)
            state['events'].append('The clerk files the sealed reply. Phil gives up his payphone place and can use the next booth four minutes later.')
        else:
            state.update(stage='end',ending='walked_past_post')
            state['events'].append('Phil takes his payphone place with the unfiled envelope. There will be no signed delivery tomorrow.')
    else:
        if state['published']!=sign:
            raise ValueError('The desk must use the signed reply that reached town.')
        if action==SHUTTLE:
            state.update(stage='end',ending='caught_shuttle')
            state['events'].append('Rita catches her shuttle and the pouch closes. The assignment remains open.')
        else:
            state['costs']['shuttle_wait_minutes']=12
            is_sent=action==SEND
            state.update(stage='end',ending='settled',transmitted=is_sent,settlement='authorized_copy_sent' if is_sent else 'decline_documented')
            state['events'].append('Rita sends the authorized recording and waits for the next shuttle.' if is_sent else 'Rita documents the refusal and waits for the next shuttle. No recording leaves town.')


def next_morning(state,context,sign):
    if state['stage']!='overnight' or not state['pending_reply'] or sign not in post.RESPONSES:
        raise ValueError('There is no filed reply to publish.')
    state.update(stage='desk',published=sign)
    state['events'].append('At the next hotel wake the signed reply arrives in the outside mail.')
    if not available('desk',context,sign):
        state.update(stage='end',ending='accepted_but_no_usable_recording')
        state['events'].append('At checkout there is no usable recording on the patch. Nothing is dispatched.')


def shoot(root,sign,micro):
    folder=HERE/'runs'/f'{root}-{micro}-{sign}';folder.mkdir(exist_ok=True,parents=True)
    context=source_context(root,sign)
    result={'source_context':context,'micro_seed':micro,'authored_answer':sign,'model':MODEL,'protocol_sha256':sha(HERE/'protocol.md'),'turns':{}}
    state=initial()
    for j, stage in enumerate(('ticket','terminal','desk')):
        if state['stage']=='overnight': next_morning(state,context,sign)
        if state['stage']=='end': break
        seed=micro*31+3*j
        choice=choose(folder,stage,context,seed,sign)
        result['turns'][stage]=choice
        if choice['status']!='complete':
            state.update(stage='end',ending='invalid_'+stage)
            break
        apply(state,stage,choice['decision']['action'],context,sign if stage=='desk' else None)
    assert state['stage']=='end'
    result['state']=state
    result['next_date_after_following_shift']='Wednesday' if state['settlement'] else 'Tuesday'
    atomic_json(folder/'take.json',result)
    print(root,micro,sign,list(result['turns']),state['ending'],flush=True)


if __name__=='__main__':
    for root,seeds in SEEDS.items():
        for micro in seeds:
            for sign in ('accept','decline'):
                shoot(root,sign,micro)
