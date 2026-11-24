"""Preserve invalid format attempts and recover interview scenes after overlong fields."""
import sys
from pathlib import Path
import shoot
from restore_stream import StreamJournal
from inference import validate
from town import atomic_json

class RecoveredBackend(StreamJournal):
    def respond(self,role,slot,messages,actions,seed):
        raw,meta=super().respond(role,slot,messages,actions,seed)
        if len(messages)<=2:return raw,meta
        try:
            if meta["finish_reason"]!="stop":raise ValueError("incomplete repaired output")
            validate(raw,actions)
            return raw,meta
        except (ValueError,TypeError) as error:
            why=str(error)
        last=messages[:2]+[{"role":"assistant","content":raw},{"role":"user","content":"Previous answer exceeded the engine limit or had invalid fields. Pick the physical act. Use at most one sentence under 160 characters in each other string. You may use an empty string."}]
        third,info=super().respond(role,slot,last,actions,seed+1)
        return third,{**info,"previous_invalid_attempt":meta,"previous_error":why}

def main():
    shoot.ObservableOllama=RecoveredBackend
    shoot.main()
    for f in sorted((shoot.HERE/"runs").glob("*/scene.json")):
        r=__import__("json").loads(f.read_bytes());changed=False
        for beat in r["beats"]:
            attempts=beat["attempts"]
            if attempts and "previous_invalid_attempt" in attempts[-1]:
                meta=attempts[-1].copy();second=meta.pop("previous_invalid_attempt")
                beat["attempts"]=attempts[:-1]+[second,meta];changed=True
        if changed:atomic_json(f,r)

if __name__=="__main__":main()
