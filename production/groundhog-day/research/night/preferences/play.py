"""Play the opening and trained heads through five two-turn scenes using common random draws."""
import argparse
import json
import random
from pathlib import Path

import numpy as np

from learn import screen_policy
from rehearsal import FEATURES, SEED, save


def pick(menu, field, draw):
    total = 0.
    for entry in menu:
        total += entry[field]
        if draw < total:
            return {'plan': entry['plan'], 'clip': entry['realized_clip']}
    raise RuntimeError('Policy probabilities do not sum to one.')


def play(result, seed):
    if result['features'] != list(FEATURES):
        raise ValueError('Model features do not match the rehearsal.')
    rng = random.Random(seed)
    w = np.asarray(result['weights'],dtype=float)
    if w.shape != (len(FEATURES),) or not np.isfinite(w).all():
        raise ValueError('Model needs one finite weight for each feature.')
    runs = []
    for scene in screen_policy(w):
        draw = rng.random()
        menu = scene['menu']
        opening = pick(menu, 'opening', draw)
        trained = pick(menu, 'trained', draw)
        runs.append({'task':scene['task'], 'setting':scene['setting'], 'shared_uniform_draw':draw,
                     'opening':opening, 'trained':trained, 'changed':opening['plan'] != trained['plan']})
    return {'kind':'Seeded policy replay in five authored two-turn simulations', 'seed':seed,
            'task_count':len(runs), 'changed_count':sum(s['changed'] for s in runs), 'scenes':runs}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',type=Path)
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--out',type=Path)
    args = parser.parse_args()
    result = play(json.loads(args.model.read_text()),args.seed)
    if args.out:
        save(args.out,result)
    else:
        print(json.dumps(result,ensure_ascii=False,indent=2))
