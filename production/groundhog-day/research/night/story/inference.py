"""OpenAI-compatible chat transport, exact-request cache and a deterministic test double."""
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

FIELDS=("action","words","intention","detail")

def canonical(v):
    return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()

def fingerprint(v):
    return hashlib.sha256(canonical(v)).hexdigest()

def object_schema(actions):
    props={k:{"type":"string"} for k in FIELDS}
    props["action"]["enum"]=actions
    return {"type":"object","properties":props,"required":list(FIELDS),"additionalProperties":False}

def validate(raw, actions):
    stripped=raw.strip()
    if stripped.startswith("```"):
        found=re.fullmatch(r"```(?:json)?\s*(.*?)\s*```",stripped,re.S|re.I)
        if found: stripped=found.group(1)
    obj=json.loads(stripped)
    if not isinstance(obj,dict) or set(obj)!=set(FIELDS):
        raise ValueError("Decision needs exactly action, words, intention and detail.")
    if not all(isinstance(v,str) for v in obj.values()) or obj["action"] not in actions:
        raise ValueError("Invalid action or field type.")
    if any(len(obj[k])>1200 for k in FIELDS):
        raise ValueError("Decision fields must each be under 1201 characters.")
    return obj

class OpenAIChat:
    def __init__(self, url, model, args):
        self.url=url.rstrip("/")+"/chat/completions";self.model=model;self.args=args
        self.key=os.environ.get(args.api_key_env) if args.api_key_env else None

    def respond(self, actor, slot, messages, actions, seed):
        body={"model":self.model,"messages":messages,"temperature":self.args.temperature,"max_tokens":self.args.max_tokens}
        if not self.args.omit_seed: body["seed"]=seed
        if self.args.thinking!="default": body["chat_template_kwargs"]={"enable_thinking":self.args.thinking=="on"}
        if self.args.response_format=="schema":
            body["response_format"]={"type":"json_schema","json_schema":{"name":"town_decision",
                                     "strict":True,"schema":object_schema(actions)}}
        elif self.args.response_format=="object": body["response_format"]={"type":"json_object"}
        headers={"Content-Type":"application/json"}
        if self.key: headers["Authorization"]="Bearer "+self.key
        req=Request(self.url,data=canonical(body),headers=headers)
        start=time.monotonic()
        try:
            with urlopen(req,timeout=self.args.timeout) as response:
                result=json.load(response)
        except HTTPError as exc:
            # Never persist response/URL headers or bearer tokens in output artifacts.
            raise RuntimeError(f"HTTP {exc.code} from the configured chat server") from exc
        c=result["choices"][0]
        raw=c.get("message",{}).get("content")
        meta={"latency_s":round(time.monotonic()-start,4),"usage":result.get("usage",{}),
              "finish_reason":c.get("finish_reason"),"response_model":result.get("model"),
              "system_fingerprint":result.get("system_fingerprint")}
        return raw if isinstance(raw,str) else "", meta

class OllamaChat:
    """Native local/forwarded Ollama. Native options make the thinking and context limits explicit."""
    def __init__(self,url,model,args):
        self.url=url.rstrip("/").removesuffix("/v1")+"/api/chat"
        self.model=model;self.args=args
        self.key=os.environ.get(args.api_key_env) if args.api_key_env else None

    def respond(self, actor, slot, messages, actions, seed):
        options={"temperature":self.args.temperature,"num_predict":self.args.max_tokens,"num_ctx":self.args.num_ctx}
        if not self.args.omit_seed: options["seed"]=seed
        body={"model":self.model,"messages":messages,"stream":False,"options":options}
        if self.args.thinking!="default": body["think"]=self.args.thinking=="on"
        if self.args.response_format=="schema": body["format"]=object_schema(actions)
        elif self.args.response_format=="object": body["format"]="json"
        headers={"Content-Type":"application/json"}
        if self.key: headers["Authorization"]="Bearer "+self.key
        req=Request(self.url,data=canonical(body),headers=headers)
        start=time.monotonic()
        try:
            with urlopen(req,timeout=self.args.timeout) as response: result=json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code} from the configured native Ollama server") from exc
        if not result.get("done"): raise ValueError("Incomplete native Ollama response")
        raw=result.get("message",{}).get("content")
        return raw if isinstance(raw,str) else "", {
            "latency_s":round(time.monotonic()-start,4),"finish_reason":result.get("done_reason"),
            "usage":{"prompt_tokens":result.get("prompt_eval_count"),"completion_tokens":result.get("eval_count")},
            "server_duration_ns":result.get("total_duration"),"response_model":result.get("model")}

class Fixture:
    def respond(self,actor,slot,messages,actions,seed):
        day,tick=slot
        obs=json.loads(messages[1]["content"])
        if actor=="reporter":
            before=["leave_pencil_mark","go_to_depot","take_coach_to_Pittsburgh","call_sister"]
            after=["look_around","go_to_studio","file_forecast","play_piano"]
            pick=(before if day==1 else after)[tick]
        elif actor=="producer":
            pick=["go_to_studio","file_forecast","air_forecast","go_to_square"][tick]
        else:
            pick=["look_around","watch_ceremony","film_cornet_player","listen_to_band"][tick]
        if pick not in actions: pick="look_around"
        obj={"action":pick,"words":"","intention":"","detail":""}
        if actor=="reporter" and tick==0 and day==1: obj["intention"]="Check the coach timetable this morning."
        if actor=="producer" and tick==0: obj["words"]="I'll take the first studio slot."
        return json.dumps(obj),{"latency_s":0,"usage":{},"finish_reason":"stop","response_model":"fixture"}

def decide(backend, actor, slot, turns, actions, seed, key, cache, write_attempt):
    # A cached request is an exact prior valid response in the same root. Rare repairs are attached
    # to the original slot and preserved even if no valid output was obtained in that attempt.
    original=list(turns)
    if key in cache:
        record=cache[key]
        return record["decision"], {"request_id":key,"messages":original,"legal_actions":actions,"sampling_seed":seed,
                                    "attempts":[],"cache_hit":True,"source_slot":record["slot"]}
    attempts=[]
    for repair in range(2):
        raw,meta=backend.respond(actor,slot,turns,actions,seed)
        error=None
        try:
            if meta.get("finish_reason")=="length": raise ValueError("Output truncated.")
            decision=validate(raw,actions)
        except (ValueError,TypeError) as exc:
            error=str(exc)
        a={"messages":turns,"response":raw,"error":error,**meta}
        attempts.append(a)
        write_attempt(key,actor,slot,a,repair)
        if error is None:
            diagnostics={"request_id":key,"messages":original,"legal_actions":actions,"sampling_seed":seed,
                         "attempts":attempts,"cache_hit":False}
            return decision,diagnostics
        turns=original+[{"role":"user","content":"Return exactly one JSON object with the four string fields action, words, intention and detail. Choose a listed action. Keep all four short."}]
    raise ValueError(f"No legal decision after repair for {actor}, slot {slot}. Completed slots remain replayable.")
