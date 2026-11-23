/* @bruin
name: core.experiments
type: duckdb.sql
materialization:
  type: table
depends:
  - raw.events
custom_checks:
  - name: experimental_links_have_provenance
    value: 0
    query: select count(*) from core.experiments where not valid_provenance
@bruin */

with results as (
    select
        run_id, id, "order", actor, loop, tick, state,
        coalesce(prediction_id, prediction) as prediction_id,
        coalesce(action_event_id, action_evidence) as action_id,
        coalesce(observation_event_id, observation) as observation_id
    from raw.events
    where type = 'test_result'
)
select
    result.run_id,
    result.id as result_id,
    result.actor,
    result.loop,
    result.tick,
    result.prediction_id,
    result.action_id,
    result.observation_id,
    prediction.text as predicted,
    observation.text as observed,
    coalesce(
        prediction.type = 'prediction'
        and prediction.actor = result.actor
        and action.actor = result.actor
        and observation.actor = result.actor
        and prediction."order" < action."order"
        and action."order" < observation."order"
        and observation."order" < result."order"
        and (observation.state is null or observation.state = result.state),
        false
    ) as valid_provenance
from results as result
left join raw.events as prediction
    on result.run_id = prediction.run_id and result.prediction_id = prediction.id
left join raw.events as action
    on result.run_id = action.run_id and result.action_id = action.id
left join raw.events as observation
    on result.run_id = observation.run_id and result.observation_id = observation.id
