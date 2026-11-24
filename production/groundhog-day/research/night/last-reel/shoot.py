"""Run a three-agent recurring day, caching exact sampled inputs and retaining every stream."""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
sys.path.insert(0,str(NIGHT/"thinking"))
from ensemble import ObservableOllama, utc
from inference import canonical, validate
from town import atomic_json, exclusive
from scene import ROLES, NAMES, ALARM, input_for, afternoon, evening

SOURCES={721:NIGHT/"takes/badges/film/seed-721.json",731:NIGHT/"thinking/runs/standard/seed-731.json"}
STATE=Path.home()/"Projects/finishers/nights/2026-11-23-groundhog-rehearsal"

def sha(data):return hashlib.sha256(data).hexdigest()

def initial(seed):
    raw=SOURCES[seed].read_bytes();row=json.loads(raw)
    if row["status"]!="complete":raise ValueError("Source needs a final commit")
    es=row["events"]
    for cut in range(2,len(es)):
        ride,night,wake=es[cut-2:cut+1]
        if ride["decision"]["action"]=="take_coach_to_Pittsburgh" and night["decision"]["action"]=="call_sister" and wake["clock"]=="6:00 am" and wake["origin"]=="inn":
            return {"source":str(SOURCES[seed].relative_to(NIGHT)),"sha256":sha(raw),"events":[r["id"] for r in (ride,night,wake)],"digest":row["configuration"]["model_revision"],
                    "memory":[{"when":"last Tuesday afternoon","witnessed":ride["effect"].split(". ")[0]+"."},{"when":"last evening in Pittsburgh","witnessed":"You reached your sister from the terminal payphone. She confirmed the van booking for Wednesday.","your_words":night["decision"]["words"]},
                              {"when":"this morning","witnessed":"After that evening in Pittsburgh you woke back in your hotel bed. The radio again announced Tuesday, February 2."}]}
    raise ValueError("No verified ride, call and next wake")

class Shoot:
    def __init__(self,seed,condition):
        self.seed=seed;self.condition=condition;self.folder=HERE/"runs"/(str(seed)+"-"+condition)
        self.folder.mkdir(parents=True,exist_ok=True)
        self.cache=HERE/"requests";self.cache.mkdir(exist_ok=True)
        self.source=initial(seed);self.tag=json.loads((NIGHT/"takes/q27/model.json").read_bytes())
        self.backend=ObservableOllama(SimpleNamespace(model=self.tag["name"],temperature=.8,num_ctx=8192,max_tokens=3072,timeout=420,base_url="http://127.0.0.1:18527"),self.folder)

    def act(self,role,day,phase,history,state,external):
        msgs,actions=input_for(role,phase,self.condition,self.source["memory"],history,state,external,day)
        tick=("afternoon","evening","alarm").index(phase)
        # Repeat NPC sampling on identical inputs. Their own day resets, whereas Phil remembers.
        rng=800000+self.seed*37+(day if role=="reporter" else 0)*13+tick*3+ROLES.index(role)
        key=sha(canonical([self.source["digest"],self.backend.args.max_tokens,.8,8192,rng,msgs,actions]))
        target=self.cache/(key+".json")
        if target.exists():
            res=json.loads(target.read_bytes())
            return {**res,"cache_hit":True}
        raw,meta=self.backend.respond(role,(day,tick),msgs,actions,rng)
        attempts=[{**meta,"stream":str((self.folder/meta["stream_path"]).relative_to(HERE))}]
        try:
            if meta["finish_reason"]!="stop":raise ValueError("incomplete decision")
            decision=validate(raw,actions)
        except (TypeError,ValueError):
            repair=msgs+[{"role":"assistant","content":raw},{"role":"user","content":"Choose the physical act and return the four required JSON strings."}]
            raw,meta=self.backend.respond(role,(day,tick),repair,actions,rng+1)
            attempts.append({**meta,"stream":str((self.folder/meta["stream_path"]).relative_to(HERE))})
            if meta["finish_reason"]!="stop":raise ValueError("Incomplete repaired decision")
            decision=validate(raw,actions)
        res={"key":key,"speaker":NAMES[role],"role":role,"decision":decision,"messages":msgs,"attempts":attempts,"source_run":self.folder.name,"source_day":day,"source_phase":phase,"seed":rng}
        atomic_json(target,res)
        return {**res,"cache_hit":False}

    def run(self):
        dest=self.folder/"take.json"
        rev=sha((HERE/"scene.py").read_bytes()+(HERE/"shoot.py").read_bytes())
        with exclusive(self.folder/".lock"):
            if dest.exists():
                out=json.loads(dest.read_bytes())
                if out["code"]!=rev:raise ValueError("Incompatible shot protocol")
            else:out={"code":rev,"condition":self.condition,"seed":self.seed,"source":self.source,"days":[],"started":utc(),"status":"partial"}
            if out["status"]=="complete":return
            history=list(out.get("reporter_memory",[]));external=out.get("external_receipt",False)
            for day in range(len(out["days"])+1,4):
                state={"afternoon_memory":{}}
                with ThreadPoolExecutor(max_workers=3) as pool:
                    jobs={r:pool.submit(self.act,r,day,"afternoon",history,state,external) for r in ROLES}
                    turns={r:j.result() for r,j in jobs.items()}
                    state=afternoon({k:v["decision"] for k,v in turns.items()})
                    daily=state["afternoon_memory"]["reporter"]+list(state["seen"]["reporter"])
                    jobs={r:pool.submit(self.act,r,day,"evening",history+daily,state,external) for r in ROLES}
                    nights={r:j.result() for r,j in jobs.items()}
                ending=evening({k:v["decision"] for k,v in nights.items()},state)
                history.append({"afternoon":state["effects"]["reporter"],"evening":ending["effects"]["reporter"],"what_you_said":nights["reporter"]["decision"]["words"],"your_last_intention":nights["reporter"]["decision"]["intention"],"next_wake":ALARM})
                if ending["both_at_party"]:history[-1]["also_seen"]="You saw Rita at the ballroom."
                external=external or ending["delivered"]
                out["days"].append({"day":day,"afternoon":turns,"evening":nights,"afternoon_state":state,"ending":ending})
                out.update({"reporter_memory":history,"external_receipt":external})
                atomic_json(dest,out)
            alarm=self.act("reporter",4,"alarm",history,{"afternoon_memory":{}},external)
            out.update({"last_alarm":alarm,"status":"complete","finished":utc()});atomic_json(dest,out)
            print(utc(),self.seed,self.condition,"completed",flush=True)

def main():
    tag=json.loads((NIGHT/"takes/q27/model.json").read_bytes())
    with urlopen("http://127.0.0.1:18527/api/tags",timeout=20) as f:
        assert any(z["name"]==tag["name"] and z["digest"]==tag["digest"] for z in json.load(f)["models"])
    # Priors and seed order fixed in advance. Each whole take is atomic and resumable.
    for seed,cond in [(721,"uncued"),(721,"hypothesis"),(721,"library"),(731,"hypothesis"),(731,"uncued"),(731,"library")]:
        Shoot(seed,cond).run()
    (STATE/"last-reel-complete").touch()

if __name__=="__main__":main()
