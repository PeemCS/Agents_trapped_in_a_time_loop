"""Run the learned overnight retrieval treatment in an isolated v2 sampler instance."""
import argparse
from pathlib import Path
import badges
import surprise_memory
from town import atomic_json, fingerprint


def config(args,seed):
    c=badges.card_config(args,seed)
    c["badge_parent_code"]=c["code"];c["protocol"]="town-surprise-1"
    c["code"]=fingerprint([c["badge_parent_code"],Path(surprise_memory.__file__).read_text(),Path(__file__).read_text()])
    return c


def main():
    p=argparse.ArgumentParser(description=__doc__);badges.sampler.run_args(p);a=p.parse_args()
    badges.sampler.config=config;badges.sampler.cue=surprise_memory.cue
    for seed in a.seeds:
        row=badges.sampler.sample(a,seed)
        row["municipality"]=badges.badge_cues.TOWN.split(",")[0]
        row["credential_names"]=badges.badge_cues.FULL[row["protagonist"]]
        atomic_json(a.out/f"seed-{seed}.json",row)

if __name__=="__main__":main()
