/* @bruin
name: raw.run_metadata
type: duckdb.sql
materialization:
  type: table
@bruin */

select *
from read_ndjson('{{ var.dataset }}/metadata.ndjson', columns = {
    'run_id': 'VARCHAR', 'mode': 'VARCHAR', 'complete': 'BOOLEAN', 'ending': 'VARCHAR',
    'seed': 'INTEGER', 'condition': 'VARCHAR', 'config': 'JSON', 'provider_calls': 'INTEGER',
    'provider_cache_hits': 'INTEGER', 'provider_usage': 'JSON'
})
where run_id is not null
