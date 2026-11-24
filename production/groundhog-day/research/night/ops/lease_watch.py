"""Run beside the orchestrator. A stale local heartbeat never renews a cloud lease."""
import datetime as dt
import time
from runpod_shift import REC, STATE, own, api, append, exec_own, terminate

def main():
    created=dt.datetime.fromisoformat(__import__("json").loads(REC.read_text())["createdAt"].replace("Z","+00:00")).timestamp()
    heartbeat=STATE/"orchestrator-alive"
    last_renewal=0
    while time.time()-created<4*3600:
        try:
            p=api("pods/"+own());p=p.get("pod",p)
            if p.get("status") in ("TERMINATED","DELETED"):
                return
            if time.time()-created>=180*60 or p.get("status")=="EXITED":
                terminate()
                return
            recent=heartbeat.exists() and time.time()-heartbeat.stat().st_mtime<14*60
            if recent and time.time()-last_renewal>=8*60:
                r=exec_own(["bash","-lc",'test -s /workspace/.guard/heartbeat && date -d "+30 minutes" +%s > /workspace/.guard/lease && cat /workspace/.guard/heartbeat'])
                if r.get("exitCode")==0:
                    append("lease-renewed",cloud_heartbeat=r["stdout"].strip())
                    last_renewal=time.time()
        except Exception as e:
            if "404" in str(e):
                append("watcher-closed",reason="owned resource absent")
                return
            append("watcher-error",error=str(e)[:250])
        time.sleep(45)
if __name__=="__main__":main()
