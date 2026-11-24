"""Two preselected live repeats after adding reservations to the real decision loop."""
import json,hashlib,subprocess,urllib.request,math
from run import HERE,HOST,MODEL,ROLES,run_trial,ask_route,write
def main():
    with urllib.request.urlopen(HOST+"/api/tags",timeout=5) as result:tag=next(t for t in json.load(result)["models"] if t["name"]==MODEL)
    pipe=subprocess.Popen(["node",str(HERE/"resolve.cjs")],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    try:
        world=ask_route(pipe,{"world":True});runs=[]
        for seed in [913,927]:runs.append(run_trial("coordinated",seed,3,tuple(ROLES),world,pipe,tag["digest"]))
    finally:pipe.stdin.close();pipe.wait()
    samples=[];keys=set();changed=0;ack=0;smallest=999
    for r in runs:
        before={}
        for rows in r["ticks"]:
            for e in rows:
                raw=(HERE/e["raw"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==e["raw_sha256"]
                request=json.loads(raw)["request"];obs=json.loads(request["messages"][1]["content"]);keys.add(e["id"])
                assert obs["you_are_at"]==e["start"]
                if e["role"] in before:
                    old=before[e["role"]];assert obs["your_own_previous_walks"][-1]["resolved"]==old["resolved"]
                    if old["status"]=="reserved-nearby":
                        assert obs["your_own_previous_walks"][-1]["status"]==old["status"];ack+=1
                changed+=e["status"]=="reserved-nearby";smallest=min(smallest,e["slotMinimumGap"])
                samples.append({"id":e["id"],"raw_sha256":e["raw_sha256"],"status":e["status"],"requested":e["requested"],"resolved":e["resolved"]});before[e["role"]]=e
    assert len(keys)==18 and smallest>=.52-1e-8
    (HERE/"coordinated.js").write_text("window.CoordinatedTakes = "+json.dumps(runs,separators=(",",":"),ensure_ascii=False)+";\n")
    write(HERE/"evidence"/"prospective.json",{"seeds":[913,927],"live_calls":18,"unique_event_ids":len(keys),"redirected":changed,
          "later_prompts_receiving_redirect":ack,"smallest_crew_gap_metres":smallest,"events":samples})
    print(18,changed,ack,smallest)
if __name__=="__main__":main()
