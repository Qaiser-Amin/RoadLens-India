#!/usr/bin/env python3
"""RoadLens V2 web/API server; run after installing requirements.txt."""

import argparse
import csv
import io

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from api.analysis import CATALOG, ROOT, SNAPSHOT, Query, analyze, filtered_facts

app = FastAPI(title="RoadLens India", version="2.0.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                for e in exc.errors()
            ]
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0", "snapshot": SNAPSHOT}


@app.get("/api/catalog")
def catalog():
    return {
        **CATALOG,
        "snapshot": SNAPSHOT,
        "default_year": 2023,
        "latest_year": max(CATALOG["years"]),
    }


@app.post("/api/query")
def query(q: Query):
    try:
        return analyze(q)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/export")
def export(q: Query):
    try:
        data = filtered_facts(q)
    except ValueError as e:
        raise HTTPException(422, str(e))
    output = io.StringIO()
    fields = [
        "dataset",
        "year",
        "state",
        "category",
        "category2",
        "accidents",
        "fatalities",
        "injuries",
        "fatal_crashes",
        "source_id",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="roadlens-{q.dataset}-filtered.csv"',
            "X-RoadLens-Snapshot": SNAPSHOT,
        },
    )


@app.post("/api/report")
def report(q: Query):
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    try:
        result = analyze(q)
    except ValueError as e:
        raise HTTPException(422, str(e))
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, title="RoadLens evidence brief")
    styles = getSampleStyleSheet()
    story = []

    def para(t, style="BodyText"):
        story.append(Paragraph(escape(str(t)), styles[style]))
        story.append(Spacer(1, 9))

    para("RoadLens India — Evidence Brief", "Title")
    para(result["dataset"]["title"], "Heading2")
    para(
        f"Years: {', '.join(map(str, q.years))} | States: {', '.join(q.states) or 'All reporting states'} | Category: {q.category or 'All'}"
    )
    para(
        f"Measure: {q.metric} | Coverage: {result['coverage']['status']} | Snapshot: {SNAPSHOT[:16]}"
    )
    for k in ["accidents", "fatalities", "injuries", "fatal_crashes", "severity"]:
        v = result["summary"][k]
        para(
            f"{k.replace('_', ' ').title()}: {round(v, 1) if isinstance(v, float) else v if v is not None else 'Unavailable'}"
        )
    para(
        f"Priority rule: Top {q.top_n} by accidents; severity >= {q.threshold}; minimum paired accident denominator {q.min_accidents}."
    )
    para("State comparison (selected measure)", "Heading2")
    values = [["State / UT", q.metric]] + [
        [
            r["state"],
            str(round(r["value"], 1) if isinstance(r["value"], float) else r["value"])
            if r["value"] is not None
            else "Unavailable",
        ]
        for r in result["states"]
    ]
    t = Table(values, colWidths=[340, 110], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f2ed")),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#087e75")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t)
    para("Interpretation and next steps", "Heading2")
    para(
        "Use these reported aggregates to prioritize investigation and compare like-for-like periods. Validate suspected patterns with local incident data before selecting an intervention. Counts are not per-trip risk or proof of causation."
    )
    para(result["dataset"]["definition"])
    para(result["dataset"].get("note", ""))
    for note in CATALOG["caveats"]:
        para(note)
    para("Source and provenance", "Heading2")
    for source in CATALOG["sources"]:
        if source["source_id"] in result["dataset"]["source_ids"]:
            para(
                source.get("title", "MoRTH")
                + " | "
                + source.get("locator", "")
                + " | "
                + source.get("url", "")
            )
    para("Additional category tables: " + result["dataset"].get("url", ""))
    doc.build(story)
    return Response(
        output.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="roadlens-{q.dataset}-evidence.pdf"'
        },
    )


# Previous source downloads remain available as stable Tableau inputs.
@app.get("/api/data")
def legacy():
    result = {}
    for table in ["state_totals", "vehicle_categories", "causes", "road_types"]:
        with (ROOT / "data/input" / f"{table}.csv").open(
            newline="", encoding="utf-8"
        ) as f:
            data = list(csv.DictReader(f))
        for r in data:
            r["year"] = int(r["year"])
            for m in ["accidents", "fatalities"]:
                r[m] = int(r[m]) if r[m] else None
        result[table] = data
    result["sources"] = CATALOG["sources"]
    return result


DIST = ROOT / "web/dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
else:

    @app.get("/")
    def unbuilt():
        raise HTTPException(503, "Frontend not built. Run npm ci and npm run build.")


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
