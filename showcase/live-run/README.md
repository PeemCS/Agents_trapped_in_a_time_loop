# 20-loop live run

[run.json](run.json) is a publication export of the Qwen and Muse cast’s 20-loop continuation. It retains story events, model labels, allowed actions, stated reasons, and receipt-to-event references. The run stopped at its configured cap while the town was still on February 2. In loop 17, Rita’s nightly trust reached 0.65. Phil had the option to invite her, and chose to wait.

[invitation-fork.json](invitation-fork.json) records a separate reconstruction of the final loop-17 exchange. The branch supplies a human-authored invitation, then lets Rita’s live Muse model decide. Rita declined.

To watch the exported live run:

```bash
python3 -m loopday.viewer --run showcase/live-run/run.json
```

[memory-audit](memory-audit/) contains the test query, archived memory records and SQL used to reproduce Phil’s ordered top eight in DuckDB. The result is a replay of the scoring rule using a test query on archived memory. Run it with a local `loopday` DuckDB connection from the repo root:

```bash
bruin query -c loopday -q "$(cat showcase/live-run/memory-audit/memory-score.sql)"
```

The returned event IDs should match [expected.json](memory-audit/expected.json).
