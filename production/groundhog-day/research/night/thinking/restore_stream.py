"""Resume exact completed native requests without repeating an inference call."""
import hashlib
import json
from ensemble import ObservableOllama
from inference import canonical

def digest(data):
    return hashlib.sha256(data).hexdigest()

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
                  "stream_path":str(p.relative_to(folder)),"stream_sha256":digest(p.read_bytes()),"provider_chunk_count":chunks}
            self.saved[key]=("".join(content),info)

    @staticmethod
    def key(role,slot,messages,actions,seed):return digest(canonical([role,list(slot),messages,actions,seed]))

    def respond(self,role,slot,messages,actions,seed):
        k=self.key(role,slot,messages,actions,seed)
        if k not in self.saved:self.saved[k]=super().respond(role,slot,messages,actions,seed)
        return self.saved[k]


class ShortAnswerJournal(StreamJournal):
    """Retain a returned second attempt, and request shorter fields when that attempt fails."""
    def respond(self,role,slot,messages,actions,seed):
        from inference import validate
        raw,meta=super().respond(role,slot,messages,actions,seed)
        if len(messages)<=2:return raw,meta
        try:
            if meta["finish_reason"]!="stop":raise ValueError("incomplete repaired output")
            validate(raw,actions)
            return raw,meta
        except (ValueError,TypeError) as error:
            why=str(error)
        last=messages[:2]+[{"role":"assistant","content":raw},{"role":"user","content":"Previous response exceeded a field limit or had invalid fields. Pick the physical act. Use at most one sentence under 160 characters in each remaining string. Empty strings are valid."}]
        third,info=super().respond(role,slot,last,actions,seed+1)
        return third,{**info,"previous_invalid_attempt":meta,"previous_error":why}
