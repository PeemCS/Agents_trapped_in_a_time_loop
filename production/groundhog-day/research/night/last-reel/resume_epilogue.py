"""Finish the matching next-morning decisions, preserving both invalid returns."""
import json
import epilogue
from restore_stream import ShortAnswerJournal

if __name__=="__main__":
    epilogue.ObservableOllama=ShortAnswerJournal
    epilogue.main()
    for p in (epilogue.HERE/"epilogues").glob("*/*.json"):
        r=json.loads(p.read_bytes());a=r["attempts"]
        if a and "previous_invalid_attempt" in a[-1]:
            last=a[-1].copy();second=last.pop("previous_invalid_attempt")
            r["attempts"]=a[:-1]+[second,last];epilogue.atomic_json(p,r)
