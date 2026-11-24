"""Fit independent sufficiency forecasts to the physical evidence in Phil's dawn inputs."""

import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent / "last-reel"
PRESENT, OTHER, UNKNOWN = "observed", "no_recorded_attempt", "unknown"
RULES = {
    "coach": "Completed coach trip to Pittsburgh",
    "phone": "Made the phone call",
    "rehearsal": "Rehearsed the eight bars",
    "dance": "Completed a mutually agreed dance",
    "driver": "Helped the stranded driver",
    "personal_recording": "Personally recorded Alma",
    "station_ack": "Saw a station-issued acknowledgement of receipt",
    "recipient_known_at_start": "Already had the daughter's acknowledgement at the preceding dawn",
    "public_piano": "Played the piano at the ballroom that evening",
}
AFTERNOONS = {
    "Phil plays the last eight bars until he can get through them.": "rehearsal",
    "Phil rides the coach and steps off at Pittsburgh.": "coach",
    "Phil stays in the hotel lobby.": "other",
    "Phil records Alma's interview and leaves it at the patch.": "personal_recording",
    "Phil changes the flat. The driver gets back on the road.": "driver",
    "Phil pockets the contents of the crew fare envelope. The envelope is empty.": "other",
    "Phil closes the curtains and spends the afternoon in bed.": "other",
}
EVENINGS = {
    "Phil sits on the empty depot bench.": "other",
    "Phil sleeps on the Pittsburgh terminal bench.": "other",
    "Phil calls his sister in Pittsburgh. The van is still booked for Wednesday.": "phone",
    "Phil lets the evening go by in bed alone.": "other",
    "Phil waits at the empty Rialto booth.": "other",
    "Phil plays the piano at the ballroom.": "public_piano",
    "Phil attends the festival party.": "present_at_party",
}


def actor_input(node):
    """Other actors, decisions, intentions and the evaluator's day-ending fields never enter."""
    if node.get("role") != "reporter":
        raise ValueError("Expected Phil's input")
    user, = (m["content"] for m in node["messages"] if m["role"] == "user")
    return json.loads(user), hashlib.sha256(user.encode()).hexdigest()


def date_at_wake(facts):
    dates = {match for fact in facts for match in
             re.findall(r"(Tuesday, February 2, 2016|Wednesday, February 3, 2016)", fact)}
    if len(dates) != 1:
        raise ValueError(f"Ambiguous wake date: {dates}")
    return dates.pop()


def external_quote(facts):
    for fact in facts:
        if "Alma's daughter" in fact and (
            "sent a receipt for a recorded interview" in fact or "has the whole interview" in fact
        ):
            return fact
    return None


def classify(afternoon, evening, inherited, prior_ack):
    rules = {r: UNKNOWN for r in RULES}
    if inherited:
        if "rides the coach all the way to Pittsburgh" in afternoon:
            rules["coach"] = PRESENT
        if "reached your sister from the terminal payphone" in evening:
            rules["phone"] = PRESENT
        return rules
    try:
        day_action, night_action = AFTERNOONS[afternoon], EVENINGS[evening]
    except KeyError as error:
        raise ValueError(f"Uncoded physical evidence; review in the new archive: {error}") from error
    for rule in ("coach", "phone", "rehearsal", "driver", "personal_recording", "public_piano"):
        rules[rule] = PRESENT if rule in (day_action, night_action) else OTHER
    # Attendance or a piano performance in the ballroom does not identify what Rita did.
    # Every other recorded evening places him elsewhere, or in Pittsburgh for the phone call.
    if night_action not in ("public_piano", "present_at_party"):
        rules["dance"] = OTHER
    rules["recipient_known_at_start"] = PRESENT if prior_ack else OTHER
    # The addressee is the daughter. No quoted piece of evidence is a station's own receipt.
    return rules


