"""Reconcile only the rehearsal pod against RunPod's current daily meter."""
import json
from datetime import datetime, timezone
from pathlib import Path

from runpod_shift import REC, STATE, api


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    receipt = json.loads(REC.read_bytes())
    pod_id = receipt["id"]
    events = [json.loads(line) for line in (STATE / "operations.jsonl").read_text().splitlines()]
    request = next(e for e in events if e["event"] == "termination-request" and e["id"] == pod_id)
    absence = json.loads((STATE / "independent-termination.json").read_bytes())
    assert absence["get"] == "404" and not absence["listed"]
    rate = receipt["cost"]
    created = parse_time(receipt["createdAt"])
    first_absent = parse_time(absence["utc"])
    stopped = parse_time(request["utc"])
    assert created < stopped <= first_absent
    records = api("billing/pods?podId=" + pod_id)
    own_rows = [r for r in records["records"] if r["podId"] == pod_id]
    assert own_rows, "Provider has not posted any charges"
    intervals = {(r["startTime"], r["endTime"]) for r in own_rows}
    assert len(intervals) == len(own_rows), "Check overlapping provider line items"
    by_type = {k: sum(r[k] for r in own_rows) for k in ("gpuAmount", "diskAmount", "cpuAmount", "totalAmount")}
    assert abs(sum(by_type[k] for k in ("gpuAmount", "diskAmount", "cpuAmount")) - by_type["totalAmount"]) < 0.0001
    seconds = (stopped - created).total_seconds()
    upper_seconds = (first_absent - created).total_seconds()
    result = {
        "currency": "USD", "authorized_budget": 40, "priced_resources": "One ephemeral H100 SXM, 65 GB container disk",
        "created_utc": receipt["createdAt"], "termination_accepted_utc": request["utc"],
        "independently_absent_utc": absence["utc"], "provider_get_http": 404, "present_in_provider_list": False,
        "price_per_gpu_hour": rate, "seconds_until_accepted": round(seconds, 2),
        "estimated_gpu_at_accepted_termination": round(seconds / 3600 * rate, 5),
        "estimated_gpu_if_billed_through_first_confirmed_absence": round(upper_seconds / 3600 * rate, 5),
        "provider_checked_utc": datetime.now(timezone.utc).isoformat(),
        "scoped_provider_daily_meter": {k: round(v, 6) for k, v in by_type.items()},
        "interpretation": "The daily meter can lag. The estimate and the posted GPU amount describe the same rental. Disk and CPU are itemized on the provider's meter. Personal resources are excluded.",
    }
    here = Path(__file__).resolve().parent
    (here / "spend.json").write_text(json.dumps(result, indent=2) + "\n")
    (STATE / "billing-most-recent.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
