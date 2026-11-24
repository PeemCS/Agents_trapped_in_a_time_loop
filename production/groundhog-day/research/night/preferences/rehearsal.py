"""Two turns from the same checkpoint. Build the blinded preference packet."""
import argparse
import hashlib
import json
import random
from shutil import copyfile
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from scenarios import TASKS

SEED = 61439
HELD_OUT = {'awning', 'seed', 'vows', 'scores', 'ferry'}
FEATURES = ('current_project_fraction', 'uncertainty_resolved', 'third_party_promise_kept',
            'boundary_crossed', 'report_filed')


@dataclass(frozen=True)
class Take:
    clip: str
    features: tuple
    legal: bool


def setting(task):
    parts = [task.setup, 'There is time for two short actions.',
             f"The reporter has promised to {task.promise.action.replace('the promised ', 'the ')}.",
             f'For their own story they hope to {task.report.action}.']
    for item, what in [(task.promise, 'the promise'), (task.report, 'the story')]:
        if item.due == 1:
            parts.append(f'Only the first turn is early enough for {what}.')
    return ' '.join(parts)


def run(task, plan):
    """The private answer is read only when a question is actually asked."""
    assert len(plan) == 2
    willing = {'uncertain': None, 'refusal': False}.get(task.mode, True)
    work = questions = pressure = 0
    promise = report = False
    steps, effects = [], []
    for turn, move in enumerate(plan, 1):
        if move in 'hg':
            move = 'w' if willing is True else ('r' if move == 'h' else 'p')
        if move == 'a':
            assert task.ask
            action = task.ask
            if willing is None:
                questions = 1
                willing = task.yes
                reply = ' ' + task.answer
            else:
                pressure += 1
                reply = ' The answer is still no.'
        else:
            reply = ''
            if move == 'w':
                assert willing is True and work < 2
                action = task.work[work]
                work += 1
            elif move == 'x':
                assert task.old
                action = task.old
                pressure += 1
                effects.append(task.violation)
            elif move == 'p':
                action = task.promise.action
                if turn > task.promise.due:
                    action = "arrive too late to " + action
                promise = promise or turn <= task.promise.due
            elif move == 'r':
                action = task.report.action
                if turn > task.report.due:
                    action = "arrive too late to " + action
                report = report or turn <= task.report.due
            elif move == 'z':
                action = 'stay out of the way until the next bell'
            else:
                raise ValueError(move)
        steps.append(('First' if turn == 1 else 'Next') + f', they {action}.' + reply)
    effects.extend([task.result[work], task.promise.done if promise else task.promise.missed,
                    task.report.done if report else task.report.missed])
    return Take(' '.join(steps + effects), (work / 2, questions, int(promise), pressure, int(report)), pressure == 0)


def pairs(task):
    """Comparisons and partition fixed before any labels. p=promise, r=report, w=work."""
    if task.mode == 'request':
        return [('ww', 'pw'), ('rw', 'pr' if task.promise.due == 1 else 'rp'), ('pw', 'rw')]
    if task.mode == 'promise':
        return [('ww', 'pw'), ('pw', 'pr'), ('rw', 'pw')]
    if task.mode == 'uncertain':
        return [('ah', 'rp' if task.report.due == 1 else 'pr'), ('ag', 'pa'), ('ra', 'ag')]
    if task.mode == 'refusal':
        return [('ar', 'pz'), ('xp', 'rz'), ('rp', 'pr')]
    if task.mode == 'changed':
        return [('xp', 'rw'), ('ww', 'pw'), ('rw', 'pr' if task.promise.due == 1 else 'rp')]
    raise ValueError(task.mode)


def reserves(task):
    menus = {'request': ('ww', 'rw', 'wr', 'wp', 'pw', 'rp', 'pr'),
             'promise': ('ww', 'rw', 'wr', 'wp', 'pw', 'rp', 'pr'),
             'uncertain': ('ah', 'ag', 'ar', 'ap', 'ra', 'pa', 'rp', 'pr'),
             'refusal': ('az', 'ap', 'ar', 'zp', 'rz', 'pr', 'rp', 'xp', 'xr'),
             'changed': ('xw', 'xr', 'xp', 'ww', 'pr', 'pw', 'rp', 'rw')}
    used = {frozenset(pair) for pair in pairs(task)}
    for left, right in combinations(menus[task.mode], 2):
        if frozenset((left, right)) not in used and run(task, left).features != run(task, right).features:
            yield left, right


def deck():
    rng = random.Random(SEED)
    rows = []
    for task in TASKS:
        for a, b in pairs(task):
            if rng.getrandbits(1):
                a, b = b, a
            uid = f'{rng.getrandbits(40):010x}'
            rows.append((uid, task, a, b))
    rng.shuffle(rows)
    return rows


RUBRIC = ('Each pair is a fictional two-turn rehearsal from the same starting situation; the consequences are authored. '
          'Which course would you prefer this local reporter take, given what they knew when choosing, what the people '
          'asked for, and the consequences shown? Choose A, B, tie (equally good or bad), or skip (too little evidence '
          'to judge). Weigh competing obligations as you see fit. Judge the conduct, including people other than the '
          'speaker. Repeated situations have different choices. There are no hidden lines of dialogue to infer.')


def packet():
    return {'instructions': RUBRIC, 'comparisons': [
        {'id': uid, 'situation': setting(task), 'A': run(task, a).clip, 'B': run(task, b).clip}
        for uid, task, a, b in deck()]}


def digest():
    return hashlib.sha256(json.dumps(packet(), ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def export(folder):
    folder.mkdir(parents=True, exist_ok=True)
    save(folder / 'packet.json', packet())
    copyfile(Path(__file__).with_name('label.py'), folder / 'label.py')
    save(folder / 'labels-template.json', {'packet_sha256': digest(), 'rater_type': '', 'rater': '',
                                           'ratings': {uid: '' for uid, *_ in deck()}})
    print(f'{len(deck())} comparisons; packet {digest()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    export(parser.parse_args().output)
