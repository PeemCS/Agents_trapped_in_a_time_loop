"""Town layout, schedules, and story rules for February 2."""

from collections import deque
from dataclasses import dataclass

PLACES = {
    "inn": {"label": "Cherry Street Inn", "x": -20, "z": 16},
    "main_st": {"label": "Main Street", "x": 0, "z": 10},
    "knob": {"label": "Gobbler’s Knob", "x": -22, "z": -15},
    "diner": {"label": "Tip Top Café", "x": 13, "z": 14},
    "hotel": {"label": "Hotel Ballroom", "x": 18, "z": -5},
    "country_rd": {"label": "County Road", "x": 29, "z": -24},
    "piano_teacher": {"label": "Piano Teacher", "x": -6, "z": -13},
    "alley": {"label": "Snowy Alley", "x": 12, "z": 23},
    "outskirts": {"label": "Outside Town", "x": 37, "z": -32},
}
ROADS = {
    "inn": ("main_st",),
    "main_st": ("inn", "diner", "knob", "piano_teacher", "alley"),
    "knob": ("main_st", "hotel", "country_rd"),
    "diner": ("main_st", "hotel", "piano_teacher", "alley"),
    "hotel": ("diner", "knob", "country_rd", "piano_teacher", "alley"),
    "country_rd": ("knob", "hotel", "outskirts"),
    "piano_teacher": ("main_st", "diner", "hotel"),
    "alley": ("main_st", "diner", "hotel"),
    "outskirts": ("country_rd",),
}
STARTS = {"phil": "inn", "rita": "hotel", "larry": "hotel", "ned": "main_st"}
CAST = {
    "phil": {
        "name": "Phil Connors", "goal": "Cover the ceremony and get out of town.",
        "voice": "Dry, impatient, and unexpectedly funny when he stops performing for the camera.",
    },
    "rita": {
        "name": "Rita Hanson", "goal": "Produce a good local story and see what people actually do.",
        "voice": "Warm, wry, and practical. Curious about the locals and protective of her crew.",
    },
    "larry": {
        "name": "Larry", "goal": "Get usable footage and avoid wasting the crew's time.",
        "voice": "Deadpan. Notices movement, opportunistic B-roll, and the reactions around him.",
    },
    "ned": {
        "name": "Ned Ryerson", "goal": "Make a sale, chat with people, and get to the party.",
        "voice": "Infectiously cheerful and a little too familiar. Earnest when someone needs help.",
    },
}
ANCHORS = {
    0: ("radio", "inn", "The clock flips to 06:00. Morning, Punxsutawney. Buttons up, then out to the Knob."),
    3: ("ned_greeting", "main_st", "Phil Connors! I’d recognize a forecast jacket like that in a blizzard."),
    4: ("ceremony", "knob", "The groundhog sees its shadow. The crew waits for Phil’s weather segment."),
    20: ("snow", "country_rd", "The blizzard closes the road out of town."),
    26: ("party", "hotel", "The ballroom opens for the Groundhog Day party."),
}
APPOINTMENTS = {
    "rita": {4: "knob"},
    "larry": {4: "knob"},
    "ned": {3: "main_st"},
}
REJOIN_TICKS = {
    "rita": (4, 12, 26),
    "larry": (4, 26),
    "ned": (3, 26),
}
SCHEDULES = {
    "rita": {
        0: ("hotel", "reviewing the station’s rundown"),
        2: ("knob", "producing the groundhog segment"),
        8: ("main_st", "talking to the locals for B-roll"),
        12: ("diner", "breaking for coffee"),
        14: ("hotel", "checking in with the station"),
        26: ("hotel", "attending the ballroom party"),
    },
    "larry": {
        0: ("hotel", "checking the camera"),
        2: ("knob", "setting up the camera"),
        8: ("main_st", "getting B-roll"),
        12: ("diner", "breaking for lunch"),
        14: ("hotel", "putting the camera away"),
        26: ("hotel", "catching the ballroom band"),
    },
    "ned": {
        0: ("main_st", "waiting for the morning foot traffic"),
        3: ("main_st", "selling insurance"),
        12: ("diner", "getting a bite to eat"),
        15: ("main_st", "wrapping up his calls"),
        23: ("hotel", "heading to the party"),
    },
}
TURNS = {
    "phil": (0, 1, 3, 4, 6, 10, 11, 12, 14, 16, 18, 20, 24, 26, 30, 32, 33, 35),
    "rita": (3, 4, 11, 12, 18, 24, 26, 30, 33),
    "larry": (3, 4, 11, 12, 18, 24, 26, 30),
    "ned": (3, 4, 11, 12, 18, 24, 26, 30),
}


@dataclass(frozen=True)
class Opportunity:
    location: str
    opens: int
    closes: int
    notice: str
    helped: str
    elapsed: str


OPPORTUNITIES = {
    "kid_tree": Opportunity("main_st", 11, 11, "A child is stranded on an icy tree branch.",
                            "Phil helps the child down before the branch gives way.",
                            "The branch gives way before anyone reaches the child."),
    "flat_tire": Opportunity("country_rd", 14, 15, "A car has a flat and its passengers are standing in the cold.",
                             "Phil helps the stranded passengers get a ride back into town.",
                             "The stranded passengers have to wait for roadside assistance."),
    "choking": Opportunity("hotel", 24, 24, "A guest needs help in the restaurant.",
                           "Phil alerts the staff and stays with the guest while they help.",
                           "The staff notices the guest and calls for help."),
    "old_man_cold": Opportunity("alley", 30, 33, "An older man has nowhere warm to wait out the storm.",
                                "Phil walks with the older man to somewhere warm.",
                                "The relief crew reaches the alley after the ballroom empties."),
}

RITA_FACTS = {
    "drink": ("sweet vermouth", 0, "I’d have sweet vermouth with a twist."),
    "toast": ("world peace", 0, "If we’re making a toast, mine is to world peace."),
    "poetry": ("french poetry", 1, "I used to read nineteenth-century French poetry."),
    "network": ("network news", 1, "I’d like to run a network news show someday."),
    "dad": ("mailman", 2, "My dad was a mailman in Ohio."),
    "snow": ("snowball fights", 2, "I still have a soft spot for snowball fights."),
    "rocky": ("rocky", 2, "I cried at Rocky. That goes no further."),
    "ideal": ("kind to strangers", 2, "I like people who are kind to strangers."),
}


def schedule_at(actor: str, tick: int) -> tuple[str, str] | None:
    schedule = SCHEDULES.get(actor)
    if schedule is None:
        return None
    return schedule[max(slot for slot in schedule if slot <= tick)]


def next_stop(location: str, destination: str) -> str | None:
    if location == destination:
        return None
    seen = {location}
    queue = deque((neighbor, neighbor) for neighbor in ROADS[location])
    while queue:
        first, place = queue.popleft()
        if place == destination:
            return first
        if place in seen:
            continue
        seen.add(place)
        queue.extend((first, neighbor) for neighbor in ROADS[place] if neighbor not in seen)
    return None


def clock(tick: int) -> str:
    minutes = (6 * 60 + 30 * tick) % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
