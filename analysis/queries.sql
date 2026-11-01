-- Run against the DuckDB facts table: one dataset at a time.
-- Annual reported totals. NULL means unavailable, never zero.
SELECT year, SUM(accidents) accidents, SUM(fatalities) fatalities,
       COUNT(fatalities) reporting_states, SUM(injuries) injuries,
       SUM(fatal_crashes) fatal_crashes
FROM facts WHERE dataset = 'totals' GROUP BY year ORDER BY year;

-- Weighted severity from matched accident/death observations only.
SELECT state, SUM(accidents) accidents, SUM(fatalities) fatalities,
       100.0 * SUM(fatalities) FILTER (WHERE accidents IS NOT NULL)
       / NULLIF(SUM(accidents) FILTER (WHERE fatalities IS NOT NULL), 0) severity
FROM facts WHERE dataset = 'totals' AND year = 2023
GROUP BY state ORDER BY accidents DESC, state;

-- A real joint table: do not join independent weather/time/vehicle marginals.
SELECT category victim, category2 opponent, SUM(fatalities) fatalities
FROM facts WHERE dataset = 'matrix' AND year = 2023
GROUP BY category, category2 ORDER BY victim, fatalities DESC;

-- Observed unknown time remains part of the national accident count.
SELECT category, SUM(accidents) accidents
FROM facts WHERE dataset = 'hours' AND year = 2023
GROUP BY category ORDER BY accidents DESC;
