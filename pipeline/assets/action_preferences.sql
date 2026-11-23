/* @bruin
name: train.local_preferences
type: duckdb.sql
materialization:
  type: table
depends:
  - train.qualified_rollouts
custom_checks:
  - name: positive_matched_preference
    value: 0
    query: |
      select count(*) from train.local_preferences
      where chosen_action = rejected_action or margin < 0.15 or source != 'world_rollout'
@bruin */

with actions as (
    select checkpoint, seed, action, avg(outcome) as mean_return,
           list(evidence_id order by trial) as evidence_ids
    from train.qualified_rollouts
    group by checkpoint, seed, action
), ranked as (
    select *, row_number() over (partition by checkpoint order by mean_return desc, action) as high,
           row_number() over (partition by checkpoint order by mean_return, action) as low
    from actions
)
select best.checkpoint, best.seed, 'world_rollout' as source, best.action as chosen_action,
       worst.action as rejected_action, best.mean_return - worst.mean_return as margin,
       best.evidence_ids as chosen_evidence, worst.evidence_ids as rejected_evidence
from ranked as best
join ranked as worst on best.checkpoint = worst.checkpoint
where best.high = 1 and worst.low = 1 and best.mean_return - worst.mean_return >= 0.15
