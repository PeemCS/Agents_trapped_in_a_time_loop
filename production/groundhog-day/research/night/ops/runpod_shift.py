"""Private rehearsal operations. Reads only a newly created pod by its creation receipt."""
import argparse
import base64
import datetime as dt
import gzip
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

STATE = Path.home()/"Projects/finishers/nights/2026-11-23-groundhog-rehearsal"
REC = STATE/"created-pod.json"
API = "https://api.runpod.io/v2/"
GPU = os.environ.get("TOWN_GPU", "NVIDIA H100 NVL")
NAME = "groundhog-rehearsal-20261123"
TTL = 180
MAX_COMPUTE_RATE = 4.50
MAX_SPEND = 40.0
def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()
def token():
    if os.getenv("RUNPOD_API_KEY"):
        return os.environ["RUNPOD_API_KEY"]
    p=Path.home()/".config/finisher/keys.env"
    return next(s.partition("=")[2].strip().strip('"').strip("'") for s in p.read_text().splitlines() if s.startswith("RUNPOD_API_KEY="))
def api(route, method="GET", body=None):
    req=urllib.request.Request(API+route,method=method,headers={"Authorization":"Bearer "+token(),"Content-Type":"application/json"},
                               data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req,timeout=50) as res:
            raw=res.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Runpod {method} {route} returned {e.code}: "+e.read(400).decode(errors="replace")) from None
def append(event,**details):
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/"operations.jsonl").open("a") as f:
        print(json.dumps({"utc":now(),"event":event,**details}),file=f)
def safe(p):
    return {k:p.get(k) for k in ("id","name","status","cost","createdAt","startedAt","gpu","ssh","dataCenterId")}
def own():
    return json.loads(REC.read_text())["id"]
def exec_own(cmd,timeout=15):
    j=api("pods/"+own()+"/exec","POST",{"command":cmd,"timeoutSeconds":timeout})
    return j.get("result",j)
def create():
    if REC.exists() or (STATE/"allocation-pending").exists():
        raise SystemExit("Existing creation receipt or pending allocation. Reconcile before any new create.")
    quotes=api("catalog/gpus")["gpus"]
    quote=next(i for i in quotes if i["id"]==GPU)["price"]["secure"]
    # Reserve $2/h for any storage over the 3h hard window, and $8 for optional metered comparison calls.
    committed=(quote+2)*(TTL/60)+8
    if not (0<quote<=MAX_COMPUTE_RATE and committed<=MAX_SPEND):
        raise SystemExit("Quote exceeds rehearsal reserve.")
    existing=api("pods")["pods"]
    if any(i.get("name")==NAME for i in existing):
        raise SystemExit("Matching resource exists without a local creation receipt.")
    guard=(Path.home()/".claude/skills/night-shift/scripts/pod_guard.sh").read_text()
    spot='    # Try every documented way; the first that works ends this container.'
    assert spot in guard
    guard=guard.replace(spot,'''    # The v2 API accepts the provider's automatically injected pod-scoped credential.
    if [ -n "${RUNPOD_API_KEY:-}" ] && [ -n "${RUNPOD_POD_ID:-}" ]; then
        curl --fail --silent --show-error --max-time 12 -X POST \\
            "https://api.runpod.io/v2/pods/$RUNPOD_POD_ID/action" \\
            -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" \\
            --data '{"action":"stop"}' >/dev/null && return
    fi
'''+spot)
    guard64=base64.b64encode(gzip.compress(guard.encode())).decode()
    loader='echo "$GUARD_GZ" | base64 -d | gzip -dc >/guard.sh && chmod 700 /guard.sh && (nohup /guard.sh >/tmp/guard-boot.log 2>&1 &); exec /start.sh'
    pub=(Path.home()/".ssh/runpod_zjh5z1h7s12wtk.pub").read_text().strip()
    data={"name":NAME,"cloud":"SECURE","gpu":{"id":GPU,"count":1,"minCudaVersion":"12.8"},
          "image":"runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404","disk":65,"ports":["22/tcp"],"startSsh":True,
          "entrypoint":["/bin/bash","-c"],"cmd":[loader],"env":{"GUARD_GZ":guard64,"GUARD_LEASE_MIN":"30","GUARD_TTL_MIN":str(TTL),"GUARD_IDLE_MIN":"40","PUBLIC_KEY":pub}}
    STATE.mkdir(parents=True,exist_ok=True)
    append("reserved",quote_usd_h=quote,max_committed_usd=committed,ttl_min=TTL,existing_resource_count=len(existing))
    (STATE/"allocation-pending").write_text(now())
    res=api("pods","POST",data)
    p=res.get("pod",res)
    assert p["id"] and p.get("name")==NAME
    REC.write_text(json.dumps(safe(p),indent=2))
    append("created",id=p["id"],name=NAME,rate=p.get("cost"),created_at=p.get("createdAt"))
    print(json.dumps(safe(p)))
    if p.get("cost",0)>MAX_COMPUTE_RATE:
        stop()
        raise SystemExit("Actual rate exceeded reservation; stopped.")
def stop():
    j=api("pods/"+own()+"/action","POST",{"action":"stop"})
    append("stop-request",id=own())
    print("Stop result:",j.get("pod",j).get("status"))
def terminate():
    # Dedicated, ephemeral rehearsal instance, created and tracked by this process.
    j=api("pods/"+own()+"/action","POST",{"action":"terminate"})
    append("termination-request",id=own())
    print("Termination response:",j.get("pod",j).get("status","accepted"))
def main():
    p=argparse.ArgumentParser()
    p.add_argument("verb",choices=["create","get","renew","exec","stop","terminate","billing"])
    p.add_argument("args",nargs=argparse.REMAINDER)
    a=p.parse_args()
    if a.verb=="create":return create()
    if a.verb=="get":
        result=api("pods/"+own());print(json.dumps(safe(result.get("pod",result)),indent=2))
    elif a.verb=="exec":print(json.dumps(exec_own(a.args)))
    elif a.verb=="renew":print(json.dumps(exec_own(["bash","-lc",'test -s /workspace/.guard/heartbeat && date -d "+30 minutes" +%s > /workspace/.guard/lease && cat /workspace/.guard/heartbeat'])))
    elif a.verb=="stop":stop()
    elif a.verb=="terminate":terminate()
    elif a.verb=="billing":
        result=api("billing/pods?podId="+own());(STATE/"billing.json").write_text(json.dumps(result,indent=2));print(json.dumps(result)[:2000])
if __name__=="__main__":
    main()
