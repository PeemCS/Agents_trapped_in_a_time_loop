/* @bruin
name: town.air_sources
type: duckdb.sql
description: Match the final switch, contributing actor and earlier recorded take to their committed source decisions.
depends:
  - town.air_refs
  - town.decisions
materialization:
  type: table
custom_checks:
  - name: every reference resolves on this date at or before airtime
    query: SELECT count(*) FROM town.air_sources WHERE source_slot IS NULL OR source_day <> air_day OR source_slot > air_slot
    value: 0
  - name: producer selects the bulletin in the evening
    query: SELECT count(*) FROM town.air_sources WHERE ordinal = 0 AND (source_actor IS DISTINCT FROM selected_by OR source_slot IS DISTINCT FROM air_slot OR NOT ends_with(source_id, '-producer'))
    value: 0
  - name: every selected recording has a prior physical capture
    query: SELECT count(*) FROM (SELECT world, bulletin_id, channel FROM town.air_sources WHERE channel IN ('camera_take','filed_forecast') GROUP BY ALL HAVING COUNT(*) FILTER (WHERE source_slot < air_slot AND ((channel = 'camera_take' AND source_action IN ('film_festival','film_cornet_player')) OR (channel = 'filed_forecast' AND source_action = 'file_forecast'))) = 0)
    value: 0
@bruin */
SELECT r.world, r.bulletin_id, CAST(r.air_slot AS INTEGER) AS air_slot,
       CAST(r.air_day AS INTEGER) AS air_day, r.channel, r.selected_by,
       CAST(r.ordinal AS INTEGER) AS ordinal, r.source_id,
       CAST(d.slot AS INTEGER) AS source_slot, CAST(d.day AS INTEGER) AS source_day,
       d.actor AS source_actor, d.action AS source_action, d.place AS source_place
FROM town.air_refs AS r
LEFT JOIN town.decisions AS d ON d.world = r.world AND d.event_id = r.source_id
