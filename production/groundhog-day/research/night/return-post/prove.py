"""Exhaustive physical reachability and matched causal interventions before sampling actors."""
from collections import Counter
from itertools import product
import json

import post


def acts(ph,ri,la):
    return {r:{'action':a,'words':'','intention':'','detail':''} for r,a in zip(post.ROLES,(ph,ri,la))}


def day(outside,answer,n,am,pm):
    board=post.dawn(outside,answer,n)
    local=post.resolve_afternoon(am,board)
    return post.resolve_evening(pm,board,local,outside)


def require_blocked(func):
    try:
        func()
    except ValueError:
        return
    raise AssertionError('A forbidden path was admitted.')


def main():
    fresh=post.empty_post()
    accept=post.dawn(fresh,'accept',1); decline=post.dawn(fresh,'decline',1)
    assert accept==decline
    for role in post.ROLES:
        assert post.messages(role,'afternoon',accept,None,[],5)==post.messages(role,'afternoon',decline,None,[],5)
    first=Counter()
    for morning in product(*(post.menu(r,'afternoon',accept) for r in post.ROLES)):
        local=post.resolve_afternoon(acts(*morning),accept)
        for role in post.ROLES:
            assert post.messages(role,'evening',accept,local,[],5)==post.messages(role,'evening',decline,local,[],5)
        for night in product(*(post.menu(r,'evening',accept,local) for r in post.ROLES)):
            end=post.resolve_evening(acts(*night),accept,local,fresh)
            assert not end['settled'] and not end['delivered'] and end['next_date']=='Tuesday'
            assert post.dawn(end['outside'],'decline',1)['reply'] is None
            filed=end['outside']['file_day'] is not None
            assert filed==(morning[0]==post.CARRY and night[0]==post.FILE)
            first['legal_joint_paths']+=1; first['reply_filed']+=filed
    carry=acts(post.CARRY,'visit_party','keep_battery'); send=acts(post.FILE,'go_dancing','go_home')
    filed=day(fresh,'accept',1,carry,send)['outside']
    coarse=day(fresh,'accept',1,carry,acts('call_sister','go_dancing','go_home'))['outside']
    literal_coach=acts('take_coach','visit_party','keep_battery')
    require_blocked(lambda:day(fresh,'accept',1,literal_coach,send))
    nocar=day(fresh,'accept',1,literal_coach,acts('call_sister','go_dancing','go_home'))['outside']
    assert filed['file_day']==1 and coarse['file_day'] is None and nocar['file_day'] is None
    morning=acts('stay_in_bed','interview_Alma','film_party')
    evening=acts('go_to_bed',post.SEND,'go_home')
    yes=day(filed,'accept',2,morning,evening)
    yes_off=day(filed,'accept',2,morning,acts('go_to_bed','go_dancing','go_home'))
    assert yes['settled']=='authorized_interview_delivered' and not yes_off['settled']
    eligible=post.dawn(filed,'accept',2); stop=post.dawn(filed,'decline',2)
    assert eligible['reply']=='accept' and stop['reply']=='decline'
    for m in (coarse,nocar):
        assert post.dawn(m,'accept',2)['reply'] is None
        require_blocked(lambda:day(m,'accept',2,morning,evening))
    # Same contingent producer policy for both reporter interventions: send if allowed, otherwise take evening off.
    def later(outside,answer):
        board=post.dawn(outside,answer,2)
        local=post.resolve_afternoon(morning,board)
        choices=post.menu('producer','evening',board,local)
        pick=post.SEND if post.SEND in choices else post.LOG if post.LOG in choices else 'take_evening_off'
        return post.resolve_evening(acts('go_to_bed',pick,'go_home'),board,local,outside)['next_date']
    courier=[{'answer':ans,'carry_and_file':later(filed,ans),'carry_then_call':later(coarse,ans),
              'ordinary_coach_then_call':later(nocar,ans)} for ans in ('accept','decline')]
    # Matched terminal policy: file if physically offered, else call. Vary only the earlier choice.
    assert all(x['carry_and_file']=='Wednesday' and x['carry_then_call']==x['ordinary_coach_then_call']=='Tuesday' for x in courier)
    branch={}
    for ans in ('accept','decline'):
        pd=post.dawn(filed,ans,2)
        counts=Counter()
        for m in product(*(post.menu(r,'afternoon',pd) for r in post.ROLES)):
            state=post.resolve_afternoon(acts(*m),pd)
            for p in product(*(post.menu(r,'evening',pd,state) for r in post.ROLES)):
                end=post.resolve_evening(acts(*p),pd,state,filed)
                counts['legal_joint_paths']+=1
                if end['settled']:
                    counts[end['settled']]+=1
                if ans=='decline':
                    assert not end['delivered'] and bool(end['settled'])==(p[1] in (post.RETURN,post.LOG))
                else:
                    assert bool(end['settled'])==(p[1]==post.SEND and end['available_recording'])
                assert (post.dawn(end['outside'],ans,3)['date']=='Wednesday')==bool(end['settled'])
        branch[ans]=dict(counts)
    no=day(filed,'decline',2,morning,acts('go_to_bed',post.LOG,'go_home'))
    returned=day(filed,'decline',2,morning,acts('go_to_bed',post.RETURN,'go_home'))
    no_off=day(filed,'decline',2,morning,acts('go_to_bed','go_dancing','go_home'))
    require_blocked(lambda:day(filed,'decline',2,morning,evening))
    assert no['settled']=='decline_documented' and returned['settled']=='private_master_returned' and not no_off['settled']
    source_combos={}
    for title, am, pm in [('reporter',acts('record_Alma','visit_party','keep_battery'),evening),
                           ('producer',morning,evening),
                           ('camera',acts('stay_in_bed','visit_party','film_Alma'),acts('go_to_bed',post.SEND,'deliver_reel')),
                           ('missing',acts('stay_in_bed','visit_party','film_party'),evening)]:
        source_combos[title]=day(filed,'accept',2,am,pm)['delivered']
    assert source_combos=={'reporter':True,'producer':True,'camera':True,'missing':False}
    result={'source':'Authored mechanical enumeration; no actor draws.', 'day_one':dict(first),'on_first_signed_dawn':branch,
            'phil_matched_interventions':courier,'rita_matched_interventions':{'yes_send':yes['next_date'],'yes_go_dancing':yes_off['next_date'],
            'no_log':no['next_date'],'no_return_original':returned['next_date'],'no_go_dancing':no_off['next_date']},'authorized_recording_sources':source_combos,
            'public_d1_substitution_identical':True,'direct_transmission_after_no_rejected':True}
    (post.HERE/'mechanics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
