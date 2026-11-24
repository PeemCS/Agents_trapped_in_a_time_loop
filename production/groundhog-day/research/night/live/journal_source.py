"""Incrementally consume presentation frames; a write without its terminating newline stays pending."""
import json
import time
from journal import encode
from director import Source


class JournalSource(Source):
    def __init__(self,path,pace):
        super().__init__(path,pace)
        self.inode=None
        self.cursor=0
        self.previous="00"*32
        self.read_bytes=0

    def refresh(self):
        try:
            stat=self.path.stat()
            changed_inode=stat.st_ino!=self.inode
            rewound=stat.st_size<self.cursor
            if not changed_inode and not rewound and stat.st_size==self.cursor:
                self.note="" if self.frames else "Waiting for a committed turn"
                return
            with self.path.open("rb") as f:
                # Validate a replacement header before discarding the last good take.
                if changed_inode or rewound:
                    first=f.readline(1024*1024)
                    if not first.endswith(b"\n"):
                        self.note="Waiting for a complete journal header";return
                    kind,header,digest=self.decode(first,"00"*32)
                    if kind!="begin" or not isinstance(header,dict) or "protagonist" not in header:
                        raise ValueError("Invalid journal header")
                    self.epoch+=1;self.started=time.monotonic()
                    self.frames=[];self.header={**header,"status":"partial"};self.previous=digest
                    self.cursor=f.tell();self.inode=stat.st_ino;self.read_bytes+=len(first)
                f.seek(self.cursor)
                self.note=""
                # Bound work per poll; a busy producer never monopolizes the director thread.
                for _ in range(512):
                    line=f.readline(2*1024*1024)
                    if not line:break
                    if not line.endswith(b"\n"):
                        self.note="Waiting for the rest of a committed turn";break
                    kind,data,digest=self.decode(line,self.previous)
                    if self.header["status"]=="complete":raise ValueError("Record after end of take")
                    if kind=="slot":
                        if data["offset"]!=len(self.frames) or not isinstance(data["event"],dict):
                            raise ValueError("Out-of-order journal slot")
                        self.frames.append(data["event"])
                    elif kind=="end" and data["slots"]==len(self.frames):
                        self.header["status"]="complete"
                    else:raise ValueError("Unexpected journal record")
                    self.previous=digest;self.cursor=f.tell();self.read_bytes+=len(line)
        except FileNotFoundError:
            self.note="Source temporarily unavailable" if self.frames else "Waiting for the source file"
        except (KeyError,TypeError,OSError,ValueError) as exc:
            self.note="Holding last committed turn ("+type(exc).__name__+")"

    @staticmethod
    def decode(line,previous):
        obj=json.loads(line)
        if not isinstance(obj,dict) or obj.get("previous")!=previous:raise ValueError("Broken journal chain")
        kind,body=obj["kind"],obj["data"]
        _,expected=encode(kind,body,previous)
        if expected!=obj["checksum"]:raise ValueError("Journal checksum mismatch")
        return kind,body,expected
