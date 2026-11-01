"""Offline snapshot integrity and independent analytical reconciliation."""

import csv
import hashlib
import json
import re
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(
            (ROOT / "data/analytics/catalog.json").read_text(encoding="utf-8")
        )
        with (ROOT / "data/analytics/facts.csv").open(
            newline="", encoding="utf-8"
        ) as f:
            cls.facts = list(csv.DictReader(f))

    def test_grain_is_unique_and_complete(self):
        self.assertEqual(len(self.facts), 6732)
        keys = {
            (r["dataset"], r["year"], r["state"], r["category"], r["category2"])
            for r in self.facts
        }
        self.assertEqual(len(keys), len(self.facts))
        self.assertEqual(len(self.catalog["states"]), 36)
        for r in self.facts:
            self.assertIn(r["state"], self.catalog["states"])
            self.assertIn(
                r["category"], self.catalog["datasets"][r["dataset"]]["categories"]
            )

    def test_count_types_and_supported_measure_contract(self):
        for r in self.facts:
            for m in ["accidents", "fatalities", "injuries", "fatal_crashes"]:
                self.assertTrue(r[m] == "" or re.fullmatch("[0-9]+", r[m]))
                if m not in self.catalog["datasets"][r["dataset"]]["metrics"]:
                    self.assertEqual(r[m], "")

    def test_catalog_describes_actual_rows_years_and_categories(self):
        counts = Counter(r["dataset"] for r in self.facts)
        for key, meta in self.catalog["datasets"].items():
            data = [r for r in self.facts if r["dataset"] == key]
            self.assertEqual(counts[key], meta["rows"])
            self.assertEqual(sorted({int(r["year"]) for r in data}), meta["years"])
            self.assertEqual(
                sorted({r["category"] for r in data}), sorted(meta["categories"])
            )

    def test_age_bands_preserve_order_across_both_source_pages(self):
        data = [r for r in self.facts if r["dataset"] == "demographics"]
        ages = sorted({(int(r["ordinal"]), r["category"]) for r in data})
        self.assertEqual(
            [name for _, name in ages],
            [
                "Under 18",
                "18–25",
                "25–35",
                "35–45",
                "45–60",
                "60 and above",
                "Age unknown",
            ],
        )

    def test_source_registry_and_reconciliation_manifest(self):
        ids = {s["source_id"] for s in self.catalog["sources"]}
        self.assertTrue(all(r["source_id"] in ids for r in self.facts))
        self.assertEqual(len(self.catalog["checks"]), 394)
        for check in self.catalog["checks"]:
            self.assertEqual(check["sum"], check["printed_total"])
        for source in self.catalog["sources"]:
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(source["verified"])
            self.assertTrue(source["url"].startswith("https://"))

    def test_source_defined_additive_classifications(self):
        totals = {
            (r["state"], r["year"]): r for r in self.facts if r["dataset"] == "totals"
        }
        for family, metrics in [
            ("collisions", ["accidents", "fatalities", "injuries"]),
            ("months", ["accidents", "fatalities", "injuries", "fatal_crashes"]),
            ("hours", ["accidents"]),
            ("urban", ["accidents", "fatalities", "injuries"]),
            ("outcomes", ["accidents"]),
            ("demographics", ["fatalities"]),
        ]:
            data = [r for r in self.facts if r["dataset"] == family]
            for key in {(r["state"], r["year"]) for r in data}:
                selected = [r for r in data if (r["state"], r["year"]) == key]
                for metric in metrics:
                    # A source dash stays unavailable, so only compare fully observed cells.
                    if totals[key][metric] != "" and all(
                        r[metric] != "" for r in selected
                    ):
                        with self.subTest(family=family, key=key, metric=metric):
                            self.assertEqual(
                                sum(int(r[metric]) for r in selected),
                                int(totals[key][metric]),
                            )

    def test_latest_detail_is_not_invented(self):
        families = {r["dataset"] for r in self.facts if r["year"] == "2024"}
        self.assertEqual(families, {"totals", "users", "outcomes"})

    def test_independent_sql_sensitivity_matches_api_default(self):
        from api.analysis import Query, analyze

        report = json.loads(
            (ROOT / "analysis/results.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            report["snapshot"],
            hashlib.sha256(
                (ROOT / "data/analytics/facts.csv").read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(len(report["priority_sensitivity"]), 27)
        for case in report["priority_sensitivity"]:
            actual = analyze(
                Query(
                    top_n=case["top_n"],
                    threshold=case["threshold"],
                    min_accidents=case["minimum_accidents"],
                )
            )["risk"]
            self.assertEqual({r["state"] for r in actual}, set(case["states"]))
