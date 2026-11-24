/* @bruin
name: raw.events
type: duckdb.sql
materialization:
  type: table
custom_checks:
  - name: unique_event_ids_per_run
    value: 0
    query: |
      select count(*)
      from (
        select run_id, id
        from raw.events
        group by run_id, id
        having id is null or count(*) > 1
      )
  - name: valid_event_time
    value: 0
    query: |
      select count(*) from raw.events
      where loop is null or loop < 1 or tick is null
        or tick < 0 or tick > 35 or "order" is null or "order" < 0
@bruin */

select *
from read_ndjson(
    '{{ var.dataset }}/events.ndjson',
    columns = {
        'run_id': 'VARCHAR', 'id': 'VARCHAR', 'order': 'BIGINT', 'loop': 'INTEGER',
        'tick': 'INTEGER', 'time': 'VARCHAR', 'type': 'VARCHAR',
        'actor': 'VARCHAR', 'action': 'VARCHAR', 'mode': 'VARCHAR', 'source': 'VARCHAR',
        'anchor': 'VARCHAR', 'location': 'VARCHAR', 'text': 'VARCHAR',
        'state': 'VARCHAR', 'failure_kind': 'VARCHAR',
        'recalled': 'VARCHAR[]', 'stated_support': 'VARCHAR[]', 'current_evidence': 'VARCHAR[]',
        'prediction': 'VARCHAR', 'action_evidence': 'VARCHAR', 'observation': 'VARCHAR',
        'prediction_id': 'VARCHAR', 'action_event_id': 'VARCHAR', 'observation_event_id': 'VARCHAR',
        'checkpoint_fingerprint': 'VARCHAR', 'available_actions': 'VARCHAR[]', 'reward': 'DOUBLE',
        'return_to_go': 'DOUBLE', 'phase': 'VARCHAR', 'op': 'VARCHAR', 'npc_mode': 'VARCHAR',
        'model_metadata': 'JSON', 'transport': 'JSON', 'message_receipts': 'JSON',
        'state_after': 'JSON', 'gate_level': 'INTEGER', 'value': 'DOUBLE'
    }
)
where run_id is not null
