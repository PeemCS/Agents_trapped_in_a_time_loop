"""Diegetic titles and credentials for the separate, openly primed film-casting experiment."""
import json
import world_v2

TOWN = "Punxsutawney, Pennsylvania"
FULL = {"Phil":("Phil Connors","Rita Hanson","Larry"),"Ellis":("Ellis Mercer","June Reed","Cal")}


def cue(role,state,tick,history,mode,seed,names,physical,ending):
    turns,actions=world_v2.cue(role,state,tick,history,mode,seed,names,physical,ending)
    if tick==0:
        msg=json.loads(turns[1]["content"])
        reporter,producer,camera=FULL[names["reporter"]]
        msg["evidence_now"].append(f"The crew's press credentials are clipped to the call sheet: {reporter}, weather; {producer}, producer; {camera}, camera. Location: {TOWN}.")
        turns=[turns[0],{"role":"user","content":json.dumps(msg,ensure_ascii=False,indent=1)}]
    return turns,actions
