"""Replay all published results and link each exchange receipt to the actual model wire output."""
import hashlib
import json
from pathlib import Path
from adapter import HERE, SEEDS, VARIANTS, canonical, checksum, make_body, resolve, source, validate

def verify(path):
    case=json.loads(path.read_bytes()); inp=HERE/case["request"]; raw=HERE/case["response"]
    assert inp.read_bytes()==canonical(make_body(case["variant"],case["sampling_seed"]))
    assert checksum(inp)==case["request_sha256"] and checksum(raw)==case["response_sha256"]
    chunks=[]
    for line in raw.read_bytes().splitlines():
        row=json.loads(line)
        if case["reused"]:
            if row["kind"]!="chunk":continue
            row=row["provider"]
        chunks.append(row)
    text="".join(row.get("message",{}).get("content","") for row in chunks)
    thoughts="".join(row.get("message",{}).get("thinking","") for row in chunks)
    assembled=json.loads((HERE/case["assembled_provider_text"]).read_bytes())
    assert text==assembled["content"] and thoughts==assembled["native_thinking"]
    assert chunks[-1].get("done_reason")==case["stop"]
    if case["stop"]!="stop" or case["actual_error"]:return case
    legal=json.loads(inp.read_bytes())["format"]["properties"]["action"]["enum"]
    decision=validate(text,legal)
    assert decision==case["decision"]
    after,events,ledger=resolve(case["variant"],decision,checksum(inp),checksum(raw))
    assert (after,events,ledger)==(case["world_after"],case["actor_events"],case["exchange_log"])
    cast=source()[1]["cast"]
    assert all(events[e["role"]]["decision"]==e["decision"] for e in cast)
    assert case["confirmed_call"]==(bool(ledger) and after["called_sister"])
    assert len(ledger)==int(decision["action"]=="call_sister")
    return case

if __name__=="__main__":
    archive=json.loads((HERE/"comparison.json").read_bytes())
    results=[verify(HERE/f"takes/{v}-{s}/result.json") for v in VARIANTS for s in SEEDS]
    assert len(results)==6 and sum(not c["reused"] for c in results)==5
    assert len(archive["cases"])==len(results) and all(c in archive["cases"] for c in results)
    fresh=[c for c in results if not c["reused"]]
    print(json.dumps({"verified_cases":len(results),"new_calls":len(fresh),"new_input_tokens":sum(c["prompt_tokens"] for c in fresh),"new_output_tokens":sum(c["output_tokens"] for c in fresh),
                      "all_native_thinking":all(c["thinking_chars"]>0 for c in results),
                      "exchange_receipts":[c["sampling_seed"] for c in results if c.get("confirmed_call")]},indent=2))