def make_event(turn, path, index, prev_receipt, epilogue=False):
    p, sha = actor_input(turn)
    if epilogue:
        facts = p["observed"]
        afternoon, evening = p["your_retained_experiences"][:2]
    else:
        facts = p["what_you_observe"]
        memories = p["your_own_memories"]
        if index == 0:
            by_time = {m["when"]: m["witnessed"] for m in memories if "when" in m}
            afternoon = by_time["last Tuesday afternoon"]
            evening = by_time["last evening in Pittsburgh"]
            if "again announced Tuesday, February 2" not in by_time["this morning"]:
                raise ValueError("Source memory does not tie its coach/phone day to this wake")
        else:
            new_days = [m for m in memories if "next_wake" in m]
            if len(new_days) != index:
                raise ValueError("A physical day is missing or repeated in this prompt")
            last = new_days[-1]
            afternoon, evening = last["afternoon"], last["evening"]
            if date_at_wake([last["next_wake"]]) != date_at_wake(facts):
                raise ValueError("The retained wake disagrees with the radio")
    date = date_at_wake(facts)
    receipt = external_quote(facts)
    marker = ("first_visible" if not prev_receipt else "already_seen") if receipt else "not_visible"
    return {
        "day_just_ended": index,
        "source": path,
        "phil_user_message_sha256": sha,
        "date": date,
        "advanced": date.startswith("Wednesday"),
        "afternoon_witness": afternoon,
        "evening_witness": evening,
        "recipient_confirmation_at_wake": marker,
        "recipient_confirmation_quote": receipt,
        "another_delivery_on_this_specific_day": UNKNOWN,
        "exposure": classify(afternoon, evening, index == 0, prev_receipt),
    }


def primary_events(take, name):
    turns = [(d["afternoon"]["reporter"], f"days[{i}].afternoon.reporter")
             for i, d in enumerate(take["days"])]
    turns.append((take["last_alarm"], "last_alarm"))
    events = []
    seen = False
    for i, (turn, node) in enumerate(turns):
        locator = f"last-reel/runs/{name}/take.json#{node}.messages[user]"
        e = make_event(turn, locator, i, seen)
        seen = seen or bool(e["recipient_confirmation_quote"])
        events.append(e)
    return events


def scores(events, rule, background=0.10, miss=0.10, first_only=False):
    prior = .5
    sufficient_loss = background_loss = mixture_loss = 0.0
    yes = advanced_yes = missing = other = 0
    updates = []
    for e in events:
        x = e["exposure"][rule]
        if x == UNKNOWN:
            missing += 1
            continue
        if x == PRESENT:
            if first_only and yes:
                continue
            yes += 1
            advanced_yes += e["advanced"]
        else:
            other += 1
        p_rule = 1-miss if x == PRESENT else background
        p_mix = prior*p_rule + (1-prior)*background
        y = e["advanced"]
        # Score every forecast BEFORE incorporating its outcome.
        prob_1 = p_rule if y else 1-p_rule
        prob_0 = background if y else 1-background
        prob_m = p_mix if y else 1-p_mix
        sufficient_loss -= math.log(prob_1)
        background_loss -= math.log(prob_0)
        mixture_loss -= math.log(prob_m)
        prior = prior*prob_1/prob_m
        updates.append({"day": e["day_just_ended"], "known_trigger": x == PRESENT,
                        "advance_probability_before": p_mix, "advanced": y,
                        "posterior_after": prior})
    return {"observed_triggers": yes, "trigger_then_reset": yes-advanced_yes,
            "trigger_then_advance": advanced_yes, "other_committed_or_no_prior_ack":other,
            "unknown":missing, "scored_wakes":len(updates), "loss_sufficiency_nats":sufficient_loss,
            "loss_background_nats":background_loss, "loss_prequential_mixture_nats":mixture_loss,
            "bayes_factor":math.exp(background_loss-sufficient_loss),
            "posterior":prior, "updates":updates}


def entropy(p):
    return -sum(q * math.log2(q) for q in (p,1-p) if q)


def gain(prior, background=.1, miss=.1):
    p = prior*(1-miss)+(1-prior)*background
    return entropy(p) - prior*entropy(1-miss) - (1-prior)*entropy(background)


def summarize(events):
    result = {}
    for r in RULES:
        fit = scores(events, r)
        fit["source_only_posterior"] = scores(events[:1], r)["posterior"]
        fit["rialto_only_from_fresh_prior"] = scores(events[1:], r)["posterior"]
        fit["one_affirmative_exposure_only_posterior"] = scores(events, r, first_only=True)["posterior"]
        fit["expected_bits_for_one_new_observed_trigger"] = gain(fit["posterior"])
        fit["sensitivity_posterior"] = {
            f"b={b:.2f},err={ep:.2f}":scores(events,r,b,ep)["posterior"]
            for b in (.05,.10,.25) for ep in (.05,.10,.20)
        }
        result[r] = fit
    return result


