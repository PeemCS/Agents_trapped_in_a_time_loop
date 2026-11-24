#!/usr/bin/env python3
"""Materialize the real town ledger in local DuckDB using the official Bruin CLI."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

EDITOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EDITOR))
from edit import read_trace, seed_csv, summary


def add_bulletins(traces, assets):
    expected = set()
    references = []
    for path in traces:
        trace, digest = read_trace(path)
        if trace.get("ending") != "bulletin":
            continue
        for i, e in enumerate(trace["events"]):
            if e["clock"] != "7:00 pm":
                continue
            air = e["world_after"]["bulletin"]
            if not air["source_ids"]:
                raise ValueError("evening missing all source references")
            for ordinal, source_id in enumerate(air["source_ids"]):
                references.append(
                    (digest, e["id"], i, e["day"], air["channel"], air["selected_by"], ordinal, source_id)
                )
                expected.add((digest, e["id"], ordinal, source_id))
    if references:
        for file in (EDITOR / "bruin" / "bulletin-assets").iterdir():
            shutil.copyfile(file, assets / file.name)
        with (assets / "air_refs.csv").open("w", newline="") as stream:
            csv_out = csv.writer(stream)
            csv_out.writerow(
                (
                    "world",
                    "bulletin_id",
                    "air_slot",
                    "air_day",
                    "channel",
                    "selected_by",
                    "ordinal",
                    "source_id",
                )
            )
            csv_out.writerows(references)
    return expected


def run():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("traces", nargs="+", type=Path)
    p.add_argument("--bruin", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    exe = a.bruin.resolve()
    traces = [x.resolve() for x in a.traces]
    env = dict(os.environ, TELEMETRY_OPTOUT="true", INGESTR_DISABLE_TELEMETRY="true")
    results = {}
    with tempfile.TemporaryDirectory(prefix="town-bruin-") as name:
        work = Path(name)
        subprocess.run(["git", "init", "-q"], cwd=work, check=True)
        shutil.copytree(EDITOR / "bruin" / "pipeline", work / "pipeline")
        (work / ".bruin.yml").write_text(
            "default_environment: local\nenvironments:\n  local:\n    connections:\n      duckdb:\n        - name: town-local\n          path: "
            + json.dumps(str(work / "screening.duckdb"))
            + "\n"
        )
        seed_csv(traces, work / "pipeline" / "assets" / "decisions.csv")
        air_expected = add_bulletins(traces, work / "pipeline" / "assets")

        def invoke(args):
            cmd = [str(exe), *args]
            proc = subprocess.run(cmd, cwd=work, text=True, capture_output=True, env=env, timeout=120)
            if proc.returncode:
                raise SystemExit(proc.stdout + proc.stderr)
            return proc.stdout

        out = invoke(["run", "--config-file", ".bruin.yml", "--workers", "1", "pipeline/pipeline.yml"])
        results["run_log"] = out.replace(str(work), "<temporary-project>")

        def query(sql):
            text = invoke(
                ["query", "--config-file", ".bruin.yml", "-c", "town-local", "-o", "json", "-q", sql]
            )
            return json.loads(text)

        results["ledger"] = query(
            "SELECT world, count(*) AS decisions, count(*) FILTER(WHERE cast(is_lead AS BOOLEAN)) AS slots, count(DISTINCT actor) AS actors FROM town.decisions GROUP BY world ORDER BY world"
        )
        results["coach"] = query(
            "SELECT world, arrival_id, arrival_slot, city_id, city_slot, wake_id, wake_slot, ready FROM town.coach_payoffs ORDER BY world, arrival_slot"
        )
        if air_expected:
            results["air_sources"] = query(
                "SELECT world, bulletin_id, ordinal, source_id, source_slot, source_actor, source_action, source_place, channel FROM town.air_sources ORDER BY world, air_slot, ordinal"
            )
            actual = {(r[0], r[1], r[2], r[3]) for r in results["air_sources"]["rows"] if r[4] is not None}
            if actual != air_expected:
                raise ValueError("SQL and original bulletin evidence disagree")
            results["verified_air_source_count"] = len(actual)
        results["input_hashes"] = [hashlib.sha256(t.read_bytes()).hexdigest() for t in traces]
        results["baseline_python_anchors"] = [
            {"world": s["sha256"], "anchors": s["ready_payoffs"]} for s in map(summary, traces)
        ]
        sql_anchors = {(row[0], row[2], row[4], row[6]) for row in results["coach"]["rows"] if row[7]}
        reducer_anchors = {
            (world["world"], a["arrival"], a["hold"], a["wake"])
            for world in results["baseline_python_anchors"]
            for a in world["anchors"]
        }
        if sql_anchors != reducer_anchors:
            raise ValueError(
                f"SQL and ordered-event scanner disagree on the anchors: {sql_anchors ^ reducer_anchors}"
            )
        results["verified_payoff_count"] = len(sql_anchors)
        results["bruin_version"] = invoke(["version"]).splitlines()[0]
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
        print(f"Materialized {len(traces)} source worlds. Query evidence: {a.output}")


if __name__ == "__main__":
    run()
