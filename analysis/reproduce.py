"""Independent SQL analysis and transparent threshold sensitivity; no fitted forecasts."""

import hashlib
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def run():
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE facts AS SELECT * FROM read_csv(?,header=true,types={year:INTEGER,accidents:BIGINT,fatalities:BIGINT,injuries:BIGINT,fatal_crashes:BIGINT})",
        [str(ROOT / "data/analytics/facts.csv")],
    )

    def query(sql):
        result = con.execute(sql)
        return [
            dict(zip([c[0] for c in result.description], r)) for r in result.fetchall()
        ]

    annual = query(
        "SELECT year,SUM(accidents) accidents,SUM(fatalities) fatalities,COUNT(fatalities) reporting_states,SUM(injuries) injuries,SUM(fatal_crashes) fatal_crashes FROM facts WHERE dataset='totals' GROUP BY year ORDER BY year"
    )
    paired = query(
        "SELECT a.year,COUNT(*) states,SUM(a.fatalities) current_deaths,SUM(b.fatalities) previous_deaths,100.0*(SUM(a.fatalities)-SUM(b.fatalities))/SUM(b.fatalities) change_pct FROM facts a JOIN facts b ON a.state=b.state AND a.year=b.year+1 AND b.dataset='totals' WHERE a.dataset='totals' AND a.year=2024 AND a.fatalities IS NOT NULL AND b.fatalities IS NOT NULL GROUP BY a.year"
    )
    users = query(
        "SELECT category,SUM(fatalities) fatalities,100.0*SUM(fatalities)/172890 share_of_reported_deaths_pct FROM facts WHERE dataset='users' AND year=2023 GROUP BY category ORDER BY fatalities DESC"
    )
    peak = query(
        "SELECT category,SUM(accidents) accidents FROM facts WHERE dataset='hours' AND year=2023 GROUP BY category ORDER BY accidents DESC"
    )
    sensitivity = []
    for n in [5, 10, 15]:
        for threshold in [25, 50, 75]:
            for minimum in [0, 100, 500]:
                selected = query(
                    f"WITH s AS (SELECT state,accidents,fatalities,100.0*fatalities/NULLIF(accidents,0) severity,ROW_NUMBER() OVER(ORDER BY accidents DESC,state) rank FROM facts WHERE dataset='totals' AND year=2023) SELECT state,rank <= {n} high_accidents,COALESCE(severity >= {threshold} AND accidents >= {minimum},false) high_severity FROM s WHERE rank <= {n} OR (severity >= {threshold} AND accidents >= {minimum}) ORDER BY high_accidents AND high_severity DESC,accidents DESC,state"
                )
                sensitivity.append(
                    {
                        "top_n": n,
                        "threshold": threshold,
                        "minimum_accidents": minimum,
                        "union_count": len(selected),
                        "intersection_count": sum(
                            r["high_accidents"] and r["high_severity"] for r in selected
                        ),
                        "states": [r["state"] for r in selected],
                    }
                )
    result = {
        "snapshot": hashlib.sha256(
            (ROOT / "data/analytics/facts.csv").read_bytes()
        ).hexdigest(),
        "annual_reported_totals": annual,
        "compatible_2024_death_comparison": paired,
        "road_users_2023": users,
        "time_bands_2023": peak,
        "priority_sensitivity": sensitivity,
        "interpretation": "Descriptive police-reported aggregates; counts are not exposure-adjusted risk, causal effects, or forecasts. Compare identical definitions; 2020–2021 pandemic disruption and reporting changes affect trends.",
    }
    (ROOT / "analysis/results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    con.close()
    return result


if __name__ == "__main__":
    result = run()
    print(
        json.dumps(
            {
                "annual": result["annual_reported_totals"],
                "cohort": result["compatible_2024_death_comparison"],
                "sensitivity_cases": len(result["priority_sensitivity"]),
            },
            indent=2,
        )
    )
