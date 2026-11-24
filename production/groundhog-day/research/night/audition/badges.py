"""Shoot an explicitly labelled casting intervention with the unchanged v2 physical simulator."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
STORY=HERE.parent/"story"
sys.path.insert(0,str(STORY))
import badge_cues
from town import atomic_json, fingerprint

# Load an isolated sampler instance. Its prompt provider and configuration signature are local to this CLI.
# This leaves the frozen baseline module (including simultaneous jobs launched elsewhere) untouched.
spec=importlib.util.spec_from_file_location("badge_shoot_sampler",STORY/"v2.py")
sampler=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampler)
frozen_config=sampler.config


def card_config(args,seed):
    c=frozen_config(args,seed)
    c["parent_code"]=c["code"]
    c["protocol"]="town-credentials-1"
    c["code"]=fingerprint([c["parent_code"],Path(badge_cues.__file__).read_text(),Path(__file__).read_text()])
    return c


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sampler.run_args(parser)
    args=parser.parse_args()
    sampler.config=card_config
    sampler.cue=badge_cues.cue
    for seed in args.seeds:
        row=sampler.sample(args,seed)
        row["municipality"]=badge_cues.TOWN.split(",")[0]
        row["credential_names"]=badge_cues.FULL[row["protagonist"]]
        atomic_json(args.out/f"seed-{seed}.json",row)


if __name__=="__main__":
    main()
