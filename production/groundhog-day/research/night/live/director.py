"""Loopback-only director for a local atomic decision log. Never calls a model."""
import argparse
import hashlib
import json
import mimetypes
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE=Path(__file__).resolve().parent
VISUAL=HERE.parent/"visual"
sys.path.insert(0,str(HERE.parent/"story"))
from audit import pack_run

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,separators=(",",":"),sort_keys=True).encode()

class DirectorServer(ThreadingHTTPServer):
    # Several screens may reconnect together after the operator reopens the projector.
    request_queue_size = 32

class Source:
    def __init__(self,path,pace):
        self.path=path
        self.pace=pace
        self.lock=threading.Lock()
        self.started=time.monotonic()
        self.marker=None
        self.epoch=0
        self.frames=[]
        self.hashes=[]
        self.header={}
        self.note="Waiting for the first committed decision"
        self.last_failure=False

    def refresh(self):
        try:
            stat=self.path.stat()
            marker=(stat.st_ino,stat.st_size,stat.st_mtime_ns)
            if marker==self.marker:
                self.note=""
                self.last_failure=False
                return
            row=pack_run(json.loads(self.path.read_bytes()))
            frames=row.pop("events")
            row.pop("source_sha256",None)
            digests=[hashlib.sha256(canonical(e)).digest() for e in frames]
            same_take=all(self.header.get(k)==row.get(k) for k in ("model","seed","memory","cast_condition","source","protagonist"))
            replaced=(not same_take or len(digests)<len(self.hashes) or self.hashes!=digests[:len(self.hashes)])
            if replaced or not self.epoch:
                self.epoch+=1
                self.started=time.monotonic()
            self.hashes,self.frames,self.header,self.marker=digests,frames,row,marker
            self.note=""
            self.last_failure=False
        except FileNotFoundError:
            self.note="Waiting for the source file" if not self.frames else "Source temporarily unavailable"
        except (TypeError,ValueError,KeyError,OSError) as exc:
            # Atomic-writer interruptions cannot replace the last good projection.
            self.last_failure=True
            self.note="Holding last committed frame ("+type(exc).__name__+")"

    def slice(self,epoch,cursor):
        with self.lock:
            self.refresh()
            count=len(self.frames)
            shown=min(count,1+int((time.monotonic()-self.started)/self.pace)) if self.pace else count
            begin=cursor if epoch==self.epoch and 0<=cursor<=shown else 0
            # A late viewer can catch up in bounded increments.
            end=min(begin+128,shown)
            header={**self.header}
            complete=header.get("status")=="complete" and shown==count and end==shown
            if not complete:header["status"]="partial"
            return {"epoch":self.epoch,"from":begin,"next":end,"available":shown,"complete":complete,
                    "kind":"recorded stream" if self.pace else "decision log","notice":self.note,
                    "header":header,"events":self.frames[begin:end]}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        uri=urlparse(self.path)
        if uri.path=="/api/live":
            q=parse_qs(uri.query)
            try: payload=self.server.source.slice(int(q.get("epoch",["-1"])[0]),int(q.get("after",["0"])[0]))
            except ValueError:
                self.send_error(400);return
            self.respond(canonical(payload),"application/json; charset=utf-8")
        elif uri.path=="/":
            self.respond((HERE/"stage.html").read_bytes(),"text/html; charset=utf-8")
        elif uri.path.startswith("/visual/"):
            name=unquote(uri.path[len("/visual/"):])
            if Path(name).name!=name or Path(name).suffix not in {".html",".css",".js",".png",".webp",".ico",".woff2"}:
                self.send_error(404);return
            target=VISUAL/name
            if not target.is_file():
                self.send_error(404);return
            self.respond(target.read_bytes(),mimetypes.guess_type(name)[0] or "application/octet-stream")
        else:self.send_error(404)

    def respond(self,data,kind):
        self.send_response(200)
        self.send_header("Content-Type",kind)
        self.send_header("Content-Length",str(len(data)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        try:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass
    def log_message(self,*args):
        return

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path,help="An already recorded trace or the trajectory the headless runner is writing.")
    p.add_argument("--port",type=int,default=8766)
    p.add_argument("--journal",action="store_true",help="Read an incremental presentation journal with chained SHA-256 records.")
    p.add_argument("--recorded-interval",type=float,default=0,help="Pace a saved trajectory in seconds per slot for stream QA.")
    a=p.parse_args()
    if a.recorded_interval<0:p.error("Interval must be nonnegative.")
    host=DirectorServer(("127.0.0.1",a.port),Handler)
    if a.journal:
        from journal_source import JournalSource
        host.source=JournalSource(a.trace,a.recorded_interval)
    else:
        host.source=Source(a.trace,a.recorded_interval)
    print(f"Director listening at http://127.0.0.1:{host.server_port}/",flush=True)
    host.serve_forever()
if __name__=="__main__":main()
