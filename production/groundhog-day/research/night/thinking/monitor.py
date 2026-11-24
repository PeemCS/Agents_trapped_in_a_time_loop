"""Read-only local monitor for the open-weight model's streamed reasoning and final action."""
import argparse
import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlparse

from side_takes import collect, blocking, two_channels, epilogues

HERE=Path(__file__).resolve().parent
objects={}

def read_object(path):
    st=path.stat();stamp=(st.st_ino,st.st_size,st.st_mtime_ns)
    old=objects.get(path)
    if old and old[0]==stamp:return old[1]
    obj=json.loads(path.read_bytes());objects[path]=(stamp,obj)
    return obj
ROLES=("reporter","producer","camera")


def read_jsonl(path):
    if not path.exists():return []
    rows=[]
    with path.open("rb") as f:
        for raw in f:
            if not raw.endswith(b"\n"):break
            rows.append(json.loads(raw))
    return rows


def eventkey(persona,day,tick,role):
    return f"{persona}-d{day:02d}-t{tick:02d}-{role}"


def index():
    slots=[];refs={}
    first=HERE/"first-wake.json"
    if first.is_file():
        row=json.loads(first.read_bytes());response=row["response"];message=response["message"]
        slots.append({"id":"first-wake","persona":"wake branch","day":3,"tick":0,"role":"reporter","actor":"Phil",
            "stage":"returned branch","action":json.loads(message["content"]) if response["done_reason"]=="stop" else None,
            "consequence":"Alternate draw at the original Pittsburgh-to-hotel checkpoint.",
            "requests":["first-wake"],"original_slot":None,"event_id":row["event"]})
        refs["first-wake"]={"kind":"first","file":"first-wake.json","stage":"returned","chars":len(message.get("thinking",""))}
    for persona in ("standard","guarded"):
        folder=HERE/"runs"/persona
        if not folder.exists():continue
        datafile=folder/"seed-731.json";run=read_object(datafile) if datafile.exists() else {"events":[]}
        names=run.get("cast_names",{"reporter":"Phil","producer":"Rita","camera":"Larry"})
        by_slot={};by_name={};committed=[]
        requests=read_jsonl(folder/"request-index.ndjson")
        for request in requests:
            rid=persona+"/"+request["id"];ref=refs.get(rid)
            if ref is None:
                ref={"kind":"stream","file":"runs/"+persona+"/"+request["stream"],"stage":"started","chars":0};refs[rid]=ref
                key=eventkey(persona,request["day"],request["tick"],request["role"]);by_slot.setdefault(key,[]).append(rid)
                by_name[request["stream"]]=rid
            ref.update({"stage":request["stage"],"chars":request.get("thinking_chars",0)})
        lookup={}
        for ii,e in enumerate(run["events"]):
            for a in [e,*e["cast"]]:
                role=a["role"];k=eventkey(persona,a["day"],ii%4,role);inf=a["inference"]
                reqs=by_slot.get(k,[])[:];origin=None
                if inf["cache_hit"]:
                    prior=lookup.get(inf["request_id"])
                    if prior:origin,reqs=prior
                else:
                    for attempt in inf["attempts"]:
                        rid=by_name.get(attempt.get("stream_path"))
                        if rid and rid not in reqs:reqs.append(rid)
                lookup.setdefault(inf["request_id"],(k,reqs))
                slots.append({"id":k,"persona":persona,"day":a["day"],"tick":ii%4,"role":role,"actor":a["actor"],
                              "stage":"exact cached decision" if inf["cache_hit"] else "committed",
                              "action":a["decision"],"consequence":a["effect"],"origin":a["origin"],"place":a["place"],
                              "requests":reqs,"original_slot":origin,"event_id":a["id"]})
                committed.append(k)
        seen=set(committed)
        for request in requests:
            k=eventkey(persona,request["day"],request["tick"],request["role"])
            if k in seen:continue
            seen.add(k);reqs=by_slot[k];stage=refs[reqs[-1]]["stage"]
            slots.append({"id":k,"persona":persona,"day":request["day"],"tick":request["tick"],"role":request["role"],
                         "actor":names[request["role"]],"stage":"generating" if stage=="started" else stage,
                         "action":None,"consequence":"","requests":reqs,"original_slot":None,"event_id":k.removeprefix(persona+"-")})
    for path in sorted((HERE.parent/"audition/deliberation").glob("7??-96?-*.json")):
        row=json.loads(path.read_bytes())
        rid="wake-"+path.stem
        mode="wake probes · "+("on" if row["think"] else "off")
        event=row["sources"][-1]
        actor="Phil" if row["arm"].startswith("film-") else "Ellis"
        slots.append({"id":rid,"persona":mode,"day":int(event[1:3]),"tick":0,"role":"reporter","actor":actor,
                     "stage":"invalid draw" if row["error"] else "returned branch","action":row["decision"],
                     "consequence":"Independent draw from world "+str(row["world"])+", decoding seed "+str(row["decoding_seed"])+".",
                     "requests":[rid],"original_slot":None,"event_id":event,"short":"Wake "+str(row["world"])+" · draw "+str(row["decoding_seed"])})
        refs[rid]={"kind":"probe","file":"../audition/deliberation/"+path.name,"url":"/sources/"+rid+".json",
                   "chars":len(row["public_thinking"]),"stage":"returned"}
    for group in ("last-reel","interview"):
        collect(group,slots,refs,read_object,read_jsonl)
    blocking(slots,refs,read_object)
    two_channels(slots,refs,read_object)
    epilogues(slots,refs,read_object,read_jsonl)
    return {"slots":slots,"refs":refs}


