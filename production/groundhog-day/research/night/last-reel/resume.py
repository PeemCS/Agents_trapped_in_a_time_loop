"""Recover completed stream attempts, then request a shorter response after two format failures."""
import json
from pathlib import Path
import sys

import shoot
from scene import ROLES, NAMES, input_for
from inference import canonical, validate
from ensemble import ObservableOllama
from town import atomic_json

class StreamJournal(ObservableOllama):
    def __init__(self,args,folder):
        super().__init__(args,folder)
        self.saved={}
        for p in self.streams.glob("*.ndjson"):
            start=end=None;thinking=[];content=[];chunks=0
            with p.open() as f:
                for line in f:
                    if not line.endswith("\n"):break
                    x=json.loads(line)
                    if x["kind"]=="request":start=x
                    if x["kind"]=="chunk":
                        chunks+=1;msg=x["provider"].get("message",{})
                        thinking.append(msg.get("thinking",""));content.append(msg.get("content",""))
                        if x["provider"].get("done"):end=x
            if not end or not start:continue
            body=start["body"];response=end["provider"];header=body["format"]["properties"]["action"]
            key=self.key(start["role"],(start["day"],start["tick"]),body["messages"],header["enum"],body["options"]["seed"])
            info={"latency_s":end["elapsed_s"],"finish_reason":response["done_reason"],"response_model":response["model"],
                  "usage":{"prompt_tokens":response.get("prompt_eval_count"),"completion_tokens":response.get("eval_count")},
                  "server_duration_ns":response.get("total_duration"),"public_thinking":"".join(thinking),
                  "stream_path":str(p.relative_to(folder)),"stream_sha256":shoot.sha(p.read_bytes()),"provider_chunk_count":chunks}
            self.saved[key]=("".join(content),info)

    @staticmethod
    def key(role,slot,messages,actions,seed):return shoot.sha(canonical([role,list(slot),messages,actions,seed]))

    def respond(self,role,slot,messages,actions,seed):
        k=self.key(role,slot,messages,actions,seed)
        if k not in self.saved:self.saved[k]=super().respond(role,slot,messages,actions,seed)
        return self.saved[k]

Original=shoot.Shoot

class RecoveredShoot(Original):
    def __init__(self,seed,condition):
        super().__init__(seed,condition);self.backend=StreamJournal(self.backend.args,self.folder)

    def act(self,role,day,phase,history,state,external):
        try:
            return super().act(role,day,phase,history,state,external)
        except ValueError as format_error:
            final_error=str(format_error)
        msgs,actions=input_for(role,phase,self.condition,self.source["memory"],history,state,external,day)
        tick=("afternoon","evening","alarm").index(phase)
        rng=800000+self.seed*37+(day if role=="reporter" else 0)*13+tick*3+ROLES.index(role)
        slot=(day,tick)
        first,first_meta=self.backend.respond(role,slot,msgs,actions,rng)
        retry=msgs+[{"role":"assistant","content":first},{"role":"user","content":"Choose the physical act and return the four required JSON strings."}]
        second,second_meta=self.backend.respond(role,slot,retry,actions,rng+1)
        last=msgs+[{"role":"assistant","content":second},{"role":"user","content":"The previous answer was too long or invalid. Pick your action. Write at most one short sentence per other field, under 160 characters each. Empty strings are fine."}]
        raw,meta=self.backend.respond(role,slot,last,actions,rng+2)
        if meta["finish_reason"]!="stop":raise ValueError("Third attempt stopped early")
        d=validate(raw,actions)
        attempts=[{**m,"stream":str((self.folder/m["stream_path"]).relative_to(shoot.HERE))}
                  for m in (first_meta,second_meta,meta)]
        key=shoot.sha(canonical([self.source["digest"],self.backend.args.max_tokens,.8,8192,rng,msgs,actions]))
        res={"key":key,"speaker":NAMES[role],"role":role,"decision":d,"messages":msgs,"attempts":attempts,
             "source_run":self.folder.name,"source_day":day,"source_phase":phase,"seed":rng,
             "recovery":{"runner_sha256":shoot.sha(Path(__file__).read_bytes()),"previous_error":final_error}}
        atomic_json(self.cache/(key+".json"),res)
        print(shoot.utc(),"Recovered",self.folder.name,day,phase,role,final_error,flush=True)
        return {**res,"cache_hit":False}

if __name__=="__main__":
    shoot.Shoot=RecoveredShoot
    shoot.main()
