#!/usr/bin/env python3
"""Reproducible, checksum-bound 2023 MoRTH category extraction for RoadLens V2.

Each dataset retains its own reporting grain. Published discrepancies are recorded,
not reconciled by changing counts. Uses Poppler; output needs no PDF at runtime.
"""

import csv
import json
import re
import subprocess
from pathlib import Path

from extract_morth import ORDER, TOKEN, count
from fetch_morth import REPORTS, report_path, verify

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "dataset",
    "year",
    "state",
    "category",
    "category2",
    "ordinal",
    "accidents",
    "fatalities",
    "injuries",
    "fatal_crashes",
    "source_id",
]


def table(
    pages, page, selected, first_four=False, ranks_override=None, report_year=2023
):
    lines = pages[page - 1].splitlines()
    h = next(i for i, s in enumerate(lines) if re.match(r"^\s*1\s+2\s+\d+\s+\d+", s))
    columns = [int(x) for x in re.findall(r"\d+", lines[h])][2:]
    ranks = (
        ranks_override
        if ranks_override is not None
        else [columns[1], columns[3]]
        if page in (185, 190, 191)
        else [7]
        if page in (145, 147)
        else []
    )
    rows = {}
    total = None
    for line in lines[h + 1 :]:
        if re.match(r"^\s*Total\s", line):
            values = [m.group() for m in TOKEN.finditer(line)]
            total = dict(zip([c for c in columns if c not in ranks], values))
            break
        m = re.match(r"^\s*(\d{1,2})\s+", line)
        if not m:
            continue
        idx = int(m.group(1))
        values = [x.group() for x in TOKEN.finditer(line)][1:]
        if idx in rows:
            raise ValueError(f"Duplicate serial on page {page}")
        if page in (145, 147) or first_four:
            row = dict(zip(columns[:4], values[:4]))
        else:
            if idx == 34 and ranks and len(values) == len(columns) - len(ranks):
                for rank in ranks:
                    values.insert(columns.index(rank), "NA")
            if len(values) != len(columns):
                raise ValueError(
                    f"Page {page}, row {idx}: {len(values)} cells != {len(columns)}"
                )
            row = dict(zip(columns, values))
        rows[idx] = {c: count(row[c]) for c in selected}
    if set(rows) != set(range(1, 37)) or total is None:
        raise ValueError(f"Incomplete page {page}")
    evidence = []
    for c in selected:
        expected = count(total[c])
        actual = sum(r[c] or 0 for r in rows.values())
        if actual != expected:
            raise ValueError(
                f"Page {page} column {c}: extracted {actual} != printed {expected}"
            )
        evidence.append(
            {
                "report_year": report_year,
                "pdf_page": page,
                "column": c,
                "sum": actual,
                "printed_total": expected,
            }
        )
    return rows, evidence


