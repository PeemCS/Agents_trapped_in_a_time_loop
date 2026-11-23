"""Public appointment notices and route estimates over the town clock."""

from .town import TURNS, clock, next_stop


NOTICE_LOCATIONS = frozenset({"main_st", "piano_teacher"})
LESSON_LOCATION = "piano_teacher"
LESSON_DURATION = 2


def lesson_notice(tick: int) -> dict:
    return {"activity": "piano_lesson", "location": LESSON_LOCATION,
            "opens": tick, "closes": min(35, tick + LESSON_DURATION)}


def notice_text(appointment: dict) -> str:
    return (f"The notice lists open piano lessons at the teacher's studio "
            f"from {clock(appointment['opens'])} to {clock(appointment['closes'])}.")


def _travel_time(location: str, destination: str) -> int:
    hops = 0
    while location != destination:
        step = next_stop(location, destination)
        if step is None:
            return len(TURNS["phil"]) + 1
        location = step
        hops += 1
    return hops


def earliest_lesson(appointment: dict, location: str, tick: int, *, use_turn: bool) -> int | None:
    """Estimate the first reachable lesson using the actor's regular decision turns."""
    opens, closes = appointment["opens"], appointment["closes"]
    if tick > closes:
        return None
    moves = _travel_time(location, appointment["location"])
    first_turn = tick if use_turn else tick + 1
    turns = [stop for stop in TURNS["phil"] if first_turn <= stop <= closes]
    if len(turns) < moves:
        return None
    arrival = turns[moves - 1] if moves else first_turn - 1
    # The opening gives a lesson turn to an actor already in the studio.
    slots = sorted(set(turns) | {opens})
    return next((slot for slot in slots if max(opens, first_turn, arrival + 1) <= slot <= closes), None)


def lesson_plan(appointment: dict, location: str, tick: int) -> dict:
    """Record route and timing consequences without inspecting future world events."""
    now = earliest_lesson(appointment, location, tick, use_turn=True)
    after_wait = earliest_lesson(appointment, location, tick, use_turn=False)
    step = next_stop(location, appointment["location"])
    return {
        "source_event": appointment["event_id"], "basis": appointment["basis"],
        "opens": appointment["opens"], "closes": appointment["closes"], "location": appointment["location"],
        "projected_lesson_if_act_now": now, "projected_lesson_if_wait": after_wait,
        "route_action": f"move:{step}" if step else "wait",
        "priority_due": now is not None and (after_wait is None or appointment["opens"] - tick <= 4),
    }
