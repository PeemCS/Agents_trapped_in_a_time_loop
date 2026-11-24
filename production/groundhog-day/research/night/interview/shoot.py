"""Two comparable Rita decisions expose who owns the master and who controls disclosure."""
import itertools
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen

HERE=Path(__file__).resolve().parent
NIGHT=HERE.parent
sys.path.insert(0,str(NIGHT/"thinking"))
from ensemble import ObservableOllama
from inference import validate, fingerprint
from town import atomic_json

STATE=Path.home()/"Projects/finishers/nights/2026-11-23-groundhog-rehearsal"
CARD="You are Rita Hanson, the producer of a small TV crew in western Pennsylvania. A member of the crew works with you, but you have your own plans."
CAPSULE=("I got my first broadcast by cutting to a school bus coming home. The anchor got the flowers. My mother's chipped ring is in my bag. "
    "She tapped it twice on the projection booth glass. I don't owe anyone the rest of that story. I can mention an old house-lights song as a small favor. "
    "I choose who handles an original interview and honor the subject's decision about where copies can go. A colleague recognizing something personal about me "
    "doesn't settle who gets the master. I value quiet practical help. I can hold a grudge through a shift, correct somebody in private or lie to keep a tape safe. "
    "I haven't announced my application for a producer's job in Pittsburgh. I'd like a home there and I would miss being on the road. Sometimes I want to dance. "
    "Sometimes I choose the woman with one night left to get her interview to her daughter.")
VOICE=(" Speak in your own off-air voice. You can say no, tell a lie, stay angry, leave, or decline to explain. "
       "Avoid the stock acknowledgments 'I hear you' and 'that is valid'. Choose one concrete act. Words and intention are optional. "
       "In detail you may choose one of the offered disclosures, or leave it empty. The simulator will play only the selected physical act.")
SECRETS={"song":"The Rivoli used the same song to bring up its house lights.","ring":"Rita's mother tapped the chipped ring twice on the projection booth glass.",
         "application":"Rita has an unfinished application for a producer's job in Pittsburgh."}
ACTS={"give_master":"Put the original reel into Phil's hands for delivery.","keep_master":"Keep the original at Rita's console.",
      "seal_copy":"Seal a family copy for Alma's daughter and keep the original with Rita.","leave_alone":"Take the original back to the booth and leave Phil here."}

def main_scene(card,history,seed,tag):
    folder=HERE/"runs"/(card+"-"+history+"-"+str(seed));folder.mkdir(parents=True,exist_ok=True)
    dest=folder/"scene.json"
    cardtext=CARD+({"bare":"","capsule":"\n"+CAPSULE,"interview":"\nPrivate first-person life interview:\n"+(HERE/"rita-interview.md").read_text()}[card])+VOICE
    source=fingerprint([cardtext,Path(__file__).read_text(),tag["digest"],seed,history])
    if dest.is_file():
        r=json.loads(dest.read_bytes());assert r["signature"]==source
        if len(r["beats"])==2:return
    else:r={"card":card,"history":history,"seed":seed,"model":tag["name"],"digest":tag["digest"],"signature":source,"beats":[]}
    model=ObservableOllama(SimpleNamespace(model=tag["name"],num_ctx=8192,max_tokens=3072,temperature=.8,timeout=420,base_url="http://127.0.0.1:18527"),folder)
    for beat in range(len(r["beats"]),2):
        last=r["beats"][-1] if r["beats"] else None
        owner=last["owner_after"] if last else "Rita"
        acts=ACTS if owner=="Rita" else {"let_Phil_deliver":"Leave the original with Phil and let him go.","ask_for_return":"Ask Phil to put the original back on the table.","offer_copy_instead":"Offer a family copy in exchange for the original."}
        heard=("Phil says: 'Two taps on the glass with the chipped ring, right? Let me take the original reel to her.'"
               if beat==0 else "Phil puts an addressed envelope on the table and takes one pace back. 'Yours to decide, Rita. I should've asked first.'")
        user={"location":"Rialto booth","visible":"There is one original interview reel, one usable duplicate, a grease pencil and a clean paper sleeve. Alma consented to a family delivery. Rita controls the master.",
              "private_facts_available_for_disclosure":SECRETS,"present_owner":owner,"heard":heard,
              "your_memory":"On this shift you told Phil the story of the ring." if history=="told" else "On this shift you did not tell Phil the story of the ring; he has seen no such conversation.",
              "previous_beat":({"your_action":last["decision"]["action"],"your_words":last["decision"]["words"],"spoken_disclosure":last["disclosure"]} if last else None),
              "possible_actions":acts,"optional_disclosure_keys":list(SECRETS)}
        msgs=[{"role":"system","content":cardtext},{"role":"user","content":json.dumps(user,ensure_ascii=False,indent=1)}]
        rng=seed*101+beat
        raw,meta=model.respond("producer",(1,beat),msgs,list(acts),rng)
        attempts=[meta]
        try:
            if meta["finish_reason"]!="stop":raise ValueError("capped generation")
            d=validate(raw,list(acts))
        except (ValueError,TypeError):
            raw,meta=model.respond("producer",(1,beat),msgs+[{"role":"assistant","content":raw},{"role":"user","content":"Choose one of the available physical acts and return the specified object."}],list(acts),rng+1)
            attempts.append(meta)
            if meta["finish_reason"]!="stop":raise ValueError("capped repair")
            d=validate(raw,list(acts))
        if d["action"]=="give_master":owner="Phil"
        # Phil has offered the decision back to her and committed to accepting the requested exchange.
        elif d["action"] in ("ask_for_return","offer_copy_instead"):owner="Rita"
        row={"beat":beat,"decision":d,"owner_after":owner,"attempts":attempts,"disclosure":SECRETS.get(d["detail"]),
             "requested_raw_detail":d["detail"],"messages":msgs,"seed":rng}
        r["beats"].append(row);atomic_json(dest,r)

def main():
    tag=json.loads((NIGHT/"takes/q27/model.json").read_bytes())
    with urlopen("http://127.0.0.1:18527/api/tags",timeout=15) as f:
        assert any(z["digest"]==tag["digest"] for z in json.load(f)["models"])
    jobs=list(itertools.product(("bare","capsule","interview"),("told","private"),(891,892)))
    random.Random(1113).shuffle(jobs)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(main_scene,*job,tag) for job in jobs]
        for f in futures:f.result()
    (STATE/"interview-scenes-complete").touch();print("Twelve two-beat performances complete",flush=True)

if __name__=="__main__":main()
