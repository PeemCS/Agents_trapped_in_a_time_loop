/* @bruin
name: train.qualified_rollouts
type: duckdb.sql
materialization:
  type: table
depends:
  - raw.local_rollouts
custom_checks:
  - name: every_collected_rollout_qualifies
    value: 0
    query: |
      select (select count(*) from raw.local_rollouts)
           - (select count(*) from train.qualified_rollouts)
@bruin */

with legal as (
    select *, json_extract_string(observation, '$.actions[*]') as action_options
    from raw.local_rollouts
    where source = 'world_rollout' and isfinite(outcome)
      and regexp_full_match(checkpoint, '[0-9a-f]{64}')
      and regexp_full_match(prefix_hash, '[0-9a-f]{64}')
      and regexp_full_match(suffix_hash, '[0-9a-f]{64}')
      and regexp_full_match(evidence_id, '[0-9a-f]{64}')
), eligible as (
    select checkpoint, count(distinct trial) as trial_count
    from legal
    where list_contains(action_options, action) and list_contains(action_options, baseline_action)
    group by checkpoint
    having count(distinct prefix_hash) = 1 and count(distinct observation::varchar) = 1
       and count(distinct baseline_action) = 1 and count(distinct seed) = 1
       and count(distinct action) = min(array_length(action_options)) and count(distinct action) >= 2
       and min(trial) = 0 and max(trial) + 1 = count(distinct trial)
       and count(*) = count(distinct (action, trial))
       and count(*) = count(distinct action) * count(distinct trial)
)
select legal.* exclude (action_options), eligible.trial_count
from legal join eligible using (checkpoint)
where list_contains(action_options, action)
