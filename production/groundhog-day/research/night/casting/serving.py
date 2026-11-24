"""Compare matched receipt runs on the same accelerator, keeping latency, speed and narrative yield separate."""
import json
import math
import statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
RATES=4.39


def nearest(nums,p):
    return sorted(nums)[min(len(nums)-1,max(0,math.ceil(p*len(nums))-1))]


def main():
    scores=json.loads((HERE/"model-grid.json").read_text())
    groups={}
    for family in ("q4","q27"):
        p=NIGHT/"takes"/family
        times={(r["seed"],r["cast"]):r["wall_s"] for line in (p/"progress.jsonl").read_text().splitlines()
               if (r:=json.loads(line))["memory"]=="receipts" and r["exit"]==0}
        rows=[r for r in scores["takes"] if r["family"]==family and r["memory"]=="receipts"]
        assert len(rows)==len(times)==8
        tagged=json.loads((p/"model.json").read_text());lat=[];duration=[];out=[];input_tokens=[];decodes=[]
        for r in rows:
            take=json.loads((NIGHT/r["path"]).read_text())
            for e in take["events"]:
                for actor in [e,*e["cast"]]:
                    inf=actor["inference"]
                    for attempt in inf["attempts"]:
                        if inf["cache_hit"]:continue
                        latency=attempt.get("latency_s");server=attempt.get("server_duration_ns")
                        if latency is None or not server:continue
                        lat.append(latency);duration.append(server/1e9)
                        out.append(attempt["usage"]["completion_tokens"]);input_tokens.append(attempt["usage"]["prompt_tokens"])
                        decodes.append(out[-1]/(server/1e9))
        total=sum(times.values())
        payoffs=sum(r["returns"] for r in rows);worlds=sum(r["returns"]>0 for r in rows)
        groups[family]={"name":tagged["name"],"digest":tagged["digest"],"parameters":tagged["details"]["parameter_size"],
                        "quantization":tagged["details"]["quantization_level"],"backend_family_tag":tagged["details"]["family"],
                        "runs":len(rows),"matched_seeds":4,"committed_lead_slots":sum(r["slots"] for r in rows),
                        "observed_generation_attempts":len(lat),"reused_decisions":sum(r["cache_reuses"] for r in rows),
                        "provider_input_tokens":sum(input_tokens),"provider_output_tokens":sum(out),
                        "client_request_median_s":round(statistics.median(lat),3),"client_request_p95_s":round(nearest(lat,.95),3),
                        "per_request_server_time_median_s":round(statistics.median(duration),3),
                        "median_client_minus_provider_wall_s":round(statistics.median([a-b for a,b in zip(lat,duration)]),3),
                        "aggregate_output_tokens_per_wall_second":round(sum(out)/total,2),
                        "total_shoot_wall_s":round(total,1),"take_median_s":round(statistics.median(times.values()),2),
                        "take_range_s":[min(times.values()),max(times.values())],
                        "rental_estimate_during_these_8_job_windows_usd":round(total/3600*RATES,3),
                        "confirmed_payoff_worlds":worlds,"confirmed_payoff_events":payoffs}
    output={"scope":"Eight receipt-memory six-day takes per checkpoint; same four seeds and two casts, same rented H100 SXM, Q4_K_M, 3 parallel actor slots and same local-to-SSH transport. Job wall includes cold/loading and program overhead if it occurred in those windows. These slices are part of total rental time and are not extra charges. Output/wall second is useful end-to-end production throughput, not a kernel decoding benchmark. Distinct checkpoint releases and parameter counts move together.",
            "families":groups}
    (HERE/"serving.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(groups,indent=1))

if __name__=="__main__":main()