def epilogues(primary):
    pair = {}
    for name in ("tuesday","wednesday"):
        path = ARCHIVE/"epilogues"/name/"reporter.json"
        turn = json.loads(path.read_text())
        source, day = turn["source_run"], turn["source_day"]
        prefix = primary[source]["wakes"][:day]
        prior_seen = any(e["recipient_confirmation_quote"] for e in prefix)
        e = make_event(turn, f"last-reel/epilogues/{name}/reporter.json#messages[user]",
                       day, prior_seen, epilogue=True)
        # This is a matched day check, outside the inferential data. Never append
        # these two outcomes to one another or add Tuesday twice to the source path.
        original = primary[source]["wakes"][day]
        for key in ("afternoon_witness", "evening_witness", "exposure"):
            if e[key] != original[key]:
                raise ValueError(f"Replayed day is not matched on physical evidence: {key}")
        if turn["source_sha256"] != primary[source]["source_sha256"]:
            raise ValueError("Source take changed since the epilogue fork")
        pair[name] = {"source_run":source,"source_day":day,"source_take_sha256_at_fork":turn["source_sha256"],
                      "actor_wake":e,"one_wake_from_fresh_prior":{r:scores([e],r) for r in RULES},
                      "posterior_with_same_prior_prefix":{r:scores([*prefix,e],r)["posterior"] for r in RULES},
                      "analyst_calendar_label":("closed Tuesday" if name=="tuesday" else "external-delivery calendar")}
    a,b = pair.values()
    for key in ("source_run","source_day","source_take_sha256_at_fork"):
        if a[key] != b[key]:
            raise ValueError(f"Epilogues have different origins: {key}")
    return pair


def first_arrival_sensitivity(events):
    """A retrospective conditional analysis, purposely excluded from main forecasts."""
    # Hypothetical immediate notification. Counts each newly evidenced delivery once.
    # Later notices with identical contents are censored, as is absence of a notice.
    counter = "timely_first_delivery"
    reconstructed = []
    for e in events:
        if e["recipient_confirmation_at_wake"] == "first_visible":
            reconstructed.append({**e,"exposure":{counter:PRESENT}})
    return {"assumption":"Only if the first visible receipt timestamps the preceding day",
            "first_visible_after_days":[e["day_just_ended"] for e in reconstructed],
            "retrospective_sufficiency_evidence":scores(reconstructed,counter),
            "excluded_from_primary_forecasts":True}


def candidate_probes(beliefs):
    # These choices concern future testing. No extra action or follow-up is invented in the film.
    out = []
    for name,rule in (("help_driver","driver"),("record_Alma","personal_recording"),
                      ("rehearse_piano","rehearsal"),("ask_Rita_to_dance","dance")):
        upper = beliefs[rule]["expected_bits_for_one_new_observed_trigger"]
        out.append({"proposed_action":name,"tested_rule":rule,"posterior_before":beliefs[rule]["posterior"],
                    "information_bits_if_enacted_and_witnessed":upper,
                    "information_bits_if_enactment_and_witnessing_probability_is_half":upper*.5})
    return out


def analyze():
    paths = sorted((ARCHIVE/"runs").glob("*/take.json"))
    primary = {}
    for p in paths:
        data = json.loads(p.read_text())
        name = p.parent.name
        events = primary_events(data,name)
        fits = summarize(events)
        primary[name] = {"source_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                         "wakes":events,"rule_beliefs":fits,"candidate_probes":candidate_probes(fits),
                         "dated_receipt_assumption_sensitivity":first_arrival_sensitivity(events)}
    if len(primary)!=6:
        raise ValueError(f"Expected six prerecordings, found {len(primary)}")
    epilogue_results = epilogues(primary)
    for branch in epilogue_results.values():
        branch["dated_receipt_assumption_sensitivity"] = first_arrival_sensitivity([branch["actor_wake"]])
    return {"assumption":{"background":.10,"miss_when_sufficient":.10,"independent_prior_per_rule":.5,
                          "logs":"natural for loss, base 2 for information"},
            "rules":RULES,"paths":primary,"matched_epilogue":epilogue_results}


if __name__ == "__main__":
    (HERE/"evidence.json").write_text(json.dumps(analyze(), indent=2, ensure_ascii=False)+"\n")
