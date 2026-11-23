/* @bruin
name: core.loop_comparison
type: duckdb.sql
materialization:
  type: table
depends:
  - raw.events
  - raw.run_metadata
@bruin */

select
    events.run_id,
    meta.mode as run_mode,
    events.loop,
    count(*) filter (where type = 'decision') as decisions,
    count(*) filter (where type = 'decision' and events.mode = 'replay') as replayed_decisions,
    count(*) filter (where type = 'decision' and list_count(recalled) > 0) as decisions_with_recall,
    count(*) filter (where type = 'decision' and list_has_any(stated_support, recalled)) as decisions_with_cited_memory,
    count(*) filter (where type = 'divergence') as divergences,
    count(*) filter (where type = 'prediction') as predictions,
    count(*) filter (where type = 'test_result') as recorded_experiment_results,
    count(*) filter (where type = 'evidence_use') as verified_evidence_uses,
    count(*) filter (where type = 'memory' and op in ('FUZZ', 'DELETE')) as changed_or_lost_memories,
    avg(reward) filter (where type = 'decision' and events.actor = 'phil') as mean_phil_reward,
    max(value) filter (where type = 'deja_vu') as peak_deja_vu,
    count(*) filter (where json_extract_string(transport, '$.status') in ('verified', 'partially_verified')) as band_receipts,
    count(*) filter (where type = 'pencil' and state = 'whole') as whole_pencil_observations,
    count(*) filter (where type = 'day_two') > 0 as day_two,
    meta.complete
from raw.events as events
left join raw.run_metadata as meta using (run_id)
group by events.run_id, events.loop, meta.mode, meta.complete
