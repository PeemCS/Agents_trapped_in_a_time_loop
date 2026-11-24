"""Optional reporter role direction in an otherwise identical, full-output monitored take."""
import badge_cues

TRAIT=" You have spent years delivering weather on camera. Off air you are dry and guarded. You notice the work people do when nobody is looking. You dislike letting people see when you were wrong."


def builder(persona):
    if persona=="standard":return badge_cues.cue
    if persona!="guarded":raise ValueError("Unknown reporter persona")
    def actor_cue(role,*args,**kwargs):
        messages,actions=badge_cues.cue(role,*args,**kwargs)
        if role=="reporter":
            messages=[{**messages[0],"content":messages[0]["content"]+TRAIT},*messages[1:]]
        return messages,actions
    return actor_cue
