"""Shared SQL calculation layer. Facts are never joined across reporting grains."""

import hashlib
import json
import threading
from pathlib import Path
from typing import Literal

import duckdb
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "data/analytics/catalog.json").read_text(encoding="utf-8"))
SNAPSHOT = hashlib.sha256((ROOT / "data/analytics/facts.csv").read_bytes()).hexdigest()
CON = duckdb.connect(":memory:")
CON.execute(
    "CREATE TABLE facts AS SELECT * FROM read_csv(?, header=true, types={year:INTEGER,ordinal:INTEGER,accidents:BIGINT,fatalities:BIGINT,injuries:BIGINT,fatal_crashes:BIGINT})",
    [str(ROOT / "data/analytics/facts.csv")],
)
LOCK = threading.RLock()
METRICS = ("accidents", "fatalities", "injuries", "fatal_crashes", "severity")


class Query(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str = "totals"
    years: list[int] = Field(
        default_factory=lambda: [2023], min_length=1, max_length=20
    )
    states: list[str] = Field(default_factory=list, max_length=36)
    category: str | None = None
    metric: Literal[
        "accidents", "fatalities", "injuries", "fatal_crashes", "severity"
    ] = "fatalities"
    top_n: Literal[5, 10, 15] = 10
    min_accidents: int = Field(default=0, ge=0, le=1000000)
    threshold: float = Field(default=50, ge=0, le=1000, allow_inf_nan=False)

    @field_validator("dataset")
    @classmethod
    def dataset_known(cls, v):
        if v not in CATALOG["datasets"]:
            raise ValueError("Unknown dataset")
        return v

    @field_validator("years")
    @classmethod
    def years_known(cls, v):
        if any(y not in CATALOG["years"] for y in v):
            raise ValueError("Unsupported reporting year")
        return sorted(set(v))

    @field_validator("states")
    @classmethod
    def states_known(cls, v):
        if any(s not in CATALOG["states"] for s in v):
            raise ValueError("Unknown state")
        return sorted(set(v))


def rows(sql, params):
    with LOCK:
        result = CON.execute(sql, params)
        names = [d[0] for d in result.description]
        return [dict(zip(names, r)) for r in result.fetchall()]


def condition(q):
    parts = ["dataset = ?", "year IN (" + ",".join("?" for _ in q.years) + ")"]
    params = [q.dataset, *q.years]
    if q.states:
        parts.append("state IN (" + ",".join("?" for _ in q.states) + ")")
        params.extend(q.states)
    if q.category:
        if q.category not in CATALOG["datasets"][q.dataset]["categories"]:
            raise ValueError("Category does not belong to this dataset")
        parts.append("category = ?")
        params.append(q.category)
    return " AND ".join(parts), params


AGG = (
    ", ".join([f"SUM({m}) AS {m}, COUNT({m}) AS {m}_count" for m in METRICS[:-1]])
    + ", COUNT(*) AS observations, COUNT(CASE WHEN accidents IS NOT NULL AND fatalities IS NOT NULL THEN 1 END) AS pairs, SUM(CASE WHEN accidents IS NOT NULL AND fatalities IS NOT NULL THEN accidents END) AS paired_accidents, SUM(CASE WHEN accidents IS NOT NULL AND fatalities IS NOT NULL THEN fatalities END) AS paired_fatalities"
)


def decorate(r, metric, meta):
    r["severity"] = (
        100 * r["paired_fatalities"] / r["paired_accidents"]
        if r["paired_accidents"] and meta["severity_supported"]
        else None
    )
    for m in METRICS[:-1]:
        if m not in meta["metrics"]:
            r[m] = None
    r["value"] = r[metric]
    return r


def analyze(q: Query):
    where, params = condition(q)
    meta = CATALOG["datasets"][q.dataset]

    def grouped(columns=""):
        prefix = columns + ", " if columns else ""
        sql = (
            "SELECT "
            + prefix
            + AGG
            + " FROM facts WHERE "
            + where
            + (" GROUP BY " + columns if columns else "")
        )
        return [decorate(r, q.metric, meta) for r in rows(sql, params)]

    summary = grouped()[0]
    state_rows = grouped("state")
    categories = grouped("category")
    trend = grouped("year")
    series = grouped("state, year")
    for group in [state_rows, categories]:
        group.sort(
            key=lambda r: (
                -(r["value"] if r["value"] is not None else -1),
                r.get("state", r.get("category", "")),
            )
        )
    trend.sort(key=lambda r: r["year"])
    series.sort(key=lambda r: (r["state"], r["year"]))
    ordered = {
        r["category"]: int(r["ordinal"])
        for r in rows(
            "SELECT category,MIN(ordinal) ordinal FROM facts WHERE "
            + where
            + " GROUP BY category",
            params,
        )
    }
    for r in categories:
        r["ordinal"] = ordered[r["category"]]
    matrix = (
        grouped("category, category2")
        if q.dataset in ("matrix", "demographics")
        else grouped("state, category")
        if q.dataset == "hours"
        else []
    )
    high_accidents = {
        r["state"]
        for r in sorted(
            (r for r in state_rows if r["accidents"] is not None),
            key=lambda r: (-r["accidents"], r["state"]),
        )[: q.top_n]
    }
    risk = []
    for r in state_rows:
        complete = r["pairs"] == len(q.years) and r["severity"] is not None
        eligible = complete and r["paired_accidents"] >= q.min_accidents
        high_severity = eligible and r["severity"] >= q.threshold
        high_accident = r["state"] in high_accidents
        risk_class = (
            "Unclassified"
            if not complete
            else "Below minimum denominator"
            if not eligible
            else "Combined high risk"
            if high_accident and high_severity
            else "High accidents"
            if high_accident
            else "High severity"
            if high_severity
            else "Other reported"
        )
        if high_accident or high_severity:
            risk.append(
                {
                    **r,
                    "high_accidents": high_accident,
                    "high_severity": high_severity,
                    "risk": risk_class,
                }
            )
    priority = {
        "Combined high risk": 0,
        "High accidents": 1,
        "High severity": 2,
        "Below minimum denominator": 3,
        "Unclassified": 4,
    }
    risk.sort(key=lambda r: (priority[r["risk"]], -(r["accidents"] or 0), r["state"]))
    ncat = 1 if q.category else len(meta["categories"])
    opponents = meta.get("secondary_count", 1)
    expected = len(q.states or CATALOG["states"]) * len(q.years) * ncat * opponents
    available_count = (
        summary["pairs"] if q.metric == "severity" else summary[q.metric + "_count"]
    )
    supported = (
        q.metric in meta["metrics"]
        or q.metric == "severity"
        and meta["severity_supported"]
    )
    status = (
        "unavailable"
        if not supported or summary["value"] is None
        else "partial"
        if available_count < expected
        else "reported"
    )
    actual_years = [r["year"] for r in trend]
    change = None
    if len(q.years) == 1 and supported and q.years[0] - 1 in CATALOG["years"]:
        previous = q.model_copy(update={"years": [q.years[0] - 1]})
        pw, pp = condition(previous)
        old = decorate(
            rows("SELECT " + AGG + " FROM facts WHERE " + pw, pp)[0], q.metric, meta
        )
        # Only report a like-for-like period change when both slices are complete.
        if (
            available_count == expected
            and (old["pairs"] if q.metric == "severity" else old[q.metric + "_count"])
            == expected
            and old["value"]
        ):
            change = 100 * (summary["value"] - old["value"]) / old["value"]
    scale_query = q.model_copy(update={"years": meta["years"]})
    sw, sp = condition(scale_query)
    scales = [
        decorate(r, q.metric, meta)
        for r in rows(
            "SELECT state,year, "
            + AGG
            + " FROM facts WHERE "
            + sw
            + " GROUP BY state,year",
            sp,
        )
    ]
    map_scale = max([r["value"] for r in scales if r["value"] is not None] or [1])
    if q.states:
        trend_scale = map_scale
    else:
        annual = [
            decorate(r, q.metric, meta)
            for r in rows(
                "SELECT year, " + AGG + " FROM facts WHERE " + sw + " GROUP BY year", sp
            )
        ]
        trend_scale = max([r["value"] for r in annual if r["value"] is not None] or [1])
    return {
        "map_scale": map_scale,
        "trend_scale": trend_scale,
        "query": q.model_dump(),
        "dataset": meta,
        "summary": summary,
        "states": state_rows,
        "categories": categories,
        "trend": trend,
        "series": series,
        "matrix": matrix,
        "risk": risk if q.dataset == "totals" else [],
        "coverage": {
            "status": status,
            "expected_observations": expected,
            "available_observations": available_count if supported else 0,
            "observed_years": actual_years,
            "unprepared_years": [y for y in q.years if y not in meta["years"]],
        },
        "change_pct": change,
        "snapshot": SNAPSHOT,
    }


def filtered_facts(q):
    where, params = condition(q)
    return rows(
        "SELECT * FROM facts WHERE "
        + where
        + " ORDER BY year,state,ordinal,category,category2",
        params,
    )
