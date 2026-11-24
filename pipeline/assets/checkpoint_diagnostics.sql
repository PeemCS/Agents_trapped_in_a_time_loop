/* @bruin
name: train.checkpoint_diagnostics
type: duckdb.sql
materialization:
  type: table
depends:
  - train.qualified_rollouts
@bruin */

with action_returns as (
    select
        checkpoint, seed, condition, loop, tick, baseline_action, action,
        json_extract_string(observation, '$.actions[*]') as available_actions,
        json_extract_string(observation, '$.location_id') as location,
        avg(outcome) as mean_return,
        count(*) as trials,
        list(evidence_id order by trial) as evidence_ids
    from train.qualified_rollouts
    group by all
), compared as (
    select
        *,
        row_number() over (partition by checkpoint order by mean_return desc, action) as rank,
        max(mean_return) filter (where action = baseline_action) over (partition by checkpoint) as baseline_return
    from action_returns
)
select
    checkpoint, seed, condition, loop, tick, location, baseline_action,
    case
        when list_contains(available_actions, 'avoid_puddle') then 'puddle'
        when list_count(list_filter(available_actions, option -> starts_with(option, 'help:'))) > 0 then 'helping'
        when list_contains(available_actions, 'practice_piano') then 'piano_practice'
        when location = 'piano_teacher' then 'piano_studio_between_lessons'
        when list_contains(available_actions, 'invite_rita') or list_contains(available_actions, 'talk:rita')
            then 'social'
        else 'general'
    end as opportunity,
    action as best_action, trials, baseline_return, mean_return as best_return,
    mean_return - baseline_return as baseline_return_gap,
    evidence_ids as best_action_evidence
from compared
where rank = 1
