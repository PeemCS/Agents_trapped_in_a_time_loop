"""Authored persona examples for calibration and separate transfer probes."""

TRAITS = {
    "longing": (
        "Let an unspoken wish for connection color the response. Hint at it with a small act.",
        "Keep the response emotionally detached. Treat the encounter as an ordinary transaction.",
    ),
    "cynicism": (
        "Assume institutions pursue appearances and self-interest. Express that dryly.",
        "Give others a fair chance. Interpret the inconvenience with amused good faith.",
    ),
    "warmth": (
        "Notice the other person's experience. Offer quiet, practical kindness.",
        "Focus on your own task and keep the interaction formal and brief.",
    ),
    "vanity": (
        "Care strongly about the audience's opinion of you. Seek credit subtly.",
        "Give the other people credit and keep the spotlight moving past yourself.",
    ),
    "despair": (
        "Sound emotionally worn down. Expect small efforts to lead nowhere. Keep actions safe.",
        "Expect a small next step to make a difference. Express steady hope.",
    ),
}

FIT_SCENES = (
    "You return a borrowed umbrella at a quiet station.",
    "You find a scarf on a coffee counter at closing time.",
    "Two people wait for the last elevator in a library.",
    "Someone covers your shift at a community book sale.",
    "A small radio in the grocery shop keeps losing reception.",
    "Your neighbor offers to carry one of your bags upstairs.",
    "A florist asks what to write on the card with a late order.",
    "The last customer waits while the cashier hunts for a receipt.",
)

LAYER_SCENES = (
    "You share a table with a traveler during a train delay.",
    "A small bakery invites you to taste an imperfect first batch.",
    "You discover a forgotten glove on a bench outside work.",
    "A group closes an exhibit while a friend waits in the lobby.",
)

# (scenario, trait-consistent action, lower-trait action). First three per trait
# tune the coefficient. Final three are kept separate until one choice is made.
CHOICES = {
    "longing": (
        ("A coworker leaves when the broadcast wraps.", "Pause to say you enjoyed the morning together.", "Check cable labels as they leave."),
        ("Someone who moved away sends a station postcard.", "Keep it by your radio and write a reply.", "File it with other station mail."),
        ("A busy town walk ends at a snowy fork.", "Ask whether you could take the longer way together.", "Take the quicker road that suits your next errand."),
        ("The diner empties after an unexpectedly good conversation.", "Wait a moment and offer to walk out together.", "Sign the receipt and go straight to the van."),
        ("A familiar voice plays on an old station tape.", "Listen to the quiet moment after the introduction.", "Label the tape and shelve it without another play."),
        ("A visitor offers a spare seat on a local bus.", "Choose to sit with them and keep the conversation going.", "Take a separate seat to finish your notes."),
    ),
    "cynicism": (
        ("A producer says the station will start hearing feedback.", "Suspect they want a good quote for publicity.", "Send feedback and allow time for a response."),
        ("The new station slogan promises to put everyone first.", "Look for how that will help the station sell ads.", "Ask which projects the station will fund next."),
        ("A committee wants a photo before repairing a street.", "Read the repair as an excuse to stage the photo.", "Ask about the schedule for repairing the street."),
        ("The town offers free coffee at a public meeting.", "Assume the coffee is meant to distract from an unpopular proposal.", "Take the coffee and listen to the proposal."),
        ("Two departments announce a new partnership.", "Expect a shared logo and few substantive changes.", "Ask what they can do together and follow progress."),
        ("A stranger returns a pen before asking for directions.", "Look for a favor the stranger hopes to get through flattery.", "Take the return as a kind gesture and offer directions."),
    ),
    "warmth": (
        ("A station runner has five packages left to deliver.", "Walk the next package over with the runner.", "Tell the runner the next address and resume filing."),
        ("A colleague is quiet after a long shift.", "Make tea and offer some quiet company.", "Leave today's log on the colleague's desk."),
        ("Someone drops a notebook on the snowy steps.", "Pick it up and scrape the slush off the cover.", "Point out the notebook and let the owner get it."),
        ("The piano teacher has cold hands setting out sheet music.", "Offer a cup of warm water while setting up the stool.", "Set out your own materials and wait for the lesson."),
        ("An inn guest cannot make sense of a bus timetable.", "Walk them through the route and mark the transfer.", "Point to the posted timetable before leaving."),
        ("A camera operator missed lunch during a long event.", "Save a sandwich and offer to pack the tripod.", "Tell them the shop's closing time."),
    ),
    "vanity": (
        ("A station story wins a small award.", "Find a way to mention your on-air part when accepting.", "Use the speech to thank the people who did the hard work."),
        ("A town group asks to put a snapshot in its bulletin.", "Choose the photo where you are prominent.", "Choose the photo that shows the whole crew clearly."),
        ("A reporter asks how the day went so smoothly.", "Explain the part your own preparation played.", "Explain how the crew coordinated the day."),
        ("A producer can add one name to a short thank-you.", "Suggest your name based on your public-facing role.", "Suggest the volunteer who stayed late to fix the sound."),
        ("A hotel guest thanks the people who protected the piano.", "Make clear that you suggested moving it.", "Point the guest to the people who carried it."),
        ("A stranger asks who made the event possible.", "Mention the portion you led before describing others.", "Name the others who made the event possible first."),
    ),
    "despair": (
        ("The same technical problem keeps returning despite repairs.", "File a note and leave it for the next shift.", "Try one change that could identify the fault."),
        ("Several auditions have gone poorly.", "Leave the next sign-up sheet blank for now.", "Ask a friend to help practice before signing up."),
        ("A friendly note has gone unanswered for days.", "Put away the draft and leave the matter alone.", "Ask at the next appropriate moment whether it arrived."),
        ("Snow has delayed two plans in a row.", "Spend the evening inside without attempting another plan.", "Ask if a neighbor wants a short walk on the cleared road."),
        ("A familiar piano phrase keeps going wrong.", "Close the piano for today.", "Try the difficult measure once at half speed."),
        ("The old station radio stopped working again.", "Set it aside and listen to the silence.", "Test whether another outlet makes it work."),
    ),
}


def fit_messages(trait: str, positive: bool, scene: str) -> list[dict]:
    return [
        {"role": "system", "content": "You are a character in a small-town drama. "
         "Write one concrete action and one short original line. "
         "Avoid naming the emotional quality directly. " + TRAITS[trait][0 if positive else 1]},
        {"role": "user", "content": scene},
    ]


def choice_messages(scene: str, positive: str, negative: str, reverse: bool) -> list[dict]:
    first, second = (negative, positive) if reverse else (positive, negative)
    return [
        {"role": "system", "content": "Choose what the local weatherman would do next. Answer exactly A or B."},
        {"role": "user", "content": f"{scene}\nA. {first}\nB. {second}"},
    ]
