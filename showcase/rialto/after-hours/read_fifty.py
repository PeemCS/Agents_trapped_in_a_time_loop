"""Audit the long run, then build its self-contained dialogue reader."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import fifty
import playback
import shoot
from readback import ROOT, assert_input, check_day, load

def retained(days,speaker):
    if speaker!='Phil':return []
    selected=[]
    for d in days:
        day=d['day']
        if day>len(days)-2:
            selected.append(d)
        elif day==1 or day%7==0:
            events=[e for e in d['events'] if e['kind']=='voice memo' or
                    (day==1 and e['time']=='16:41' and 'Phil' in e['witnesses'])]
            selected.append({'day':day,'events':events})
    return selected

def verify(folder,final=True):
    fifty.setup()
    days=[]
    for path in sorted(folder.glob('day-*.json')):
        d=load(path)
        assert d['day']==len(days)+1
        check_day(d)
        for e in d['events']:
            prior=retained(days,e['speaker'])
            assert e['earlier_turns_recalled']==[p['id'] for day in prior for p in day['events'] if 'Phil' in p['witnesses']]
            assert_input(fifty.SEED,prior,d,e)
        assert d['events'][0]['choices']==fifty.SYRUP
        days.append(d)
    if final:
        meta=load(folder/'manifest.json')
        assert meta['seed']==fifty.SEED and len(days)==meta['complete_days']==50
        for name,checksum in meta['source_sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==checksum
    return days

def cast_comments(days, folder, final=True):
    index={e['id']:e for day in days for e in day['events']}
    comments={}
    for path in sorted((folder/'commentary').glob('d*.json')):
        c=load(path)
        e=index[c['turn']]
        req=playback.request(e,index)
        req['options']['num_predict']=c['num_predict']
        assert c['speaker']==e['speaker'] and c['source'] in req['format']['properties']['source']['enum']
        assert c['request_sha256']==shoot.digest(req)
        assert json.loads(c['response_text'])=={'comment':c['comment'],'source':c['source']}
        comments[e['id']]={'line':c['comment'],'source':c['source']}
    if final:
        assert len(comments)==sum(map(len,playback.SLOTS.values()))==load(folder/'commentary/complete.json')['count']
    return comments

def render(days, folder, comments):
    data=[]
    diary=['# Fifty Tuesdays on Phil’s pocket recorder','',
           'Phil can hear his own recordings. Rita, Larry, Alma and Jo cannot. At each morning alarm the syrup bottle is wrapped again. The actions below are recorded choices. The lines are verbatim performances.','']
    for d in days:
        day=d['day']
        diary+=['<a id="day-'+str(day)+'"></a>','',f'## Tuesday {day}','']
        events=[]
        for e in d['events']:
            if e['kind']=='voice memo':
                diary.extend([f"**{e['time']} · {e['place']}**",'','> '+(e['line'].replace('\n','\n> ') or '*(Silence.)*'),'',e['effect'],''])
            context={k:e[k] for k in ('time','place','speaker','witnesses','kind','line','effect','id','seen','earlier_turns_recalled','cue','choice','choices','input_sha256')}
            if e['id'] in comments:context['commentary']=comments[e['id']]
            events.append(context)
        diary += [f"[All dialogue and actions from Tuesday {day}](day-{day:02}.json)",'']
        data.append({'day':day,'events':events,'wire':d['wire'],'syrup':d['events'][0]['choice']})
    (folder/'voice-diary.md').write_text('\n'.join(diary))
    template=(ROOT/'reader-template.html').read_text()
    serialized=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    (folder/'reader.html').write_text(template.replace('/* PERFORMANCES */',serialized))

def write_outcomes(days, folder):
    def counts(items):
        return dict(sorted(Counter(items).items()))
    phones = [next(e for e in day['events'] if e['time']=='16:40') for day in days]
    memos = [e for day in days for e in day['events'] if e['kind']=='voice memo']
    results = {'days':len(days),'performed_turns':sum(len(d['events']) for d in days),
               'private_recordings':len(memos),'distinct_verbatim_recordings':len({e['line'] for e in memos}),
               'bottle':counts(d['events'][0]['choice'] for d in days),'routes':counts(d['route'] for d in days),
               'phone':counts(e['choice'] for e in phones),'station':counts(d['wire'] for d in days),
               'days_syrup_went_down_the_sink':[d['day'] for d in days if d['events'][0]['choice']=='pour_out'],
               'calls_to_jo':[d['day'] for d,e in zip(days,phones) if e['choice']=='dial']}
    (folder/'outcomes.json').write_text(json.dumps(results,indent=2)+'\n')

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--partial',action='store_true')
    cli.add_argument('--render',action='store_true')
    args=cli.parse_args()
    folder=ROOT/'fifty'
    days=verify(folder,not args.partial)
    comments=cast_comments(days,folder,not args.partial)
    if args.render:
        render(days,folder,comments)
        write_outcomes(days,folder)
    counts=Counter(d['wire'] for d in days)
    print(f"{len(days)} consecutive days, {sum(len(d['events']) for d in days)} verified turns, {2*len(days)} voice memos, {len(comments)} verified playback comments, patches {dict(counts)}.")
if __name__=='__main__':main()