def build():
    pdf = report_path(2023)
    verify(pdf, REPORTS[2023]["sha256"])
    pages = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\f")
    facts = []
    catalog = {}
    checks = []
    source = json.loads((ROOT / "data/input/sources.json").read_text())

    def register(
        key,
        title,
        definition,
        metrics,
        grain="state/year/category",
        note="",
        pages_=None,
    ):
        catalog[key] = {
            "id": key,
            "title": title,
            "definition": definition,
            "metrics": metrics,
            "grain": grain,
            "note": note,
            "pages": pages_ or [],
            "source": "MoRTH Road Accidents in India 2023",
            "url": REPORTS[2023]["url"],
            "sha256": REPORTS[2023]["sha256"],
        }

    def add(key, year, state, category="All", category2="", ordinal=0, **metrics):
        facts.append(
            dict(
                dataset=key,
                year=year,
                state=state,
                category=category,
                category2=category2,
                ordinal=ordinal,
                **{
                    m: metrics.get(m, "")
                    for m in ["accidents", "fatalities", "injuries", "fatal_crashes"]
                },
                source_id=f"morth2023_{key}",
            )
        )

    # Retain verified existing sources, definitions and years.
    for key, filename, title, definition, metrics in [
        (
            "totals",
            "state_totals",
            "All reported accidents",
            "All-road state totals; fatalities count people, not crashes.",
            ["accidents", "fatalities", "injuries", "fatal_crashes"],
        ),
        (
            "users",
            "vehicle_categories",
            "Victim road users",
            "Fatalities classified by victim road-user category. No accident denominator.",
            ["fatalities"],
        ),
        (
            "violations",
            "causes",
            "Reported traffic violations",
            "Reported attribution, not proof of causation.",
            ["accidents", "fatalities"],
        ),
        (
            "roads",
            "road_types",
            "Road classes",
            "National highways including expressways, state highways and other roads.",
            ["accidents", "fatalities"],
        ),
    ]:
        register(
            key,
            title,
            definition,
            metrics,
            note="Existing verified extracts; see source registry. Kerala road-user attribution changed in 2023."
            if key == "users"
            else "",
        )
        with (ROOT / "data/input" / f"{filename}.csv").open(
            newline="", encoding="utf-8"
        ) as f:
            for r in csv.DictReader(f):
                add(
                    key,
                    int(r["year"]),
                    r["state"],
                    r["category"],
                    **{m: count(r[m]) for m in ["accidents", "fatalities"]},
                )
                facts[-1]["source_id"] = r["source_id"]
    totals = {(r["year"], r["state"]): r for r in facts if r["dataset"] == "totals"}
    for page, metric in [(145, "injuries"), (147, "fatal_crashes")]:
        rows, ev = table(pages, page, [3, 4, 5, 6])
        checks += ev
        for serial, row in rows.items():
            for i, year in enumerate(range(2020, 2024)):
                totals[year, ORDER[serial - 1]][metric] = row[3 + i]
    register(
        "outcomes",
        "Crash injury outcomes",
        "Crash events classified by outcome. Fatal crashes are different from people killed.",
        ["accidents"],
        pages_=[149],
    )
    rows, ev = table(pages, 149, [3, 4, 5, 6, 7])
    checks += ev
    for serial, row in rows.items():
        assert sum(row[c] or 0 for c in [3, 4, 5, 6]) == row[7]
        for i, label in enumerate(
            [
                "Fatal crashes",
                "Grievous-injury crashes",
                "Minor-injury crashes",
                "Non-injury crashes",
            ]
        ):
            add(
                "outcomes",
                2023,
                ORDER[serial - 1],
                label,
                ordinal=i,
                accidents=row[3 + i],
            )

    def categories(key, title, definition, specs, note=""):
        register(
            key,
            title,
            definition,
            ["accidents", "fatalities", "injuries"],
            note=note,
            pages_=[s[0] for s in specs],
        )
        for page, groups in specs:
            columns = sorted(
                {
                    v
                    for group in groups
                    for v in group[1:]
                    if isinstance(v, int) and v > 0
                }
            )
            rows, ev = table(pages, page, columns)
            checks.extend(ev)
            for serial, row in rows.items():
                for label, a, f, g, m, total in groups:
                    injuries = (
                        row[total]
                        if total
                        else (row[g] + row[m] if row[g] != "" and row[m] != "" else "")
                    )
                    add(
                        key,
                        2023,
                        ORDER[serial - 1],
                        label,
                        accidents=row[a],
                        fatalities=row[f],
                        injuries=injuries,
                    )

    categories(
        "collisions",
        "Collision types",
        "Source-reported collision classification; categories are not causal effects.",
        [
            (173, [("Hit and run", 3, 4, 5, 6, 0), ("Parked vehicle", 7, 8, 9, 10, 0)]),
            (
                174,
                [
                    ("Hit from back", 11, 12, 13, 14, 0),
                    ("Hit from side", 15, 16, 17, 18, 0),
                ],
            ),
            (
                175,
                [
                    ("Run off road", 19, 20, 21, 22, 0),
                    ("Fixed object", 23, 24, 25, 26, 0),
                ],
            ),
            (
                176,
                [
                    ("Vehicle overturn", 27, 28, 29, 30, 0),
                    ("Head-on collision", 31, 32, 33, 34, 0),
                ],
            ),
            (177, [("Others", 35, 36, 37, 38, 0)]),
        ],
    )
    categories(
        "vehicles",
        "Reported impacting vehicles / objects",
        "Annexure 26 classification, distinct from victim-user fatalities in Annexure 29.",
        [
            (194, [("Pedestrians", 3, 4, 5, 6, 0), ("Bicycles", 7, 8, 9, 10, 0)]),
            (
                195,
                [
                    ("Two-wheelers", 11, 12, 13, 14, 0),
                    ("Auto rickshaws", 15, 16, 17, 18, 0),
                ],
            ),
            (
                196,
                [
                    ("Cars, taxis, vans and LMV", 19, 20, 21, 22, 0),
                    ("Trucks / lorries", 23, 24, 25, 26, 0),
                ],
            ),
            (
                197,
                [
                    ("Buses", 27, 28, 29, 30, 0),
                    ("Other non-motorized vehicles", 31, 32, 33, 34, 0),
                ],
            ),
            (198, [("Others", 35, 36, 37, 38, 0)]),
        ],
        note="Preserve source anomalies: Kerala bicycles reports 2 accidents and 88 deaths. Do not interpret category severity before investigating definitions/reporting. Vehicle severity is disabled.",
    )
    # Disable derived vehicle severity even though the report supplies both numbers.
    catalog["vehicles"]["severity_supported"] = False
    for key, title, definition, starts in [
        (
            "weather",
            "Weather conditions",
            "Reported weather marginals, not joinable to time/vehicle categories.",
            [
                (191, ["Sunny / clear", "Rainy"], 3, 10),
                (192, ["Foggy / misty", "Hail / sleet"], 15, 20),
                (193, ["Others"], 25, None),
            ],
        ),
        (
            "features",
            "Road features",
            "Reported road features, not precise locations.",
            [
                (181, ["Straight road", "Curved road"], 3, 8),
                (182, ["Bridge", "Culvert"], 13, 18),
                (183, ["Potholes", "Steep grade"], 23, 28),
                (184, ["Road works / construction", "Others"], 33, 38),
            ],
        ),
        (
            "junctions",
            "Junction types",
            "Reported junction categories; no specific junction coordinates.",
            [
                (185, ["T-junction", "Y-junction"], 3, 10),
                (186, ["Four-arm junction", "Staggered junction"], 15, 20),
                (187, ["Roundabout"], 25, None),
            ],
        ),
        (
            "controls",
            "Traffic controls",
            "Reported traffic control categories.",
            [
                (188, ["Traffic light signal", "Police controlled"], 3, 8),
                (189, ["Stop sign", "Flashing signal / blinker"], 13, 18),
                (190, ["Uncontrolled"], 23, None),
            ],
        ),
        (
            "environment",
            "Road environment",
            "Reported land-use environment.",
            [
                (178, ["Residential area", "Institutional area"], 3, 8),
                (179, ["Market / commercial area", "Open area"], 13, 18),
                (180, ["Others"], 23, None),
            ],
        ),
        (
            "urban",
            "Urban and rural",
            "All-road urban/rural counts, not a cross-filter for other marginal datasets.",
            [(226, ["Urban", "Rural"], 3, 8)],
        ),
    ]:
        specs = []
        for page, labels, start, second in starts:
            groups = []
            for label, c in zip(labels, [start, second]):
                # Some first groups include rank columns after accidents/fatalities.
                if page in (185, 191) and c == 3:
                    groups.append((label, 3, 5, 7, 8, 9))
                elif page == 190:
                    groups.append((label, 23, 25, 27, 28, 29))
                else:
                    groups.append((label, c, c + 1, c + 2, c + 3, c + 4))
            specs.append((page, groups))
        categories(key, title, definition, specs)
    register(
        "months",
        "Monthly accidents",
        "State × year × month; not jointly classified with vehicle/weather.",
        ["accidents", "fatalities", "injuries", "fatal_crashes"],
        pages_=list(range(229, 235)),
    )
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    for i, page in enumerate(range(229, 235)):
        base = 3 + i * 12
        cols = list(range(base, base + 12))
        rows, ev = table(pages, page, cols)
        checks += ev
        for serial, row in rows.items():
            for offset in [0, 6]:
                c = base + offset
                add(
                    "months",
                    2023,
                    ORDER[serial - 1],
                    months[i * 2 + offset // 6],
                    ordinal=i * 2 + offset // 6,
                    fatal_crashes=row[c],
                    accidents=row[c + 1],
                    fatalities=row[c + 2],
                    injuries=row[c + 5],
                )
    register(
        "hours",
        "Time of occurrence",
        "Reported 3-hour bands and unknown time; accident counts only.",
        ["accidents"],
        pages_=[236],
    )
    rows, ev = table(pages, 236, list(range(3, 13)))
    checks += ev
    bands = [
        "06:00–09:00",
        "09:00–12:00",
        "12:00–15:00",
        "15:00–18:00",
        "18:00–21:00",
        "21:00–24:00",
        "00:00–03:00",
        "03:00–06:00",
        "Unknown time",
    ]
    for serial, row in rows.items():
        assert sum(row[c] or 0 for c in range(3, 12)) == row[12]
        for i, label in enumerate(bands):
            add(
                "hours",
                2023,
                ORDER[serial - 1],
                label,
                ordinal=(i + 2) % 8 if i < 8 else 8,
                accidents=row[i + 3],
            )
    register(
        "matrix",
        "Victim / impacting-vehicle matrix",
        "Fatalities in jointly reported victim × opponent categories; not all victim groups are supplied.",
        ["fatalities"],
        "state/year/victim/opponent",
        note="Pedestrian total is 35,203 here versus 35,221 in Annexure 29. Kerala differs by 18; preserve both source totals pending reconciliation.",
        pages_=list(range(206, 211)),
    )
    opponents = [
        "Bicycles",
        "Two-wheelers",
        "Auto rickshaws",
        "Cars / LMV",
        "Trucks / lorries",
        "Buses",
        "Other non-motorized",
        "Others",
    ]
    for page, victim in zip(
        range(206, 211),
        ["Pedestrians", "Bicycles", "Two-wheelers", "Cars / LMV", "Trucks / lorries"],
    ):
        rows, ev = table(pages, page, list(range(3, 12)))
        checks += ev
        for serial, row in rows.items():
            assert sum(row[c] or 0 for c in range(3, 11)) == row[11]
            for i, opponent in enumerate(opponents):
                add(
                    "matrix",
                    2023,
                    ORDER[serial - 1],
                    victim,
                    opponent,
                    i,
                    fatalities=row[3 + i],
                )
    catalog["junctions"]["note"] = (
        "Junction-related crashes only; this is not the all-road universe."
    )
    catalog["controls"]["note"] = (
        "Traffic-control classifications cover reported junction-related crashes, not all-road totals."
    )
    register(
        "demographics",
        "Victim age and reported sex",
        "Persons killed by reported age band and sex. Source age-band labels are preserved; these are not vehicle-specific rates.",
        ["fatalities"],
        "state/year/age/sex",
        pages_=[211, 212],
    )
    for page, ages, start in [
        (211, ["Under 18", "18–25", "25–35", "35–45"], 3),
        (212, ["45–60", "60 and above", "Age unknown"], 11),
    ]:
        rows, ev = table(pages, page, list(range(start, start + len(ages) * 2)))
        checks += ev
        for serial, row in rows.items():
            for i, age in enumerate(ages):
                for offset, sex in enumerate(["Male", "Female"]):
                    add(
                        "demographics",
                        2023,
                        ORDER[serial - 1],
                        age,
                        sex,
                        i,
                        fatalities=row[start + i * 2 + offset],
                    )
    # The monthly facts must reconcile to annual totals for every complete state/measure.
    for state in ORDER:
        for metric in ["accidents", "fatalities", "injuries", "fatal_crashes"]:
            values = [
                r[metric]
                for r in facts
                if r["dataset"] == "months" and r["state"] == state
            ]
            annual = totals[2023, state][metric]
            if annual != "" and all(v != "" for v in values) and sum(values) != annual:
                raise ValueError(
                    f"Monthly mismatch {state} {metric}: {sum(values)} vs {annual}"
                )
    # Audited latest annual totals/outcomes and victim categories; other category
    # datasets retain explicitly reported 2023 coverage rather than inferred 2024 data.
    latest = ROOT / "data/sources/road-accidents-india-2024.pdf"
    sha = "70a2cf4a92c7074d13502a84ce25d606ce4655d4e7e79d49740c97fd908600ea"
    verify(latest, sha)
    p24 = subprocess.run(
        ["pdftotext", "-layout", str(latest), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\f")
    annual = {}
    for page, metric in [
        (167, "accidents"),
        (168, "fatalities"),
        (169, "injuries"),
        (170, "fatal_crashes"),
    ]:
        rows, ev = table(
            p24, page, [6], first_four=True, ranks_override=[7], report_year=2024
        )
        checks += ev
        for serial, row in rows.items():
            annual.setdefault(serial, {})[metric] = row[6]
    for serial, values in annual.items():
        add("totals", 2024, ORDER[serial - 1], **values)
        facts[-1]["source_id"] = "morth2024_totals"
    rows, ev = table(p24, 172, [3, 4, 5, 6, 7], report_year=2024)
    checks += ev
    for serial, row in rows.items():
        assert sum(row[c] or 0 for c in [3, 4, 5, 6]) == row[7]
        for i, label in enumerate(
            [
                "Fatal crashes",
                "Grievous-injury crashes",
                "Minor-injury crashes",
                "Non-injury crashes",
            ]
        ):
            add(
                "outcomes",
                2024,
                ORDER[serial - 1],
                label,
                ordinal=i,
                accidents=row[3 + i],
            )
            facts[-1]["source_id"] = "morth2024_outcomes"
    for page, groups in [
        (
            209,
            [
                ("Pedestrians", 5),
                ("Bicycles", 8),
                ("Two-wheelers", 11),
                ("Auto rickshaws", 15),
                ("Cars, taxis, vans and LMV", 18),
            ],
        ),
        (
            210,
            [
                ("Trucks / lorries", 21),
                ("Buses", 24),
                ("Other non-motor vehicles (E-rickshaw)", 27),
                ("Others", 30),
            ],
        ),
    ]:
        rows, ev = table(
            p24,
            page,
            [c for _, c in groups],
            ranks_override=[12] if page == 209 else [],
            report_year=2024,
        )
        checks += ev
        for serial, row in rows.items():
            for label, c in groups:
                add("users", 2024, ORDER[serial - 1], label, fatalities=row[c])
                facts[-1]["source_id"] = "morth2024_users"
    for key in ["totals", "outcomes", "users"]:
        source.append(
            {
                "source_id": "morth2024_" + key,
                "title": "MoRTH Road Accidents in India 2024",
                "url": "https://morth.gov.in/backend/documents/uploaded/Road%20Accidents%20in%20India%20-%202024.pdf",
                "sha256": sha,
                "locator": {
                    "totals": "Annexures 2–5, PDF 167–170",
                    "outcomes": "Annexure 7, PDF 172",
                    "users": "Annexure 29, PDF 209–210",
                }[key],
                "definition": catalog[key]["definition"],
                "verified": True,
            }
        )
    keys = [
        (r["dataset"], r["year"], r["state"], r["category"], r["category2"])
        for r in facts
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate grain keys")
    for key, meta in catalog.items():
        rows = [r for r in facts if r["dataset"] == key]
        meta["years"] = sorted({r["year"] for r in rows})
        meta["categories"] = sorted({r["category"] for r in rows})
        meta["rows"] = len(rows)
        meta["source_ids"] = sorted({r["source_id"] for r in rows})
        meta["secondary_count"] = max(
            1, len({r["category2"] for r in rows if r["category2"]})
        )
        meta["severity_supported"] = meta.get(
            "severity_supported",
            "accidents" in meta["metrics"] and "fatalities" in meta["metrics"],
        )
    for key, meta in catalog.items():
        for sid in meta["source_ids"]:
            if not any(s["source_id"] == sid for s in source):
                source.append(
                    {
                        "source_id": sid,
                        "title": "MoRTH Road Accidents in India 2023",
                        "url": REPORTS[2023]["url"],
                        "sha256": REPORTS[2023]["sha256"],
                        "locator": "PDF pages " + ", ".join(map(str, meta["pages"])),
                        "definition": meta["definition"],
                        "verified": True,
                    }
                )
    output = ROOT / "data/analytics"
    output.mkdir(exist_ok=True)
    with (output / "facts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(facts)
    (output / "catalog.json").write_text(
        json.dumps(
            {
                "datasets": catalog,
                "states": sorted(ORDER),
                "years": [2020, 2021, 2022, 2023, 2024],
                "sources": source,
                "checks": checks,
                "caveats": [
                    "Annexure 29 reports 35,221 pedestrian fatalities; Annexure 29(a) reports 35,203. Kerala differs by 18 (1,147 versus 1,129); preserve both definitions.",
                    "Impacting-vehicle category severity disabled pending source reconciliation.",
                    "State summaries do not support precise hotspots or arbitrary joint category filters.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "rows": len(facts),
                "datasets": len(catalog),
                "column_reconciliations": len(checks),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    build()