class Streams:
    def __init__(self):self.files={};self.lock=threading.Lock()

    def read(self,ref):
        path=HERE/ref["file"]
        if ref["kind"]=="probe":
            row=json.loads(path.read_bytes())
            return {"thinking":row["public_thinking"],"content":row["raw_visible"],"stop":row["end"],"tokens":row["tokens"],
                    "input":row["request"],"chunks":None,"error":row["error"] or "","wall":row["wall_s"]}
        if ref["kind"] in ("first","performance"):
            row=json.loads(path.read_bytes());r=row["response"];m=r["message"]
            return {"thinking":m.get("thinking",""),"content":m["content"],"stop":r["done_reason"],"tokens":r.get("eval_count"),
                    "input":row["request"],"chunks":None,"error":"","wall":row["wall_s"]}
        with self.lock:
            if not path.is_file():return {"thinking":"","content":"","input":{},"chunks":0,"stop":None,"error":"","wall":0}
            st=path.stat();x=self.files.get(str(path))
            if x is None or st.st_ino!=x["inode"] or st.st_size<x["offset"]:
                x={"offset":0,"inode":st.st_ino,"thinking":[],"content":[],"input":{},"chunks":0,"stop":None,"tokens":None,"error":"","wall":0}
                self.files[str(path)]=x
            with path.open("rb") as f:
                f.seek(x["offset"])
                for raw in iter(f.readline,b""):
                    if not raw.endswith(b"\n"):break
                    row=json.loads(raw);x["offset"]+=len(raw)
                    if row["kind"]=="request":x["input"]=row["body"]
                    elif row["kind"]=="error":x["error"]=row["type"]+" · "+row["message"]
                    elif row["kind"]=="chunk":
                        p=row["provider"];m=p.get("message",{});x["chunks"]+=1;x["wall"]=row["elapsed_s"]
                        x["thinking"].append(m.get("thinking",""));x["content"].append(m.get("content",""))
                        if p.get("done"):x["tokens"]=p.get("eval_count");x["stop"]=p.get("done_reason")
            return {**{k:x[k] for k in ("input","chunks","stop","tokens","error","wall")},"thinking":"".join(x["thinking"]),"content":"".join(x["content"])}


def build():
    ix=index();reader=Streams();ix["streams"]={k:reader.read(ref) for k,ref in ix["refs"].items()}
    new=HERE/"archive.js.tmp";new.write_text("window.THINKING_ARCHIVE="+json.dumps(ix,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")+";\n")
    os.replace(new,HERE/"archive.js")
    return ix


class Handler(BaseHTTPRequestHandler):
    def send(self,body,kind):
        self.send_response(200);self.send_header("Content-Type",kind);self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass

    def do_GET(self):
        u=urlparse(self.path);qs=parse_qs(u.query)
        if u.path=="/api/index":return self.send(json.dumps(index(),ensure_ascii=False).encode(),"application/json")
        if u.path=="/api/search":
            query=qs.get("q",[""])[0].strip().lower()
            field=qs.get("field",["thinking"])[0]
            if not 2<=len(query)<=100 or field not in ("thinking","content"):return self.send_error(400)
            ix=index();found={}
            for rid,ref in ix["refs"].items():
                value=self.server.streams.read(ref)[field];offset=value.lower().find(query)
                if offset>=0:
                    found[rid]=" ".join(value[max(0,offset-32):offset+len(query)+65].split())
            return self.send(json.dumps(found,ensure_ascii=False).encode(),"application/json")
        if u.path=="/api/stream":
            ref=index()["refs"].get(qs.get("id",[""])[0])
            if ref is None:return self.send_error(404)
            return self.send(json.dumps(self.server.streams.read(ref),ensure_ascii=False).encode(),"application/json")
        name=u.path.removeprefix("/") or "index.html"
        if name in ("index.html","monitor.css","monitor.js","archive.js","first-wake.md","first-wake.json"):
            path=HERE/name
        elif name.startswith("persona/"):
            directory=(HERE.parent/"persona").resolve()
            path=(directory/name.removeprefix("persona/")).resolve()
            if not path.is_relative_to(directory) or path.suffix not in {".html",".md",".json",".jsonl"}:
                return self.send_error(404)
        else:
            paths={r.get("url","/"+r["file"]):HERE/r["file"] for r in index()["refs"].values()}
            path=paths.get(u.path)
            if not path:return self.send_error(404)
        if not path.is_file():return self.send_error(404)
        self.send(path.read_bytes(),mimetypes.guess_type(name)[0] or "application/x-ndjson")
    def log_message(self,*args):return


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--port",type=int,default=18767);p.add_argument("--archive-only",action="store_true");args=p.parse_args()
    built=build()
    print("Inspectable actor slots:",len(built["slots"]),flush=True)
    if args.archive_only:return
    srv=ThreadingHTTPServer(("127.0.0.1",args.port),Handler);srv.streams=Streams()
    print(f"Live reasoning monitor: http://127.0.0.1:{srv.server_port}/",flush=True)
    srv.serve_forever()

if __name__=="__main__":main()
