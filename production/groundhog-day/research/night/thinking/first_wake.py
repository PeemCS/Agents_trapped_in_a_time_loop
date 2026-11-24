"""An observable reasoning-mode branch at a witnessed Pittsburgh-to-hotel wake."""
import datetime
import json
import sys
import time
from pathlib import Path
from urllib.request import Request,urlopen

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"audition"))
from deliberate import checkpoint, MODEL, object_schema,validate
from town import atomic_json


def call(endpoint,body,timeout=210):
    req=Request("http://127.0.0.1:18527"+endpoint,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with urlopen(req,timeout=timeout) as response:return json.load(response)


def main():
    source=checkpoint(701);assert source["sources"][-1]=="d03-t00-reporter"
    show=call("/api/show",{"model":MODEL});settings=show.get("thinking",{})
    payload={"model":MODEL,"messages":source["messages"],"think":True,"format":object_schema(source["legal"]),"stream":False,
             "options":{"temperature":.8,"num_ctx":8192,"num_predict":2048,"seed":961}}
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();begin=time.monotonic()
    ans=call("/api/chat",payload)
    msg=ans["message"];captured=msg.get("thinking","")
    result={"model":MODEL,"model_revision":source["model_revision"],"source_sha256":source["sha256"],"event":source["sources"][-1],
            "branch":True,"start_utc":start,"wall_s":round(time.monotonic()-begin,3),"reported_thinking_support":settings,
            "request":payload,"response":ans}
    atomic_json(HERE/"first-wake.json",result)
    parsed=None
    try:parsed=validate(msg["content"],source["legal"])
    except ValueError:pass
    doc=["# Phil's first extended-thinking wake","","A new Qwen3.8 27B draw from the same hotel-morning prompt used in the original seed-701 shoot. The preceding evening, Phil actually phoned his sister in Pittsburgh. The original film used a different model draw. This branch requested Ollama’s public thinking output.","","## Model-emitted thinking","","~~~text",captured,"~~~","","## Model-emitted action and words","","~~~json",json.dumps(parsed,indent=2,ensure_ascii=False) if parsed else msg["content"],"~~~","","Source event `"+source["sources"][-1]+"`. The raw server response, including the stop reason, decoding settings and exact input, is in [first-wake.json](first-wake.json)."]
    (HERE/"first-wake.md").write_text("\n".join(doc)+"\n")
    print(json.dumps({"chars":len(captured),"stop":ans["done_reason"],"tokens":ans.get("eval_count"),"wall_s":result["wall_s"],"action":parsed and parsed["action"],"words":parsed and parsed["words"]},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
