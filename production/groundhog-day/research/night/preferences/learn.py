"""Fit and evaluate a small preference model using actual ratings from a blind packet."""
import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from itertools import combinations
import json
import math
from pathlib import Path

import numpy as np

from rehearsal import FEATURES, HELD_OUT, SEED, TASKS, deck, digest, pairs, reserves, run, save

RIDGE = 0.04
BOOTSTRAPS = 400
PENDING_YES = 0.5  # A fixed public prior for an unanswered question.
Y = {'A': 1., 'B': 0., 'tie': .5}


def sigmoid(logit):
    return np.exp(-np.logaddexp(0., -np.asarray(logit)))


def fit(x, y):
    """Convex ridge-regularized Bradley–Terry likelihood with a soft target for a tie."""
    w = np.zeros(x.shape[1])
    for _ in range(80):
        p = sigmoid(x @ w)
        gradient = x.T @ (p - y) / len(y) + RIDGE * w
        hessian = (x.T * (p * (1 - p))) @ x / len(y) + RIDGE * np.eye(len(w))
        step = np.linalg.solve(hessian, gradient)
        w -= step
        if np.linalg.norm(step) < 1e-10:
            break
    if np.linalg.norm(x.T @ (sigmoid(x @ w) - y) / len(y) + RIDGE * w) > 1e-7:
        raise RuntimeError('Optimizer failed to converge.')
    return w


def unique_keys(pairs_list):
    obj = {}
    for k, v in pairs_list:
        if k in obj:
            raise ValueError(f'Duplicate JSON key {k!r}.')
        obj[k] = v
    return obj


def read_labels(path):
    obj = json.loads(path.read_text(), object_pairs_hook=unique_keys)
    if obj['packet_sha256'] != digest():
        raise ValueError(f'{path} names a different packet.')
    if obj.get('rater_type') not in ('agent', 'human') or not obj.get('rater', '').strip():
        raise ValueError(f'{path} requires an identified human or agent rater.')
    labels = obj['ratings']
    expected = {uid for uid, *_ in deck()}
    allowed = set(Y) | {'skip'}
    if labels.keys() != expected or any(v not in allowed for v in labels.values()):
        raise ValueError(f'{path} must contain one A/B/tie/skip for every packet ID.')
    return obj


def legal(task, plan):
    if 'x' in plan or ('a' in plan and task.mode != 'uncertain'):
        return False
    if 'w' in plan and task.mode in ('refusal', 'uncertain'):
        return False
    return True


def expected(task, plan):
    if task.mode == 'uncertain':
        yes = run(replace(task, yes=True), plan).features
        no = run(replace(task, yes=False), plan).features
        return PENDING_YES * np.array(yes) + (1 - PENDING_YES) * np.array(no)
    return np.array(run(task, plan).features)


def distribution(task, plans, w):
    mask = np.array([legal(task, plan) for plan in plans])
    if not mask.any():
        raise ValueError('The actor needs at least one available course of action.')
    values = np.array([w @ expected(task, plan) if ok else -np.inf for plan, ok in zip(plans, mask)])
    mass = np.exp(values - values.max())
    return mass / mass.sum()


def metrics(p, y):
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(y) == 0:
        return {'n': 0}
    losses = -y * np.log(p) - (1 - y) * np.log1p(-p)
    decisive = y != .5
    relevant = (p != .5) & decisive
    # Chance credit for exactly indifferent predictors on decisive labels.
    credit = np.sum((p[relevant] > .5) == (y[relevant] > .5)) + .5 * np.sum(decisive & ~relevant)
    bins = []
    for lo, hi in ((0., 1/3), (1/3, 2/3), (2/3, 1.00001)):
        selected = (p >= lo) & (p < hi)
        if selected.any():
            bins.append({'interval': [lo, min(1., hi)], 'n': int(selected.sum()),
                         'mean_p_A': float(p[selected].mean()), 'mean_A_target': float(y[selected].mean())})
    return {'n': len(y), 'ties': int(np.sum(~decisive)), 'log_loss_nats': float(losses.mean()),
            'brier_soft_target': float(np.mean((p-y)**2)),
            'decisive_agreement_chance_credit_at_indifference': float(credit / decisive.sum()) if decisive.any() else None,
            'calibration_bins': bins}


def entropy(p):
    p = np.asarray(p, dtype=float)
    q = np.clip(p, 1e-15, 1-1e-15)
    return np.where((p <= 0) | (p >= 1), 0., -q * np.log2(q) - (1-q)*np.log2(1-q))


def multientropy(counts):
    return float(-sum((n / sum(counts)) * math.log2(n / sum(counts)) for n in counts if n))


def priority_rule(task, plan):
    progress, _, promise, violations, _ = run(task, plan).features
    return (-violations, promise, progress)


