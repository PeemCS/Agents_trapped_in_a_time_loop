# 20-loop model run

[run.json](run.json) is the publication export of a 20-loop model-driven trajectory. It includes story events, model labels, allowed actions, stated reasons, and receipt-to-event references. The run reached its configured cap on February 2. In loop 17, Rita’s nightly trust reached 0.65. Phil could invite her to stay and chose to wait.

[invitation-fork.json](invitation-fork.json) reconstructs the final loop-17 exchange from archived state. The branch supplies a human-authored invitation and samples Rita's response from the same supporting-cast model. Rita declined. The reconstruction covers that exchange and its ending checks.

To watch the archived trajectory from the repository root, run:

```sh
python3 -m loopday.viewer --run showcase/live-run/run.json
```

## Verify memory retrieval

The [memory audit](memory-audit/) contains the archived records, a test query, and SQL that replays the scoring rule. The query combines token overlap, memory strength, recency, mood match, and location match, then orders the top eight records by priority and score.

With the optional `duckdb` Python package installed, run this check from the repository root.

```sh
python3 - <<'PY'
import json
from pathlib import Path

import duckdb

audit = Path("showcase/live-run/memory-audit")
rows = duckdb.sql((audit / "memory-score.sql").read_text()).project("event_id").fetchall()
selected = [event_id for (event_id,) in rows]
assert selected == json.loads((audit / "expected.json").read_text()), selected
print(selected)
PY
```
