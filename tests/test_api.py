"""Independent source-value and contract checks for the production V2 API."""

import csv
import io
import math
import unittest

from fastapi.testclient import TestClient

from server import app


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def query(self, **kwargs):
        r = self.client.post("/api/query", json=kwargs)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_2023_annual_source_counts_and_paired_severity(self):
        r = self.query()
        s = r["summary"]
        self.assertEqual(
            [s[k] for k in ["accidents", "fatalities", "injuries", "fatal_crashes"]],
            [480583, 172890, 462825, 160509],
        )
        self.assertAlmostEqual(s["severity"], 100 * 172890 / 480582)
        self.assertEqual(r["coverage"]["status"], "partial")

    def test_2024_annual_source_counts(self):
        r = self.query(years=[2024])
        s = r["summary"]
        self.assertEqual(
            [s[k] for k in ["accidents", "fatalities", "injuries", "fatal_crashes"]],
            [487707, 177175, 471441, 164378],
        )
        self.assertEqual(r["coverage"]["status"], "reported")

    def test_invalid_query_contracts(self):
        for body in [
            {"dataset": "bad"},
            {"states": ["bad"]},
            {"years": []},
            {"years": [2099]},
            {"threshold": -1},
            {"threshold": 1001},
            {"metric": "bad"},
            {"dataset": "users", "category": "Rainy"},
            {"weather": "Rainy"},
        ]:
            with self.subTest(body=body):
                self.assertEqual(
                    self.client.post("/api/query", json=body).status_code, 422
                )

    def test_nonfinite_threshold_is_a_validation_error_not_server_crash(self):
        for token in ["NaN", "Infinity", "-Infinity"]:
            self.assertEqual(
                self.client.post(
                    "/api/query",
                    content='{"threshold":' + token + "}",
                    headers={"Content-Type": "application/json"},
                ).status_code,
                422,
            )

    def test_vehicle_and_victim_definitions_do_not_share_denominators(self):
        r = self.query(dataset="users", category="Two-wheelers")
        self.assertEqual(r["summary"]["fatalities"], 77539)
        self.assertIsNone(r["summary"]["accidents"])
        self.assertIsNone(r["summary"]["severity"])
        r = self.query(dataset="vehicles", metric="severity")
        self.assertIsNone(r["summary"]["value"])
        self.assertEqual(r["coverage"]["status"], "unavailable")

    def test_outcome_categories_sum_to_crash_events_not_fatalities(self):
        for year, total in [(2023, 480583), (2024, 487707)]:
            r = self.query(dataset="outcomes", years=[year], metric="accidents")
            self.assertEqual(sum(v["value"] for v in r["categories"]), total)
            self.assertIsNone(r["summary"]["fatalities"])

    def test_month_time_and_urban_sources(self):
        r = self.query(dataset="months", category="January")
        self.assertEqual(r["summary"]["fatalities"], 14610)
        r = self.query(dataset="hours", metric="accidents")
        self.assertEqual(r["summary"]["value"], 480583)
        self.assertEqual(
            next(v for v in r["categories"] if v["category"] == "Unknown time")[
                "value"
            ],
            5761,
        )
        r = self.query(dataset="urban", category="Urban")
        self.assertEqual(r["summary"]["fatalities"], 54479)

    def test_joint_matrix_preserves_source_discrepancy(self):
        matrix = self.query(dataset="matrix", category="Pedestrians")
        users = self.query(dataset="users", category="Pedestrians")
        self.assertEqual(matrix["summary"]["fatalities"], 35203)
        self.assertEqual(users["summary"]["fatalities"], 35221)
        self.assertEqual(len(matrix["matrix"]), 8)

    def test_demographics_reconcile_independently(self):
        r = self.query(dataset="demographics")
        self.assertEqual(r["summary"]["fatalities"], 172890)
        self.assertEqual(r["coverage"]["expected_observations"], 504)
        r = self.query(dataset="demographics", category="Under 18")
        self.assertEqual(r["summary"]["fatalities"], 7392 + 2097)

    def test_risk_union_and_intersection_order(self):
        r = self.query()
        self.assertEqual(len(r["risk"]), 17)
        self.assertEqual(r["risk"][0]["state"], "Uttar Pradesh")
        self.assertIn("Kerala", [v["state"] for v in r["risk"]])
        self.assertTrue(
            r["risk"][0]["high_accidents"] and r["risk"][0]["high_severity"]
        )
        r = self.query(threshold=1000)
        self.assertFalse(any(v["high_severity"] for v in r["risk"]))

    def test_state_year_and_category_intersect(self):
        r = self.query(states=["Kerala", "Tamil Nadu"])
        self.assertEqual(r["summary"]["fatalities"], 22427)
        r = self.query(
            dataset="users", states=["Kerala"], years=[2022], category="Two-wheelers"
        )
        self.assertEqual(r["summary"]["fatalities"], 2424)

    def test_missing_period_and_explicit_zero_stay_distinct(self):
        r = self.query(dataset="hours", years=[2024], metric="accidents")
        self.assertEqual(r["coverage"]["status"], "unavailable")
        self.assertIsNone(r["summary"]["value"])
        self.assertEqual(r["states"], [])
        r = self.query(dataset="totals", states=["Lakshadweep"])
        self.assertEqual(r["summary"]["accidents"], 1)
        self.assertIsNone(r["summary"]["fatalities"])
        r = self.query(dataset="users", states=["Lakshadweep"])
        self.assertEqual(r["summary"]["fatalities"], 0)

    def test_filtered_export_uses_same_query_and_snapshot(self):
        q = {"states": ["Kerala"], "years": [2024]}
        r = self.query(**q)
        d = self.client.post("/api/export", json=q)
        data = list(csv.DictReader(io.StringIO(d.text)))
        self.assertEqual(len(data), 1)
        self.assertEqual(int(data[0]["fatalities"]), r["summary"]["fatalities"])
        self.assertEqual(d.headers["X-RoadLens-Snapshot"], r["snapshot"])

    def test_real_pdf_is_generated(self):
        r = self.client.post(
            "/api/report", json={"states": ["Kerala"], "years": [2023]}
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF-"))
        self.assertTrue(r.content.rstrip().endswith(b"%%EOF"))

    def test_no_cross_fact_join_amplification(self):
        r = self.query(years=[2020, 2021, 2022, 2023, 2024], metric="accidents")
        self.assertEqual(
            r["summary"]["value"], sum([372181, 412432, 461312, 480583, 487707])
        )
        self.assertEqual(r["summary"]["observations"], 180)

    def test_junction_subuniverse_is_explicit(self):
        r = self.query(dataset="junctions")
        self.assertEqual(r["summary"]["value"], 34354)
        self.assertIn("not the all-road", r["dataset"]["note"])

    def test_all_prepared_datasets_have_finite_outputs_for_supported_measures(self):
        cat = self.client.get("/api/catalog").json()
        self.assertEqual(len(cat["datasets"]), 17)
        for key, meta in cat["datasets"].items():
            for metric in meta["metrics"] + (
                ["severity"] if meta["severity_supported"] else []
            ):
                with self.subTest(dataset=key, metric=metric):
                    r = self.query(dataset=key, metric=metric, years=meta["years"])
                    self.assertTrue(
                        r["summary"]["value"] is None
                        or math.isfinite(r["summary"]["value"])
                    )
                    self.assertNotEqual(r["coverage"]["status"], "unavailable")

    def test_animation_scale_is_stable_across_single_years(self):
        a = self.query(years=[2022])
        b = self.query(years=[2023])
        self.assertEqual(a["map_scale"], b["map_scale"])
        self.assertEqual(a["trend_scale"], b["trend_scale"])

    def test_minimum_denominator_and_top_n_are_explicit(self):
        r = self.query(min_accidents=500)
        self.assertTrue(
            all(
                not s["high_severity"] or s["paired_accidents"] >= 500
                for s in r["risk"]
            )
        )
        for n in [5, 10, 15]:
            r = self.query(top_n=n, metric="injuries")
            self.assertEqual(sum(s["high_accidents"] for s in r["risk"]), n)
        self.assertEqual(
            self.client.post("/api/query", json={"min_accidents": -1}).status_code, 422
        )

    def test_snapshot_health_and_built_frontend(self):
        self.assertEqual(self.client.get("/health").json()["status"], "ok")
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("RoadLens", r.text)


if __name__ == "__main__":
    unittest.main()
