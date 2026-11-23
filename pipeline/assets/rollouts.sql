/* @bruin
name: raw.local_rollouts
type: duckdb.sql
materialization:
  type: table
custom_checks:
  - name: no_duplicate_rollout_evidence
    value: 0
    query: |
      select count(*)
      from (select evidence_id from raw.local_rollouts group by evidence_id having count(*) > 1)
  - name: only_world_simulation_rows
    value: 0
    query: |
      select count(*) from raw.local_rollouts
      where source is distinct from 'world_rollout' or outcome is null or not isfinite(outcome)
@bruin */

select * from read_ndjson('{{ var.dataset }}/rollouts.ndjson', columns = {
    'source': 'VARCHAR', 'group': 'VARCHAR', 'seed': 'INTEGER', 'trial': 'INTEGER',
    'condition': 'VARCHAR', 'checkpoint': 'VARCHAR', 'prefix_hash': 'VARCHAR',
    'loop': 'INTEGER', 'tick': 'INTEGER', 'action': 'VARCHAR', 'baseline_action': 'VARCHAR',
    'observation': 'JSON', 'outcome': 'DOUBLE', 'immediate_reward': 'DOUBLE',
    'ending': 'VARCHAR', 'ending_reason': 'VARCHAR', 'evidence_id': 'VARCHAR', 'suffix_hash': 'VARCHAR'
})
where evidence_id is not null