def rule_prediction(task, a, b):
    a, b = priority_rule(task, a), priority_rule(task, b)
    return .75 if a > b else .25 if b > a else .5


def build_rows(raters):
    rows = []
    for uid, task, a, b in deck():
        left, right = run(task, a), run(task, b)
        for rater in raters:
            choice = rater['ratings'][uid]
            if choice == 'skip':
                continue
            rows.append(dict(uid=uid, task=task, a=a, b=b, y=Y[choice], rater=rater['rater'], choice=choice,
                             x=np.subtract(left.features, right.features), online_x=expected(task, a)-expected(task, b),
                             rule=rule_prediction(task, a, b)))
    return rows


def arrays(rows):
    return np.vstack([r['x'] for r in rows]), np.array([r['y'] for r in rows])


def evaluate(rows, w):
    x, y = arrays(rows)
    p = sigmoid(x @ w)
    return {'head_realized_consequences': metrics(p, y),
            'head_public_consequence_forecast_before_consent_mask': metrics(sigmoid(np.stack([r['online_x'] for r in rows]) @ w), y),
            'fixed_priority_rule': metrics([r['rule'] for r in rows], y), 'untrained_uniform': metrics(np.full(len(y), .5), y)}


def blocks(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['task'].key].append(row)
    return groups


def sample_tasks(groups, rng):
    keys = sorted(groups)
    return [row for i in rng.integers(len(keys), size=len(keys)) for row in groups[keys[i]]]


def heldout_intervals(test, w, rng):
    groups = blocks(test)
    records = []
    for _ in range(BOOTSTRAPS):
        rows = sample_tasks(groups, rng)
        x, y = arrays(rows)
        loss = float(np.mean(np.logaddexp(0., x @ w) - y * (x @ w)))
        rule = np.array([r['rule'] for r in rows])
        rule_loss = float(np.mean(-y*np.log(rule) - (1-y)*np.log1p(-rule)))
        records.append([loss, loss - math.log(2), loss - rule_loss])
    limits = np.quantile(records, [.025,.975], axis=0)
    return dict(zip(('head_loss', 'head_minus_uniform', 'head_minus_rule'), limits.T.tolist()))


def acquisition(boot):
    candidates = []
    seen = 0
    # The untouched test tasks never enter acquisition; remove duplicate contrasts per task.
    for task in TASKS:
        if task.key in HELD_OUT:
            continue
        vectors = set()
        seen_before = {tuple(np.subtract(run(task, a).features, run(task, b).features)) for a,b in pairs(task)}
        for a,b in reserves(task):
            if not legal(task, a) or not legal(task, b):
                continue
            delta = np.subtract(run(task, a).features, run(task, b).features)
            vec = tuple(delta)
            if vec in vectors or tuple(-delta) in vectors or vec in seen_before or tuple(-delta) in seen_before:
                continue
            vectors.add(vec)
            seen += 1
            preds = sigmoid(boot @ delta)
            hp = float(entropy(preds.mean()))
            disagreement = max(0., hp - float(np.mean(entropy(preds))))
            direction = min(vec, tuple(-delta))
            candidates.append((direction, {'task':task.key, 'a':a, 'b':b, 'p_A_mean':float(preds.mean()),
                        'predictive_entropy_bits':hp, 'disagreement_bits':disagreement,
                        'A':run(task,a).clip, 'B':run(task,b).clip}))
    candidates.sort(key=lambda item: -item[1]['disagreement_bits'])
    directions, tasks, shortlist = set(), set(), []
    for direction, row in candidates:
        if direction in directions or row['task'] in tasks:
            continue
        directions.add(direction)
        tasks.add(row['task'])
        shortlist.append(row)
        if len(shortlist) == 5:
            break
    return {'eligible_novel_contrasts': seen, 'next_five_distinct_tasks_and_feature_differences': shortlist}


def signal_entropy():
    # Count every screened fork occurrence, including repeated use of the same course of action.
    ds = [(run(task,a).features, run(task,b).features) for _,task,a,b in deck()]
    result = {}
    for i, name in enumerate(FEATURES):
        bits = np.asarray([[int(a[i]>0), int(b[i]>0)] for a,b in ds])
        result[name] = {'event_is_positive':True, 'fork_occurrences':int(bits.size), 'positive':int(bits.sum()),
                        'pooled_event_entropy_bits':float(entropy(bits.mean())),
                        'matched_pairs_where_outcome_changes':int(np.sum(bits[:,0] != bits[:,1])),
                        'mean_within_pair_entropy_bits':float(np.mean(entropy(bits.mean(axis=1))))}
    return result


