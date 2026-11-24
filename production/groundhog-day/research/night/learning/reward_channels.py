"""How much immediate reward can Phil actually control in the sampled towns?"""
import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from functools import partial
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"story"))
from world import menu, resolve


def binary_entropy(p):
    if not 0 < p < 1:
        return 0.0
    return -p*math.log2(p) - (1-p)*math.log2(1-p)


def first_acquisition(key, before, after):
    return int(not before[key] and after[key])


def spent_battery(before, after):
    return int(after["camera_battery"] < before["camera_battery"])


def left_town(before, after):
    return int(before["positions"]["reporter"] != "Pittsburgh" and after["positions"]["reporter"] == "Pittsburgh")


REWARDS = {
    "new_band_recording":partial(first_acquisition,"band_recorded"),
    "new_filed_forecast":partial(first_acquisition,"weather_tape"),
    "sister_confirmed":partial(first_acquisition,"called_sister"),
    "coach_departure":left_town,
    "camera_battery_spent_by_larry":spent_battery,
}


def inspect(take):
    names = take["cast_names"]
    output = defaultdict(list)
    forks = 0
    for i, event in enumerate(take["events"]):
        before = event["world_before"]
        actual_after = event["world_after"]
        actions = menu("reporter", before, i%4, names)
        values = defaultdict(list)
        actual = event["decision"]["action"]
        other = {e["role"]:e["decision"] for e in event["cast"]}
        assert actual in actions
        for action in actions:
            decisions = {**other,"reporter":{**event["decision"],"action":action,"words":"","detail":"","intention":""}}
            after, _ = resolve(take["seed"],event["day"],i%4,before,decisions,names)
            for name,f in REWARDS.items():
                reward = f(before,after)
                values[name].append(reward)
                if action == actual:assert reward == f(before,actual_after)
            forks += 1
        for name,r in values.items():
            observed = REWARDS[name](before,actual_after)
            output[name].append((observed,mean(r),min(r)!=max(r),r[actions.index("spend_time_here")]))
    return forks, output


def summarize(rows):
    observed, chance, changes, stay = zip(*rows)
    controllable = sum(changes)
    # The state includes the realized concurrent choices of both other actors.
    cmi = mean(binary_entropy(p) for p in chance)
    observed_success_with_credit = sum(int(bool(o) and not s) for o,s in zip(observed,stay))
    return {"slots":len(rows),"observed_reward_positive":sum(observed),
            "observed_actor_marginal_reward_entropy_bits":round(binary_entropy(mean(observed)),5),
            "uniform_action_marginal_reward_entropy_bits":round(binary_entropy(mean(chance)),5),
            "uniform_action_mean_reward":round(mean(chance),5),
            "states_where_the_reporter_can_change_the_immediate_reward":controllable,
            "states_where_a_passive_reporter_already_gets_positive_reward":sum(stay),
            "observed_success_attributable_relative_to_staying":observed_success_with_credit,
            "uniform_action_conditional_mutual_information_bits":round(cmi,5)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("families",nargs="+",type=Path)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    all_rows=defaultdict(list);by_fam={};sources=[];total_forks=0
    for family in args.families:
        group=defaultdict(list);group_forks=0
        for path in sorted(family.glob("*/seed-*.json")):
            raw=path.read_bytes();take=json.loads(raw)
            if take["status"]!="complete":continue
            n,rows=inspect(take)
            for k,r in rows.items():
                group[k].extend(r);all_rows[k].extend(r)
            group_forks+=n
            sources.append({"model":take["model"],"condition":path.parent.name,"seed":take["seed"],
                            "sha256":hashlib.sha256(raw).hexdigest()})
        by_fam[family.name]={"forks":group_forks,"channels":{k:summarize(r) for k,r in group.items()}}
        total_forks+=group_forks
    assert all_rows, "No complete takes available"
    combined={k:summarize(r) for k,r in all_rows.items()}
    assert combined["camera_battery_spent_by_larry"]["states_where_the_reporter_can_change_the_immediate_reward"]==0
    assert combined["coach_departure"]["states_where_the_reporter_can_change_the_immediate_reward"]>0
    output={"scope":"One simultaneous decision only. Hold the two other performed actions and conflict order fixed. Equally weight each visited slot; draw a uniform legal reporter action within it. Multiple seeds and recurrences share starting worlds.",
            "negative_control":"Only the camera operator can spend the battery. A positive marginal entropy can coexist with zero conditional action signal.",
            "limits":"Roles' public job goals are engineering probes. None of these events proves kindness, romance or consent. This calculation gives no actor a reward, changes no canonical take and does not estimate the long-horizon return.",
            "forks":total_forks,"sources":sources,"families":by_fam,"combined":combined}
    args.out.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({"takes":len(sources),"forks":total_forks,"channels":combined},indent=2))


if __name__=="__main__":
    main()
