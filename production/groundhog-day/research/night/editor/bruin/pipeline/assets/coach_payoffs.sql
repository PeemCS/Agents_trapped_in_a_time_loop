/* @bruin
name: town.coach_payoffs
type: duckdb.sql
description: One row per actual arrival. Tell the editor whether an entire physical gag is available.
depends:
  - town.decisions
materialization:
  type: table
custom_checks:
  - name: ready payoff has three ordered anchors
    query: SELECT count(*) FROM town.coach_payoffs WHERE ready AND (city_slot IS NULL OR wake_slot IS NULL OR NOT (arrival_slot < city_slot AND city_slot < wake_slot))
    value: 0
@bruin */

WITH lead_events AS (
  SELECT world, CAST(slot AS INTEGER) AS slot, CAST(day AS INTEGER) AS day,
         actor, origin, place, action, event_id
  FROM town.decisions
  WHERE CAST(is_lead AS BOOLEAN)
),
arrivals AS (
  SELECT * FROM lead_events
  WHERE action = 'take_coach_to_Pittsburgh'
    AND origin <> 'Pittsburgh' AND place = 'Pittsburgh'
),
anchors AS (
  SELECT a.world, a.actor, a.day, a.event_id AS arrival_id, a.slot AS arrival_slot,
         max(c.slot) FILTER (WHERE c.origin = 'Pittsburgh' AND c.place = 'Pittsburgh') AS city_slot,
         min(w.slot) AS wake_slot,
         count(*) FILTER (WHERE c.origin <> 'Pittsburgh' OR c.place <> 'Pittsburgh') AS left_city_early
  FROM arrivals a
  LEFT JOIN lead_events c ON a.world = c.world AND c.day = a.day AND c.slot > a.slot
  LEFT JOIN lead_events w ON a.world = w.world AND w.day = a.day + 1
  GROUP BY a.world, a.actor, a.day, a.event_id, a.slot
)
SELECT a.world, a.actor, a.day, a.arrival_id, a.arrival_slot, a.city_slot,
       c.event_id AS city_id, a.wake_slot, w.event_id AS wake_id,
       coalesce(a.city_slot IS NOT NULL AND a.left_city_early = 0 AND w.origin = 'inn', FALSE) AS ready
FROM anchors a
LEFT JOIN lead_events c ON a.world = c.world AND a.city_slot = c.slot
LEFT JOIN lead_events w ON a.world = w.world AND a.wake_slot = w.slot
