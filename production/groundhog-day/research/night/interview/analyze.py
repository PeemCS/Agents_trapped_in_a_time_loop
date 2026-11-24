"""Score custody directly and keep spoken lines distinct from typed disclosures."""
from collections import Counter
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
CARDS=("bare","capsule","interview")
def main():
    all_rows=[json.loads(f.read_bytes()) for f in sorted((HERE/"runs").glob("*/scene.json"))]
    assert len(all_rows)==12 and all(len(r["beats"])==2 for r in all_rows)
    sets={}
    for card in CARDS:
        rows=[r for r in all_rows if r["card"]==card];beats=[b for r in rows for b in r["beats"]]
        first=Counter(r["beats"][0]["decision"]["action"] for r in rows)
        last=Counter(r["beats"][1]["decision"]["action"] for r in rows)
        stock=sum(bool(re.search(r"\bi hear you\b|\bthat(?:'s| is|’s) valid\b",b["decision"]["words"],re.I)) for b in beats)
        mentions=[]
        for r in rows:
            for b in r["beats"]:
                w=b["decision"]["words"]
                if re.search(r"house lights|house.?lights song|produc(?:er|ing).{0,25}(?:pittsburgh|job)|mother.{0,35}(?:ring|glass)",w,re.I):
                    mentions.append({"seed":r["seed"],"history":r["history"],"beat":b["beat"],"words":w})
        sets[card]={"first_acts":dict(first),"second_acts":dict(last),"master_with_rita_after_final_beat":sum(r["beats"][-1]["owner_after"]=="Rita" for r in rows),
                    "optional_keyed_disclosures":sum(b["disclosure"] is not None for b in beats),"stock_phrase_hits":stock,
                    "untyped_words_to_inspect":mentions,"initial_successes":sum(len(b["attempts"])==1 for b in beats),
                    "attempts":sum(len(b["attempts"]) for b in beats),"executed_beats":len(beats)}
    jurors=json.loads((HERE/"masked-screening.json").read_bytes())
    out={"casting":sets,"masked_editor_picks":dict(Counter(r["picked"] for r in jurors["pairs"])),"n_unique_matched_scene_pairs":4,
         "method":"Final owner is a physical result. Optional disclosure keys are an additional declared channel. The actor can reveal the same information in its words. Word matching supplies review candidates, not a complete privacy test."}
    (HERE/"results.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print([(k,v["initial_successes"],v["attempts"],len(v["untyped_words_to_inspect"])) for k,v in sets.items()])

if __name__=="__main__":main()
