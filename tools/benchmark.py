"""Measure the built app locally; results are not an Internet performance guarantee."""

import argparse
import json
import math
import statistics
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    samples = []
    for i in range(102):
        body = json.dumps(
            {
                "dataset": ["totals", "matrix", "demographics", "hours"][i % 4],
                "years": [2023],
            }
        ).encode()
        t = time.perf_counter()
        request = urllib.request.Request(
            args.url + "/api/query",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            assert response.status == 200
            json.load(response)
        if i >= 2:
            samples.append((time.perf_counter() - t) * 1000)
    ui = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        t = time.perf_counter()
        page.goto(args.url)
        page.wait_for_selector(".results[aria-busy=false] .chart svg")
        page.wait_for_timeout(
            400
        )  # Include the full configured 350ms initial animation.
        first = (time.perf_counter() - t) * 1000
        for i in range(10):
            year = str(2022 if i % 2 == 0 else 2023)
            t = time.perf_counter()
            page.select_option("#year", year)
            page.wait_for_selector(f'.results[aria-busy=false][data-years="{year}"]')
            page.wait_for_timeout(
                400
            )  # Conservative completion allowance, including animation.
            ui.append((time.perf_counter() - t) * 1000)
        browser.close()

    def summary(values):
        return {
            "n": len(values),
            "p50_ms": round(statistics.median(values), 2),
            "p95_ms": round(sorted(values)[math.ceil(len(values) * 0.95) - 1], 2),
            "max_ms": round(max(values), 2),
        }

    result = {
        "conditions": "Linux cloud container; loopback HTTP; built frontend; 6732 rows; no network throttling; fresh browser context; UI measurements include a conservative 400ms animation allowance.",
        "api_warm": summary(samples),
        "first_usable_with_animation_ms": round(first, 2),
        "ui_filters_with_animation": summary(ui),
    }
    (ROOT / "docs/performance.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
