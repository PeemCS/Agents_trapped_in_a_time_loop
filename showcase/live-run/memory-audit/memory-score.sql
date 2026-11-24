with input as (
    select * from read_json_auto('showcase/live-run/memory-audit/memory-input.json')
), context as (
    select * from read_json_auto('showcase/live-run/memory-audit/query.json')
), query_words as (
    select word, count(*) as hits
    from context, unnest(tokens) as t(word) group by word
), record_words as (
    select i, word, count(*) as hits
    from input, unnest(tokens) as t(word) group by i, word
), lexical_scores as (
    select r.i, sum(r.hits * coalesce(q.hits, 0)) /
        nullif(sqrt(sum(r.hits * r.hits) * (select sum(hits * hits) from query_words)), 0) as lexical
    from record_words r left join query_words q using (word)
    group by r.i
), signals as (
    select i.i, event_id, text, i.loop, priority, coalesce(lexical, 0) as lexical,
        least(1.0, importance * exp(
            -(case when kind = 'observation' then 0.35 else 0.09 end)
            * greatest(0, c.clock - last_access_loop)) + 0.15 * ln(1 + access_count)) as strength,
        exp(-0.45 * (c.clock - last_access_loop)) as recency,
        1 - abs(c.mood - valence) / 2 as mood_match,
        (i.location is not distinct from c.location)::int as location_match
    from input i cross join context c
    left join lexical_scores l on i.i = l.i
    where i.loop < c.clock
)
select *, 0.42 * lexical + 0.24 * strength + 0.14 * recency
    + 0.10 * mood_match + 0.10 * location_match as score
from signals order by priority desc, score desc, loop desc, i limit 8
