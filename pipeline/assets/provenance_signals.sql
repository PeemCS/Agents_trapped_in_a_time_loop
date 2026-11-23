/* @bruin
name: core.provenance_signals
type: duckdb.sql
materialization:
  type: table
depends:
  - raw.events
  - raw.run_metadata
@bruin */

with signals as (
    select * from read_ndjson('{{ var.dataset }}/signals.ndjson', columns = {
        'run_id': 'VARCHAR', 'kind': 'VARCHAR', 'event_id': 'VARCHAR', 'actor': 'VARCHAR',
        'surface': 'VARCHAR', 'loop': 'INTEGER', 'matched': 'VARCHAR', 'prior_event': 'VARCHAR'
    })
)
select signals.*, json_extract(config, '$.alias_names')::boolean as alias_names
from signals
join raw.events as event on signals.run_id = event.run_id and signals.event_id = event.id
join raw.run_metadata as meta on signals.run_id = meta.run_id
where event.mode = 'live'
