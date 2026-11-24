/* @bruin
name: core.agent_loop_diagnostics
type: duckdb.sql
materialization:
  type: table
depends:
  - raw.events
  - raw.run_metadata
@bruin */

with decisions as (
    select
        run_id, loop, actor,
        count(*) filter (where type = 'decision') as decisions,
        count(*) filter (where type = 'rejected') as rejected_decisions,
        count(*) filter (where type = 'rejected' and failure_kind = 'provider_timeout') as provider_timeout_waits,
        count(*) filter (where type = 'decision' and mode = 'replay') as replayed_decisions,
        count(*) filter (where type = 'decision' and list_count(recalled) > 0) as decisions_with_recall,
        count(*) filter (where type = 'decision' and list_has_any(stated_support, recalled))
            as decisions_citing_recall,
        count(*) filter (where type = 'decision' and json_extract_string(model_metadata, '$.provider') is not null)
            as model_decisions_with_metadata,
        count(*) filter (where type = 'decision' and json_extract_string(model_metadata, '$.cache_hit') = 'true')
            as cached_model_decisions,
        sum(try_cast(json_extract_string(model_metadata, '$.tokens.prompt_tokens') as bigint))
            filter (where type = 'decision' and json_extract_string(model_metadata, '$.cache_hit') = 'false')
            as reported_muse_prompt_tokens,
        sum(try_cast(json_extract_string(model_metadata, '$.tokens.completion_tokens') as bigint))
            filter (where type = 'decision' and json_extract_string(model_metadata, '$.cache_hit') = 'false')
            as reported_muse_completion_tokens,
        sum(try_cast(json_extract_string(model_metadata, '$.tokens') as bigint))
            filter (where type = 'decision' and json_extract_string(model_metadata, '$.provider') = 'colab')
            as recorded_qwen_generated_tokens,
        avg(reward) filter (where type = 'decision') as mean_recorded_reward
    from raw.events
    where actor is not null and type in ('decision', 'rejected')
    group by run_id, loop, actor
)
select
    decisions.*,
    meta.mode as run_mode,
    meta.condition,
    meta.complete,
    try_cast(json_extract_string(meta.config, '$.keep_memory') as boolean) as persistent_memory,
    json_extract(meta.config, '$.generation.steering') as requested_persona_steering,
    json_extract_string(meta.config, '$.verified_phil_runtime.adapter') as verified_phil_adapter
from decisions
join raw.run_metadata as meta using (run_id)
