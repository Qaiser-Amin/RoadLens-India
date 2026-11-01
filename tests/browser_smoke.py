"""Actual production-web journeys; no Tableau interaction claims.

Install Python Playwright and browsers, start server.py, then run this script.
Use --browser chromium|firefox|webkit and --url for an alternate local test port.
"""

import argparse
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

p = argparse.ArgumentParser()
p.add_argument(
    "--browser", choices=["chromium", "firefox", "webkit"], default="chromium"
)
p.add_argument("--url", default="http://127.0.0.1:8000")
args = p.parse_args()
with sync_playwright() as pw:
    browser = getattr(pw, args.browser).launch(
        headless=True,
        timeout=45000,
        **({"args": ["--no-sandbox"]} if args.browser == "chromium" else {}),
    )
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    def ready(dataset=None):
        selector = ".results[aria-busy=false]" + (
            f'[data-dataset="{dataset}"]' if dataset else ""
        )
        page.wait_for_selector(selector)

    def change(fn, dataset=None):
        with page.expect_response(
            lambda r: r.url.endswith("/api/query") and r.request.method == "POST"
        ) as response:
            fn()
        assert response.value.status == 200, response.value.text()
        ready(dataset)

    def nav(name):
        change(lambda: page.click("[data-tab=" + name + "]"))

    def number(metric):
        return page.locator(f'[data-kpi="{metric}"] strong').inner_text()

    page.goto(args.url)
    ready("totals")
    print("Loaded dashboard", args.browser, flush=True)
    assert number("accidents") == "4,80,583"
    assert number("fatalities") == "1,72,890"
    assert number("injuries") == "4,62,825"
    page.locator('[data-map-state="Kerala"]').focus()
    assert page.get_by_role("tooltip").is_visible()
    change(lambda: page.keyboard.press("Enter"), "totals")
    assert number("fatalities") == "4,080"
    assert (
        page.evaluate('document.activeElement.getAttribute("data-map-state")')
        == "Kerala"
    )
    change(lambda: page.click("#reset"), "totals")
    for n in [5, 15, 10]:
        change(lambda n=n: page.select_option("#topN", str(n)))
        panel = page.locator(".panel").filter(
            has=page.get_by_role("heading", name=f"Top {n} states & UTs", exact=True)
        )
        assert panel.locator("tbody tr").count() == n
    page.get_by_role("button", name="Motion on", exact=True).click()
    page.get_by_role("button", name="Motion off", exact=True).click()
    page.get_by_role("button", name="▷ Play years", exact=True).click()
    expect(page.get_by_role("button", name="Ⅱ Pause", exact=True)).to_be_visible()
    with page.expect_response(
        lambda r: r.url.endswith("/api/query") and r.request.method == "POST"
    ):
        pass
    ready()
    expect(page.locator(".results")).to_have_attribute("data-years", "2024")
    # Playback stops at the final prepared year.
    expect(page.get_by_role("button", name="▷ Play years", exact=True)).to_be_visible()
    change(lambda: page.select_option("#year", "2023"))
    change(lambda: page.select_option("#year", "2024"))
    assert number("accidents") == "4,87,707"
    assert number("fatalities") == "1,77,175"
    nav("types")
    assert page.locator(".notice").count() > 0
    change(
        lambda: page.get_by_role(
            "button", name="Use latest prepared year (2023)", exact=True
        ).click(),
        "collisions",
    )
    change(lambda: page.select_option("#metric", "accidents"))
    change(
        lambda: page.get_by_label("Category", exact=True).select_option(
            "Head-on collision"
        )
    )
    assert number("accidents") == "84,348"
    nav("users")
    change(
        lambda: page.get_by_role("button", name="Use Fatalities", exact=True).click(),
        "users",
    )
    change(
        lambda: page.get_by_label("Category", exact=True).select_option("Two-wheelers")
    )
    assert number("fatalities") == "77,539"
    assert number("accidents") == "Unavailable"
    change(lambda: page.select_option("#metric", "severity"))
    assert page.locator(".notice").count() > 0
    change(lambda: page.select_option("#metric", "fatalities"))
    change(
        lambda: page.get_by_role(
            "button", name="Reported impacting vehicles / objects", exact=True
        ).click(),
        "vehicles",
    )
    assert "severity is disabled" in page.locator(".results").inner_text().lower()
    change(
        lambda: page.get_by_role(
            "button", name="Victim / impacting-vehicle matrix", exact=True
        ).click(),
        "matrix",
    )
    assert page.locator(".chart svg").count() > 0
    change(
        lambda: page.get_by_role(
            "button", name="Victim age and reported sex", exact=True
        ).click(),
        "demographics",
    )
    assert number("fatalities") == "1,72,890"
    nav("conditions")
    for label, key in [
        ("Weather conditions", "weather"),
        ("Road features", "features"),
        ("Junction types", "junctions"),
        ("Traffic controls", "controls"),
        ("Road environment", "environment"),
    ]:
        change(
            lambda label=label: page.get_by_role(
                "button", name=label, exact=True
            ).click(),
            key,
        )
    nav("when")
    assert number("fatalities") == "1,72,890"
    change(lambda: page.select_option("#year", "custom"))
    change(lambda: page.get_by_label("From year", exact=True).select_option("2022"))
    ready()
    assert page.locator(".results").get_attribute("data-years") == "2022,2023,2024"
    page.reload()
    ready()
    assert page.get_by_label("From year", exact=True).input_value() == "2022"
    assert page.locator(".results").get_attribute("data-years") == "2022,2023,2024"
    change(
        lambda: page.get_by_role(
            "button", name="Time of occurrence", exact=True
        ).click(),
        "hours",
    )
    change(lambda: page.select_option("#metric", "accidents"))
    assert number("accidents") == "4,80,583"
    assert (
        "No prepared detail for 2022, 2024" in page.locator(".notice").last.inner_text()
    )
    change(lambda: page.click("#reset"), "totals")
    nav("priorities")
    change(lambda: page.select_option("#minimum", "500"))
    assert "minimum 500 accidents" in page.locator("main").inner_text()
    change(lambda: page.select_option("#minimum", "0"))
    assert page.locator(".risk-table tbody tr").count() == 17
    assert "Uttar Pradesh" in page.locator(".risk-table tbody tr").first.inner_text()
    assert (
        page.locator(".risk-table")
        .get_by_role("button", name="Kerala", exact=True)
        .count()
        == 1
    )
    page.fill("#threshold", "-1")
    page.locator("#threshold").press("Tab")
    expect(page.locator("#threshold-error")).to_be_visible()
    assert page.locator(".risk-table tbody tr").count() == 17
    assert "Results still use 50" in page.locator("#threshold-error").inner_text()
    page.get_by_role("button", name="Restore 50", exact=True).click()
    assert page.locator("#threshold").input_value() == "50"
    page.fill("#threshold", "0")
    change(lambda: page.locator("#threshold").press("Tab"))
    assert page.locator(".risk-table tbody tr").count() == 35
    page.reload()
    ready("totals")
    assert page.locator("#threshold").input_value() == "0"
    change(lambda: page.click("#reset"), "totals")
    page.locator(".state-picker summary").click()
    change(lambda: page.locator('[data-state-check="Kerala"]').check())
    change(lambda: page.locator('[data-state-check="Tamil Nadu"]').check())
    page.locator(".state-picker summary").click()
    assert number("fatalities") == "22,427"
    change(lambda: page.select_option("#year", "all"))
    assert page.locator(".chart svg").count() > 0
    change(lambda: page.click("#reset"))
    for kind, label, extension in [
        ("export", "↓ Filtered CSV", "csv"),
        ("report", "↗ Evidence PDF", "pdf"),
    ]:
        with page.expect_download() as item:
            page.get_by_role("button", name=label, exact=True).click()
        d = item.value
        assert d.suggested_filename.endswith("." + extension)
        payload = Path(d.path()).read_bytes()
        if kind == "report":
            assert payload.startswith(b"%PDF-")
        else:
            assert len(payload.decode().strip().splitlines()) == 37
    nav("evidence")
    assert "discrepancies" in page.locator("main").inner_text().lower()
    assert "35,221" in page.locator("main").inner_text()
    for width in [320, 390, 768, 1366, 1440]:
        page.set_viewport_size({"width": width, "height": 850})
        nav("overview")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            width
        )
        nav("priorities")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            width
        )
    page.emulate_media(reduced_motion="reduce")
    expect(
        page.get_by_role("button", name="Reduced motion", exact=True)
    ).to_be_disabled()
    expect(page.get_by_role("button", name="▷ Play years", exact=True)).to_be_disabled()
    page.emulate_media(reduced_motion="no-preference")
    change(lambda: page.click("#reset"))
    page.select_option("#year", "2022")
    page.select_option("#year", "2024")
    page.select_option("#year", "2023")
    ready()
    expect(page.locator(".results")).to_have_attribute("data-years", "2023")
    expect(page.locator('[data-kpi="fatalities"] strong')).to_have_text("1,72,890")
    page.route("**/api/query", lambda route: route.abort())
    page.select_option("#year", "2024")
    expect(page.get_by_role("alert")).to_be_visible()
    page.unroute("**/api/query")
    change(lambda: page.get_by_role("button", name="Retry", exact=True).click())
    assert number("fatalities") == "1,77,175"
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(args.url + "/?page=users&dataset=matrix")
    ready("matrix")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator(".heatmap-scroll .chart").bounding_box()["width"] >= 760
    assert "999999999" not in page.locator(".chart").last.inner_text()
    # Malformed shared state lists must not create duplicate ECharts series ids.
    page.goto(args.url + "/?page=priorities&states=Kerala%7CKerala%7CUnknown")
    ready("totals")
    assert number("fatalities") == "4,080"
    assert page.locator(".state-picker summary").inner_text() == "Kerala"
    change(lambda: page.click("#reset"))
    # Rendering captures are QA evidence, not application content.
    page.wait_for_timeout(400)
    page.screenshot(
        path=str(Path(tempfile.gettempdir()) / f"roadlens-v2-{args.browser}.png"),
        full_page=True,
    )
    assert not errors, errors
    browser.close()
    print(
        "PASS",
        args.browser,
        ": seven dashboards, categories, real 2024 totals, filters/ranges, keyboard focus/tooltips, risk, validation, reset/deep links, exports, error recovery, reduced motion and five viewport widths; no JS errors.",
    )