def policy_checks(w):
    check = Counter()
    for _, task, a, b in deck():
        plans = [a,b,'pr']
        p = distribution(task, plans, w)
        for speaker, promise_holder in [('Mara', 'Kit'), ('Kit', 'Mara')]:
            recast = replace(task, setup=f'{speaker} speaks. {promise_holder} holds the earlier promise. ' + task.setup)
            assert np.array_equal(distribution(recast, plans, w),p)
        check['pairs_with_identical_policy_after_recast'] += 1
        if task.mode in ('refusal','changed'):
            options = ['xw' if task.mode == 'changed' else 'xp','pr','rw' if task.mode == 'changed' else 'ar']
            policy = distribution(task, options, w)
            assert all(p_i == 0 for p_i, plan in zip(policy, options) if not legal(task,plan))
            check['refused_or_revoked_case_zero_mass_on_crossing'] += 1
        if task.mode == 'uncertain':
            other = replace(task, yes=not task.yes, answer='WITHHELD')
            assert np.array_equal(distribution(other, plans, w),p)
            check['unanswered_cases_unchanged_when_future_reply_flips'] += 1
    return dict(check)


def screen_policy(w):
    menus = {'awning': ('ww','pw','rw'), 'seed':('ag','rp'), 'vows':('ar','xp','rp','pr'),
             'scores':('ww','pw','pr'), 'ferry':('xp','ww','rw','pw')}
    rows = []
    for task in TASKS:
        if task.key not in menus:
            continue
        plans = menus[task.key]
        before, after = distribution(task,plans,np.zeros(len(w))), distribution(task,plans,w)
        rows.append({'task':task.key,'setting':task.setup,'menu':[{'plan':plan, 'legal':legal(task,plan),'opening':float(p0),
                    'trained':float(p1),'realized_clip':run(task,plan).clip} for plan,p0,p1 in zip(plans,before,after)]})
    return rows


def compare_raters(raters):
    results = []
    for a,b in combinations(raters,2):
        counts = Counter()
        for uid, *_ in deck():
            x,y = a['ratings'][uid], b['ratings'][uid]
            if 'skip' in (x,y):
                counts['any_skip'] += 1
            elif x==y:
                counts['exact_agreement'] += 1
            elif 'tie' in (x,y):
                counts['one_tied'] += 1
            else:
                counts['opposite_decisive_votes'] += 1
        results.append({'raters':[a['rater'],b['rater']], 'counts':dict(counts)})
    return results


def train(raters):
    if len(set((r['rater_type'],r['rater']) for r in raters)) != len(raters):
        raise ValueError('Duplicate rater identities.')
    rows = build_rows(raters)
    training = [r for r in rows if r['task'].key not in HELD_OUT]
    test = [r for r in rows if r['task'].key in HELD_OUT]
    if not training or not test:
        raise ValueError('Training and held-out tasks each need at least one non-skipped vote.')
    x, y = arrays(training)
    w = fit(x,y)
    groups = blocks(training)
    rng = np.random.default_rng(SEED)
    boot = np.stack([fit(*arrays(sample_tasks(groups,rng))) for _ in range(BOOTSTRAPS)])
    predictions = []
    for r in test:
        predictions.append({'id':r['uid'],'task':r['task'].key,'A':r['a'],'B':r['b'],'rater':r['rater'],'label':r['choice'],
                            'p_A':float(sigmoid(w @ r['x'])),'p_A_public_forecast':float(sigmoid(w @ r['online_x']))})
    def rater_stats(r):
        counts = Counter(r['ratings'].values())
        return {'rater':r['rater'],'type':r['rater_type'],'counts':dict(counts),'four_way_label_entropy_bits':multientropy(counts.values())}
    return {'provenance':'Authored two-turn simulations. Labels supplied by identified blind raters. Model predicts their comparisons.',
            'packet_sha256':digest(),'raters':[rater_stats(r) for r in raters], 'rater_agreement':compare_raters(raters),
            'training_tasks':sorted(groups),'heldout_tasks':sorted(blocks(test)),'ridge':RIDGE,'bootstrap_draws':BOOTSTRAPS,
            'seed':SEED,'features':list(FEATURES),'weights':w.tolist(),'train_bootstrap_weight_intervals':np.quantile(boot,[.025,.975],axis=0).T.tolist(),
            'train':evaluate(training,w),'heldout':evaluate(test,w),'heldout_by_task':{k:evaluate(v,w) for k,v in blocks(test).items()},
            'heldout_task_bootstrap_95pct_fixed_head':heldout_intervals(test,w,rng),'heldout_predictions':predictions,
            'screened_fork_event_entropy':signal_entropy(), 'next_label_acquisition':acquisition(boot),
            'policy_checks':policy_checks(w),'heldout_scene_menus':screen_policy(w)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ratings', nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.resolve() in {path.resolve() for path in args.ratings}:
        parser.error("Choose a separate output file for the model results.")
    result = train([read_labels(p) for p in args.ratings])
    save(args.out,result)
    for k,v in result['heldout'].items():
        print(f"{k:50s} n={v['n']:2d}   log loss={v['log_loss_nats']:.4f}")
