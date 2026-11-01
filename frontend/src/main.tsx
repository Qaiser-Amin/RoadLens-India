import React, { useEffect, useState, useRef, useMemo } from "react";
import { createRoot } from "react-dom/client";
import * as echarts from "echarts/core";
import {
  BarChart,
  LineChart,
  ScatterChart,
  HeatmapChart,
} from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  AriaComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import "./style.css";
echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  AriaComponent,
  SVGRenderer,
]);
type Metric =
  "accidents" | "fatalities" | "injuries" | "fatal_crashes" | "severity";
type Page =
  | "overview"
  | "types"
  | "users"
  | "conditions"
  | "when"
  | "priorities"
  | "evidence";
type Row = {
  state?: string;
  category?: string;
  category2?: string;
  year?: number;
  ordinal?: number;
  value: number | null;
  accidents: number | null;
  fatalities: number | null;
  injuries: number | null;
  fatal_crashes: number | null;
  severity: number | null;
  observations: number;
  pairs: number;
  [k: string]: any;
};
type Dataset = {
  id: string;
  title: string;
  definition: string;
  metrics: Metric[];
  grain: string;
  note: string;
  pages: number[];
  years: number[];
  categories: string[];
  rows: number;
  severity_supported: boolean;
  url: string;
  source_ids: string[];
};
type Catalog = {
  datasets: Record<string, Dataset>;
  states: string[];
  years: number[];
  sources: any[];
  checks: any[];
  caveats: string[];
  snapshot: string;
  latest_year: number;
};
type Query = {
  dataset: string;
  years: number[];
  states: string[];
  category: string | null;
  metric: Metric;
  top_n: number;
  min_accidents: number;
  threshold: number;
};
type Result = {
  map_scale: number;
  trend_scale: number;
  query: Query;
  dataset: Dataset;
  summary: Row;
  states: Row[];
  categories: Row[];
  trend: Row[];
  series: Row[];
  matrix: Row[];
  risk: Row[];
  coverage: {
    status: string;
    expected_observations: number;
    available_observations: number;
    observed_years: number[];
    unprepared_years: number[];
  };
  change_pct: number | null;
  snapshot: string;
};
const metricNames: Record<Metric, string> = {
  accidents: "Accidents",
  fatalities: "Fatalities",
  injuries: "People injured",
  fatal_crashes: "Fatal crashes",
  severity: "Deaths / 100 accidents",
};
const pages: Record<
  Page,
  {
    label: string;
    title: string;
    description: string;
    icon: string;
    datasets: string[];
  }
> = {
  overview: {
    label: "National overview",
    title: "Every journey deserves a safer road.",
    description: "The national picture, grounded in reported evidence.",
    icon: "◈",
    datasets: ["totals"],
  },
  types: {
    label: "Accident types",
    title: "Understand how accidents happen.",
    description: "Compare collision mechanisms and crash injury outcomes.",
    icon: "◇",
    datasets: ["collisions", "outcomes"],
  },
  users: {
    label: "Vehicles & road users",
    title: "Every road user counts.",
    description:
      "Explore all reported categories, with distinct victim and impacting-vehicle definitions.",
    icon: "◎",
    datasets: ["users", "vehicles", "matrix", "demographics"],
  },
  conditions: {
    label: "Causes & conditions",
    title: "Look beyond the headline numbers.",
    description:
      "Reported violations, weather and road context — each at its own reporting grain.",
    icon: "△",
    datasets: [
      "violations",
      "weather",
      "features",
      "junctions",
      "controls",
      "environment",
    ],
  },
  when: {
    label: "When & where",
    title: "Find the patterns in time and place.",
    description:
      "Monthly cycles, reported time bands, road classes and urban/rural differences.",
    icon: "◷",
    datasets: ["months", "hours", "urban", "roads"],
  },
  priorities: {
    label: "Compare & prioritize",
    title: "Turn evidence into better questions.",
    description:
      "Compare states and inspect transparent accident-burden and severity criteria.",
    icon: "↗",
    datasets: ["totals"],
  },
  evidence: {
    label: "Evidence & quality",
    title: "Trust begins with transparency.",
    description:
      "Inspect coverage, source provenance, known discrepancies and reporting definitions.",
    icon: "▤",
    datasets: ["totals"],
  },
};
const colors = ["#087e75", "#dc8a5e", "#5b76b7", "#987197", "#858b49"];
const fmt = (v: number | null | undefined, m: Metric = "accidents") =>
  v === null || v === undefined
    ? "Unavailable"
    : new Intl.NumberFormat("en-IN", {
        maximumFractionDigits: m === "severity" ? 1 : 0,
        minimumFractionDigits: m === "severity" ? 1 : 0,
      }).format(v);
const initial = new URLSearchParams(location.search);
const safeNumber = (key: string, fallback: number, maximum = 1000) => {
  const raw = initial.get(key);
  const n = raw === null ? fallback : Number(raw);
  return Number.isFinite(n) && n >= 0 && n <= maximum ? n : fallback;
};
const initPage = (
  Object.keys(pages).includes(initial.get("page") || "")
    ? initial.get("page")
    : "overview"
) as Page;
function Chart({
  option,
  title,
  motion,
  onClick,
}: {
  option: any;
  title: string;
  motion: boolean;
  onClick?: (name: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.EChartsType | null>(null);
  const callback = useRef(onClick);
  callback.current = onClick;
  useEffect(() => {
    if (!ref.current) return;
    const c = echarts.init(ref.current, undefined, { renderer: "svg" });
    chart.current = c;
    c.on("click", (e: any) => callback.current?.(e.name));
    const resize = new ResizeObserver(() => c.resize());
    resize.observe(ref.current);
    return () => {
      resize.disconnect();
      c.dispose();
      chart.current = null;
    };
  }, []);
  useEffect(() => {
    chart.current?.setOption(
      {
        ...option,
        aria: { enabled: true, description: title },
        animation: motion,
        animationDuration: 350,
        animationDurationUpdate: 300,
        textStyle: { fontFamily: "system-ui", color: "#28443d", fontSize: 11 },
      },
      true,
    );
  }, [option, motion, title]);
  return <div ref={ref} className="chart" role="img" aria-label={title} />;
}
function DataTable({
  rows,
  metric,
  label = "View data",
  onState,
}: {
  rows: Row[];
  metric: Metric;
  label?: string;
  onState?: (s: string) => void;
}) {
  return (
    <details className="data-table">
      <summary>
        {label} <span>↗</span>
      </summary>
      <div
        className="table-scroll"
        role="region"
        aria-label={label}
        tabIndex={0}
      >
        <table>
          <thead>
            <tr>
              <th>State / category / year</th>
              <th>{metricNames[metric]}</th>
              <th>Accidents</th>
              <th>Fatalities</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={[r.state, r.category, r.category2, r.year, i].join("-")}>
                <td>
                  {onState && r.state ? (
                    <button className="link" onClick={() => onState(r.state!)}>
                      {r.state}
                    </button>
                  ) : (
                    [r.state, r.category, r.category2, r.year]
                      .filter(Boolean)
                      .join(" · ")
                  )}
                </td>
                <td>{fmt(r.value, metric)}</td>
                <td>{fmt(r.accidents)}</td>
                <td>{fmt(r.fatalities)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && (
          <p className="empty">
            No reported observations match this selection.
          </p>
        )}
      </div>
    </details>
  );
}
function Panel({
  title,
  subtitle,
  children,
  wide = false,
  tag,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  wide?: boolean;
  tag?: string;
}) {
  return (
    <section className={"panel " + (wide ? "wide" : "")}>
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {tag && <span className="tag">{tag}</span>}
      </div>
      {children}
    </section>
  );
}
function StateMap({
  geo,
  rows,
  metric,
  onSelect,
  scale,
}: {
  geo: any;
  rows: Row[];
  metric: Metric;
  scale: number;
  onSelect: (s: string) => void;
}) {
  const [tip, setTip] = useState<{ name: string; x: number; y: number } | null>(
    null,
  );
  const paths = useMemo(
    () =>
      geo.features.map((f: any) => {
        const point = ([lon, lat]: number[]) => [
          30 + (lon - 67) * 11.5,
          405 - (lat - 6) * 12.4,
        ];
        const ring = (c: number[][]) =>
          c
            .map(
              (p, i) =>
                `${i ? "L" : "M"}${point(p)
                  .map((v) => v.toFixed(2))
                  .join(",")}`,
            )
            .join("") + "Z";
        const polys =
          f.geometry.type === "Polygon"
            ? [f.geometry.coordinates]
            : f.geometry.coordinates;
        return {
          name: f.properties.name,
          path: polys.map((p: number[][][]) => p.map(ring).join("")).join(""),
        };
      }),
    [geo],
  );
  const max = scale,
    lookup = new Map(rows.map((r) => [r.state, r]));
  return (
    <>
      <svg
        className="india-map"
        viewBox="0 0 450 430"
        role="group"
        aria-label="India state selection map"
      >
        {paths.map((f: any) => {
          const r = lookup.get(f.name),
            value = r?.value;
          const t = value == null ? null : Math.min(value / max, 1);
          const fill =
            t === null
              ? "#e4e8e6"
              : `rgb(${Math.round(225 - 216 * t)},${Math.round(241 - 116 * t)},${Math.round(234 - 117 * t)})`;
          return (
            <path
              key={f.name}
              d={f.path}
              fill={fill}
              fillRule="evenodd"
              tabIndex={0}
              role="button"
              data-map-state={f.name}
              aria-label={`${f.name}: ${metricNames[metric]} ${fmt(value, metric)}. Select state.`}
              onClick={() => onSelect(f.name)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(f.name);
                }
              }}
              onFocus={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                setTip({
                  name: f.name,
                  x: Math.min(rect.x + rect.width / 2, window.innerWidth - 260),
                  y: Math.min(rect.y + rect.height, window.innerHeight - 180),
                });
              }}
              onBlur={() => setTip(null)}
              onPointerMove={(e) =>
                setTip({
                  name: f.name,
                  x: Math.max(
                    8,
                    Math.min(e.clientX + 12, window.innerWidth - 260),
                  ),
                  y: Math.max(
                    8,
                    Math.min(e.clientY + 12, window.innerHeight - 180),
                  ),
                })
              }
              onPointerLeave={() => setTip(null)}
            >
              <title>
                {f.name}: {fmt(value, metric)}
              </title>
            </path>
          );
        })}
      </svg>
      <div className="legend">
        <span>Lower</span>
        <i />
        <span>Higher · {metricNames[metric]}</span>
        <span>Gray: unavailable · scale: 0–{fmt(max, metric)}</span>
      </div>
      <p className="footnote">
        Select a state or press Enter on a focused mark. Illustrative current
        boundaries; coverage follows reported tables.
      </p>
      {tip && (
        <div
          id="map-tooltip"
          className="map-tooltip"
          role="tooltip"
          style={{ left: tip.x, top: tip.y }}
        >
          <strong>{tip.name}</strong>
          <div>
            {metricNames[metric]}: {fmt(lookup.get(tip.name)?.value, metric)}
          </div>
          <div>Accidents: {fmt(lookup.get(tip.name)?.accidents)}</div>
          <div>Fatalities: {fmt(lookup.get(tip.name)?.fatalities)}</div>
          <div>
            Deaths / 100 accidents:{" "}
            {fmt(lookup.get(tip.name)?.severity, "severity")}
          </div>
        </div>
      )}
    </>
  );
}
function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null),
    [geo, setGeo] = useState<any>(null),
    [page, setPage] = useState<Page>(initPage),
    [dataset, setDataset] = useState(
      initial.get("dataset") || pages[initPage].datasets[0],
    );
  const [year, setYear] = useState(initial.get("year") || "2023"),
    [states, setStates] = useState<string[]>(
      initial.get("states")?.split("|").filter(Boolean) || [],
    ),
    [metric, setMetric] = useState<Metric>(
      (initial.get("metric") || "fatalities") as Metric,
    ),
    [topN, setTopN] = useState(Number(initial.get("topN")) || 10),
    [category, setCategory] = useState<string | null>(initial.get("category")),
    [threshold, setThreshold] = useState(safeNumber("threshold", 50)),
    [minimum, setMinimum] = useState(safeNumber("minimum", 0, 1000000)),
    [thresholdInput, setThresholdInput] = useState(
      String(safeNumber("threshold", 50)),
    ),
    [thresholdError, setThresholdError] = useState("");
  const [result, setResult] = useState<Result | null>(null),
    [busy, setBusy] = useState(true),
    [error, setError] = useState(""),
    [search, setSearch] = useState(""),
    [retry, setRetry] = useState(0),
    [playing, setPlaying] = useState(false),
    [motion, setMotion] = useState(true),
    [reduced, setReduced] = useState(
      matchMedia("(prefers-reduced-motion: reduce)").matches,
    ),
    [exporting, setExporting] = useState(false);
  const [fromYear, setFromYear] = useState(safeNumber("from", 2020, 2100)),
    [toYear, setToYear] = useState(safeNumber("to", 2024, 2100));
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const listener = () => setReduced(media.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);
  useEffect(() => {
    Promise.all([
      fetch("/api/catalog").then((r) => {
        if (!r.ok) throw Error("Data catalog unavailable");
        return r.json();
      }),
      fetch("/assets/india-states.geojson").then((r) => r.json()),
    ])
      .then(([c, g]) => {
        setCatalog(c);
        setGeo(g);
        if (!c.datasets[dataset] || !pages[page].datasets.includes(dataset))
          setDataset(pages[page].datasets[0]);
        if (
          year !== "all" &&
          year !== "custom" &&
          !c.years.includes(Number(year))
        )
          setYear("2023");
        setStates((s) =>
          [...new Set(s.filter((x) => c.states.includes(x)))].slice(0, 5),
        );
        if (!c.years.includes(fromYear)) setFromYear(c.years[0]);
        if (!c.years.includes(toYear) || fromYear > toYear)
          setToYear(c.years.at(-1));
        if (![0, 100, 500, 1000].includes(minimum)) setMinimum(0);
        if (!Object.keys(metricNames).includes(metric)) setMetric("fatalities");
        if (![5, 10, 15].includes(topN)) setTopN(10);
      })
      .catch((e) => {
        setError(e.message);
        setBusy(false);
      });
  }, [retry]);
  const query = useMemo<Query | null>(
    () =>
      catalog
        ? {
            dataset,
            years:
              year === "all"
                ? catalog.years
                : year === "custom"
                  ? catalog.years.filter((y) => y >= fromYear && y <= toYear)
                  : [Number(year)],
            states,
            category,
            metric,
            top_n: topN,
            min_accidents: minimum,
            threshold,
          }
        : null,
    [
      catalog,
      dataset,
      year,
      states,
      category,
      metric,
      topN,
      minimum,
      threshold,
      fromYear,
      toYear,
    ],
  );
  useEffect(() => {
    if (!query) return;
    controller.current?.abort();
    const c = new AbortController();
    controller.current = c;
    setBusy(true);
    setError("");
    fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(query),
      signal: c.signal,
    })
      .then(async (r) => {
        if (!r.ok)
          throw Error(
            "The selection could not be analyzed. Check the filters or reset.",
          );
        return r.json();
      })
      .then((r) => {
        setResult(r);
        setBusy(false);
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setError(e.message);
          setBusy(false);
        }
      });
    const url = new URLSearchParams({
      page,
      dataset,
      year,
      metric,
      topN: String(topN),
      threshold: String(threshold),
      minimum: String(minimum),
    });
    if (year === "custom") {
      url.set("from", String(fromYear));
      url.set("to", String(toYear));
    }
    if (states.length) url.set("states", states.join("|"));
    if (category) url.set("category", category);
    history.replaceState(null, "", "?" + url);
    return () => c.abort();
  }, [query, page]);
  useEffect(() => {
    if (!playing || !catalog) return;
    const years = catalog.datasets[dataset].years;
    const i = years.indexOf(Number(year));
    const timer = setTimeout(() => {
      if (i === years.length - 1) setPlaying(false);
      else setYear(String(years[i + 1] || years[0]));
    }, 1100);
    return () => clearTimeout(timer);
  }, [playing, year, catalog, dataset]);
  useEffect(() => {
    if (reduced) setPlaying(false);
  }, [reduced]);
  function nav(next: Page) {
    setPage(next);
    setDataset(pages[next].datasets[0]);
    setCategory(null);
    setResult(null);
    setPlaying(false);
  }
  function chooseDataset(next: string) {
    setDataset(next);
    setCategory(null);
    setResult(null);
    setPlaying(false);
  }
  function reset() {
    setPage("overview");
    setDataset("totals");
    setYear("2023");
    setStates([]);
    setMetric("fatalities");
    setTopN(10);
    setCategory(null);
    setThreshold(50);
    setMinimum(0);
    setThresholdInput("50");
    setThresholdError("");
    setSearch("");
    setPlaying(false);
    setFromYear(2020);
    setToYear(2024);
  }
  function selectState(s: string) {
    setStates((old) => (old.length === 1 && old[0] === s ? [] : [s]));
  }
  async function download(kind: "export" | "report") {
    if (!result || busy) return;
    setExporting(true);
    try {
      const r = await fetch("/api/" + kind, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result.query),
      });
      if (!r.ok) throw Error("Export failed; please retry.");
      const blob = await r.blob(),
        a = document.createElement("a"),
        url = URL.createObjectURL(blob);
      a.href = url;
      a.download = `roadlens-${dataset}-${kind === "report" ? "evidence.pdf" : "filtered.csv"}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setExporting(false);
    }
  }
  const active = pages[page],
    meta = catalog?.datasets[dataset];
  const scope = result
    ? `${result.query.years.join(", ")} · ${result.query.states.length ? result.query.states.join(", ") : "All states & UTs"} · ${metricNames[result.query.metric]}`
    : "";
  const activeMetric = result?.query.metric || metric;
  const units =
    activeMetric === "severity"
      ? "Deaths per 100 compatible accidents"
      : metricNames[activeMetric];
  function bars(rows: Row[], key: "state" | "category", limit = 20) {
    const shown = rows.filter((r) => r.value !== null).slice(0, limit);
    const option = {
      grid: { left: 5, right: 55, top: 12, bottom: 20, containLabel: true },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      xAxis: { type: "value", splitLine: { lineStyle: { color: "#edf1ee" } } },
      yAxis: {
        type: "category",
        inverse: true,
        data: shown.map((r) => r[key]),
        axisLabel: { width: 150, overflow: "truncate" },
        axisTick: { show: false },
        axisLine: { show: false },
      },
      series: [
        {
          type: "bar",
          id: "values",
          data: shown.map((r, i) => ({
            name: r[key],
            value: r.value,
            itemStyle: {
              color: i === 0 ? "#d18b61" : "#107f72",
              borderRadius: [0, 4, 4, 0],
            },
          })),
          label: {
            show: true,
            position: "right",
            formatter: (p: any) => fmt(p.value, activeMetric),
          },
          barMaxWidth: 20,
        },
      ],
    };
    return (
      <>
        {shown.length ? (
          <Chart
            option={option}
            title={`${units} by ${key}`}
            motion={motion && !reduced}
            onClick={(s) =>
              key === "state"
                ? selectState(s)
                : setCategory((old) => (old === s ? null : s))
            }
          />
        ) : (
          <p className="empty">
            This measure is unavailable for the selected reporting slice.
          </p>
        )}
        <DataTable
          rows={shown}
          metric={activeMetric}
          onState={key === "state" ? selectState : undefined}
        />
      </>
    );
  }
  function trend() {
    if (!result) return null;
    const years = result.query.years;
    const compare = result.query.states.length > 0;
    const labels = compare ? result.query.states : ["Reported total"];
    const series = labels.map((name, i) => ({
      name,
      type: "line",
      id: name,
      connectNulls: false,
      symbolSize: 7,
      lineStyle: { width: 3 },
      itemStyle: { color: colors[i % colors.length] },
      data: years.map(
        (y) =>
          (compare
            ? result.series.find((r) => r.state === name && r.year === y)
            : result.trend.find((r) => r.year === y)
          )?.value ?? null,
      ),
    }));
    return (
      <>
        <Chart
          title={`${units} by reporting year`}
          motion={motion && !reduced}
          option={{
            grid: { left: 65, right: 20, bottom: 35, top: 40 },
            tooltip: { trigger: "axis" },
            legend: { top: 0, type: "scroll" },
            xAxis: { type: "category", data: years },
            yAxis: { type: "value", max: result.trend_scale * 1.15 },
            series,
          }}
        />
        <p className="footnote">
          {years.length === 1
            ? "One year is selected. Choose All years to explore the reporting history."
            : "Missing periods remain gaps. All-year KPI counts are cumulative; the lines show annual observations."}
        </p>
        <DataTable
          rows={result.query.states.length ? result.series : result.trend}
          metric={activeMetric}
        />
      </>
    );
  }
  function categoryChart() {
    if (!result) return null;
    if (
      dataset === "matrix" ||
      dataset === "demographics" ||
      dataset === "hours"
    )
      return heatmap();
    if (dataset === "months") {
      const list = [...result.categories].sort(
        (a, b) => Number(a.ordinal) - Number(b.ordinal),
      );
      return (
        <>
          <Chart
            title={`${units} by month`}
            motion={motion && !reduced}
            option={{
              grid: { left: 65, right: 20, top: 20, bottom: 55 },
              tooltip: { trigger: "axis" },
              xAxis: {
                type: "category",
                data: list.map((r) => r.category),
                axisLabel: { rotate: 30 },
              },
              yAxis: { type: "value" },
              series: [
                {
                  id: "months",
                  type: "line",
                  data: list.map((r) => r.value),
                  connectNulls: false,
                  symbolSize: 7,
                  lineStyle: { width: 3, color: "#087e75" },
                  itemStyle: { color: "#087e75" },
                },
              ],
            }}
          />
          <DataTable rows={list} metric={activeMetric} />
        </>
      );
    }
    return bars(result.categories, "category");
  }
  function heatmap() {
    if (!result) return null;
    const matrix = dataset === "matrix" || dataset === "demographics";
    const xs = matrix
      ? [...new Set(result.matrix.map((r) => r.category2))]
      : [...result.categories]
          .sort((a, b) => Number(a.ordinal) - Number(b.ordinal))
          .map((r) => r.category);
    const ys = matrix
      ? [...new Set(result.matrix.map((r) => r.category))]
      : [...new Set(result.matrix.map((r) => r.state))];
    const values = result.matrix
      .filter((r) => r.value !== null)
      .map((r) => [
        xs.indexOf(matrix ? r.category2 : r.category),
        ys.indexOf(matrix ? r.category : r.state),
        r.value,
      ]);
    const max = Math.max(...values.map((v) => Number(v[2])), 1);
    return (
      <>
        <div className={matrix ? "" : "tall-chart"}>
          <Chart
            title={
              dataset === "demographics"
                ? "Fatalities by reported age and sex"
                : matrix
                  ? "Joint victim and impacting-vehicle fatalities"
                  : "State by reported time-band accidents"
            }
            motion={motion && !reduced}
            option={{
              grid: { left: 145, right: 20, bottom: 85, top: 20 },
              tooltip: {
                position: "top",
                formatter: (p: any) =>
                  `${ys[p.value[1]]} / ${xs[p.value[0]]}: ${fmt(p.value[2], activeMetric)}`,
              },
              xAxis: {
                type: "category",
                data: xs,
                axisLabel: { rotate: 35, width: 95, overflow: "truncate" },
              },
              yAxis: {
                type: "category",
                data: ys,
                inverse: true,
                axisLabel: { width: 135, overflow: "truncate" },
              },
              visualMap: {
                min: 0,
                max,
                calculable: true,
                orient: "horizontal",
                left: "center",
                bottom: 0,
                inRange: { color: ["#edf5ef", "#69ada0", "#087568"] },
              },
              series: [
                {
                  type: "heatmap",
                  id: "matrix",
                  data: values,
                  label: {
                    show: matrix,
                    fontSize: 10,
                    formatter: (p: any) => fmt(p.value[2], activeMetric),
                  },
                },
              ],
            }}
          />
        </div>
        <DataTable
          rows={result.matrix}
          metric={activeMetric}
          label="View complete heatmap data"
        />
      </>
    );
  }
  const metricSupported =
    !!meta &&
    (meta.metrics.includes(metric) ||
      (metric === "severity" && meta.severity_supported));
  return (
    <>
      <header>
        <a className="brand" href="/" aria-label="RoadLens home">
          <span className="brand-icon">R↗</span>
          <span>
            RoadLens <em>INDIA</em>
            <small>ROAD SAFETY OBSERVATORY</small>
          </span>
        </a>
        <span className="header-note">EVIDENCE FOR SAFER MOBILITY</span>
        <button className="source-badge" onClick={() => nav("evidence")}>
          <i /> Official MoRTH data
        </button>
      </header>
      <div className="shell">
        <aside>
          <span className="nav-label">EXPLORE THE EVIDENCE</span>
          <nav aria-label="Dashboards">
            {(Object.keys(pages) as Page[]).map((id) => (
              <button
                key={id}
                data-tab={id}
                className={page === id ? "active" : ""}
                aria-current={page === id ? "page" : undefined}
                onClick={() => nav(id)}
              >
                <span>{pages[id].icon}</span>
                {pages[id].label}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <small>THE INDIA PERSPECTIVE</small>
            <p>
              Better questions.
              <br />
              Safer journeys.
            </p>
            <span>
              36 reporting states & UTs
              <br />
              2020–2024 annual coverage
            </span>
            <button className="link" onClick={() => nav("evidence")}>
              Sources & methodology ↗
            </button>
          </div>
        </aside>
        <main>
          <div className="eyebrow">
            INDIAN ROAD SAFETY / {active.label.toUpperCase()}
          </div>
          <div className="page-head">
            <div>
              <h1>{active.title}</h1>
              <p>{active.description}</p>
            </div>
            <div className="exports">
              <button
                disabled={!result || busy || exporting}
                onClick={() => download("export")}
              >
                ↓ Filtered CSV
              </button>
              <button
                disabled={!result || busy || exporting}
                onClick={() => download("report")}
              >
                ↗ Evidence PDF
              </button>
            </div>
          </div>
          <section className="filterbar" aria-label="Global filters">
            <label>
              REPORTING PERIOD
              <select
                id="year"
                value={year}
                onChange={(e) => {
                  setYear(e.target.value);
                  setPlaying(false);
                }}
              >
                {[...(catalog?.years || [2023])].reverse().map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
                <option value="all">All years · cumulative</option>
                <option value="custom">Custom range…</option>
              </select>
            </label>
            {year === "custom" && (
              <div className="range-picker">
                <label>
                  From
                  <select
                    aria-label="From year"
                    value={fromYear}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setFromYear(n);
                      if (n > toYear) setToYear(n);
                    }}
                  >
                    {catalog?.years.map((y) => (
                      <option key={y}>{y}</option>
                    ))}
                  </select>
                </label>
                <label>
                  To
                  <select
                    aria-label="To year"
                    value={toYear}
                    onChange={(e) => {
                      const n = Number(e.target.value);
                      setToYear(n);
                      if (n < fromYear) setFromYear(n);
                    }}
                  >
                    {catalog?.years.map((y) => (
                      <option key={y}>{y}</option>
                    ))}
                  </select>
                </label>
              </div>
            )}
            <details className="state-picker">
              <summary>
                {states.length === 0
                  ? "All states & UTs"
                  : states.length === 1
                    ? states[0]
                    : `${states.length} selected states`}
              </summary>
              <div className="state-options">
                <label>
                  Find a state
                  <input
                    aria-label="Find a state"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search states…"
                  />
                </label>
                <button className="link" onClick={() => setStates([])}>
                  Clear selection
                </button>
                <p>Choose up to 5 states to compare.</p>
                <div>
                  {catalog?.states
                    .filter((s) =>
                      s.toLowerCase().includes(search.toLowerCase()),
                    )
                    .map((s) => (
                      <label key={s}>
                        <input
                          type="checkbox"
                          data-state-check={s}
                          checked={states.includes(s)}
                          disabled={states.length >= 5 && !states.includes(s)}
                          onChange={(e) =>
                            setStates((old) =>
                              e.target.checked
                                ? [...old, s]
                                : old.filter((v) => v !== s),
                            )
                          }
                        />
                        {s}
                      </label>
                    ))}
                </div>
              </div>
            </details>
            <label>
              EXPLORE MEASURE
              <select
                id="metric"
                value={metric}
                onChange={(e) => setMetric(e.target.value as Metric)}
              >
                {(Object.keys(metricNames) as Metric[]).map((m) => (
                  <option key={m} value={m}>
                    {metricNames[m]}
                    {meta &&
                    !(
                      meta.metrics.includes(m) ||
                      (m === "severity" && meta.severity_supported)
                    )
                      ? " · unavailable"
                      : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              STATE RANKING
              <select
                id="topN"
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
              >
                {[5, 10, 15].map((n) => (
                  <option key={n} value={n}>
                    Top {n}
                  </option>
                ))}
              </select>
            </label>
            <button className="reset" id="reset" onClick={reset}>
              ↺ Reset filters
            </button>
          </section>
          <div className="utility">
            <span>
              {states.length ? states.join(" + ") : "All reporting states"} ·{" "}
              {year === "all"
                ? "Cumulative reporting period"
                : year === "custom"
                  ? `${fromYear}–${toYear}`
                  : year}
              {category && (
                <>
                  {" "}
                  ·{" "}
                  <button className="chip" onClick={() => setCategory(null)}>
                    {category} ×
                  </button>
                </>
              )}
            </span>
            <div>
              <span className="year-note">
                2024 totals available · 2023 detailed categories
              </span>
              <button
                className="link"
                disabled={reduced || !catalog}
                onClick={() => {
                  if (playing) {
                    setPlaying(false);
                  } else {
                    setYear(String(catalog!.datasets[dataset].years[0]));
                    setPlaying(true);
                  }
                }}
              >
                {playing ? "Ⅱ Pause" : "▷ Play years"}
              </button>
              <button
                className="link"
                onClick={() => setMotion(!motion)}
                disabled={reduced}
              >
                {reduced
                  ? "Reduced motion"
                  : motion
                    ? "Motion on"
                    : "Motion off"}
              </button>
            </div>
          </div>
          {active.datasets.length > 1 && (
            <div className="dataset-tabs" aria-label="Analysis dimension">
              {active.datasets.map((d) => (
                <button
                  key={d}
                  onClick={() => chooseDataset(d)}
                  className={dataset === d ? "active" : ""}
                >
                  {catalog?.datasets[d].title || d}
                </button>
              ))}
            </div>
          )}
          {meta && meta.categories.length > 1 && (
            <label className="category-select">
              Filter this dataset{" "}
              <select
                aria-label="Category"
                value={category || ""}
                onChange={(e) => setCategory(e.target.value || null)}
              >
                <option value="">All reported categories</option>
                {meta.categories.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
              <small>Applies only to {meta.title.toLowerCase()}.</small>
            </label>
          )}
          {meta && (
            <p className="definition">
              <b>{meta.title}.</b> {meta.definition}{" "}
              <span>Prepared years: {meta.years.join(", ")}.</span>
            </p>
          )}
          {error && (
            <div className="error" role="alert">
              {error}{" "}
              <button onClick={() => setRetry((r) => r + 1)}>Retry</button>
              <button onClick={reset}>Reset selection</button>
            </div>
          )}
          {(!catalog || (!result && !error)) && (
            <div className="loading" role="status">
              Loading verified reporting data…
            </div>
          )}
          {result && !error && (
            <div
              aria-busy={busy}
              className="results"
              data-dataset={result.query.dataset}
              data-years={result.query.years.join(",")}
              data-metric={result.query.metric}
              data-category={result.query.category || ""}
            >
              <div className="status-line" role="status">
                {busy
                  ? "Updating… previous results shown until the request completes."
                  : scope}
                <span className={"coverage " + result.coverage.status}>
                  {result.coverage.status} ·{" "}
                  {result.coverage.available_observations}/
                  {result.coverage.expected_observations} measure observations
                </span>
              </div>
              {result.coverage.status === "unavailable" && (
                <div className="notice" role="status">
                  {!metricSupported
                    ? "This measure has no compatible reporting definition or denominator for this dataset."
                    : "No prepared observations match this reporting slice."}{" "}
                  {result.dataset.years.length > 0 && (
                    <button
                      className="link"
                      onClick={() =>
                        setYear(
                          String(
                            result.dataset.years[
                              result.dataset.years.length - 1
                            ],
                          ),
                        )
                      }
                    >
                      Use latest prepared year ({result.dataset.years.at(-1)})
                    </button>
                  )}{" "}
                  {!metricSupported && (
                    <button
                      className="link"
                      onClick={() => setMetric(result.dataset.metrics[0])}
                    >
                      Use {metricNames[result.dataset.metrics[0]]}
                    </button>
                  )}
                </div>
              )}
              {result.coverage.unprepared_years.length > 0 && (
                <p className="notice">
                  No prepared detail for{" "}
                  {result.coverage.unprepared_years.join(", ")}. Those periods
                  are unavailable, not zero.
                </p>
              )}
              <section className="kpis" aria-label="Dynamic indicators">
                {(
                  [
                    "accidents",
                    "fatalities",
                    "injuries",
                    "fatal_crashes",
                  ] as Metric[]
                ).map((m, i) => (
                  <article className="kpi" key={m} data-kpi={m}>
                    <span className="kpi-symbol">
                      {["↗", "◎", "♡", "◇"][i]}
                    </span>
                    <span>{metricNames[m].toUpperCase()}</span>
                    <strong>{fmt(result.summary[m], m)}</strong>
                    <small>
                      {result.summary[m] === null
                        ? "Unavailable in this reporting definition"
                        : `${result.summary[m + "_count"]} reported observations`}
                    </small>
                  </article>
                ))}
              </section>
              <div className="analysis-note">
                <span>
                  <b>Severity:</b> {fmt(result.summary.severity, "severity")}{" "}
                  deaths / 100 compatible accidents
                </span>
                <span>
                  <b>Comparable annual change:</b>{" "}
                  {result.change_pct === null
                    ? "Unavailable / incomplete comparison"
                    : `${result.change_pct > 0 ? "+" : ""}${result.change_pct.toFixed(1)}%`}
                </span>
              </div>
              {page === "evidence" ? (
                <div className="grid">
                  <Panel
                    title="What is available?"
                    subtitle="Green indicates a prepared reporting period; gray is not prepared, not zero accidents."
                    wide
                  >
                    <Chart
                      title="Dataset reporting availability by year"
                      motion={motion && !reduced}
                      option={{
                        grid: { left: 200, right: 20, top: 15, bottom: 40 },
                        xAxis: { type: "category", data: catalog!.years },
                        yAxis: {
                          type: "category",
                          data: Object.values(catalog!.datasets).map(
                            (d) => d.title,
                          ),
                          axisLabel: { width: 180, overflow: "truncate" },
                          inverse: true,
                        },
                        tooltip: {
                          formatter: (p: any) =>
                            `${Object.values(catalog!.datasets)[p.value[1]].title} / ${catalog!.years[p.value[0]]}: ${p.value[2] ? "Prepared" : "Not prepared"}`,
                        },
                        visualMap: {
                          show: false,
                          min: 0,
                          max: 1,
                          inRange: { color: ["#e7ebe5", "#16806b"] },
                        },
                        series: [
                          {
                            type: "heatmap",
                            data: Object.values(catalog!.datasets).flatMap(
                              (d, i) =>
                                catalog!.years.map((y, j) => [
                                  j,
                                  i,
                                  d.years.includes(y) ? 1 : 0,
                                ]),
                            ),
                          },
                        ],
                      }}
                    />
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Dataset</th>
                            <th>Prepared years</th>
                            <th>Supported measures</th>
                            <th>Rows</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.values(catalog!.datasets).map((d) => (
                            <tr key={d.id}>
                              <td>{d.title}</td>
                              <td>{d.years.join(", ")}</td>
                              <td>
                                {d.metrics
                                  .map((m) => metricNames[m])
                                  .join(", ")}
                                {d.severity_supported ? ", severity" : ""}
                              </td>
                              <td>{fmt(d.rows)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Panel>
                  <Panel title="Known discrepancies & interpretation">
                    {catalog!.caveats.map((n) => (
                      <p className="quality-note" key={n}>
                        △ {n}
                      </p>
                    ))}
                    <p className="quality-note">
                      Severity is not personal crash probability. Population and
                      exposure rates are not supplied. Current map geography is
                      illustrative, not historical.
                    </p>
                    <p className="quality-note">
                      Data refresh is a reviewed command-line extraction, not a
                      live feed. Source checks reconcile columns to printed
                      totals; they cannot establish completeness of police
                      reporting.
                    </p>
                  </Panel>
                  <Panel
                    title="Source register"
                    subtitle={`${catalog!.checks.length} expanded-table column reconciliations passed`}
                  >
                    {[
                      ...new Map(
                        catalog!.sources.map((s) => [s.url, s]),
                      ).values(),
                    ].map((s) => (
                      <p key={s.url} className="source-link">
                        <a href={s.url} target="_blank" rel="noreferrer">
                          {s.title} ↗
                        </a>
                      </p>
                    ))}
                    <p className="footnote">
                      Snapshot: {result.snapshot.slice(0, 20)}. All fact rows
                      carry source IDs. The supporting Tableau draft still
                      requires native Tableau acceptance.
                    </p>
                  </Panel>
                </div>
              ) : page === "priorities" ? (
                <div className="grid">
                  <Panel
                    title="Burden and severity"
                    subtitle="Each point is a state; counts describe reporting burden, not exposure risk."
                  >
                    {
                      <Chart
                        title="Accidents versus deaths per 100 accidents by state"
                        motion={motion && !reduced}
                        onClick={selectState}
                        option={{
                          tooltip: {
                            formatter: (p: any) =>
                              `${p.name}: ${fmt(p.value[0])} accidents / severity ${fmt(p.value[1], "severity")}`,
                          },
                          grid: { left: 65, right: 25, top: 25, bottom: 45 },
                          xAxis: {
                            name: "Accidents",
                            nameLocation: "middle",
                            nameGap: 30,
                            type: "value",
                          },
                          yAxis: { name: "Deaths / 100", type: "value" },
                          series: [
                            {
                              type: "scatter",
                              id: "states",
                              data: result.states
                                .filter(
                                  (r) =>
                                    r.accidents !== null && r.severity !== null,
                                )
                                .map((r) => ({
                                  name: r.state,
                                  value: [r.accidents, r.severity],
                                  symbolSize: Math.max(
                                    8,
                                    Math.min(
                                      30,
                                      Math.sqrt(r.fatalities || 0) / 5,
                                    ),
                                  ),
                                })),
                              itemStyle: { color: "#087e75", opacity: 0.8 },
                            },
                          ],
                        }}
                      />
                    }
                    <DataTable
                      rows={result.states}
                      metric={activeMetric}
                      onState={selectState}
                    />
                  </Panel>
                  <Panel
                    title="Compare annual patterns"
                    subtitle="Select 2–5 states in the global state control."
                  >
                    {trend()}
                  </Panel>
                  <Panel
                    title="Where high accidents meet high severity"
                    subtitle={`Every state in either set; the intersection appears first. Top ${result.query.top_n} accident states and severity ≥ ${result.query.threshold}; minimum ${result.query.min_accidents} accidents for severity membership.`}
                    wide
                  >
                    <label className="threshold">
                      Severity threshold
                      <input
                        id="threshold"
                        type="number"
                        min="0"
                        max="1000"
                        step="1"
                        value={thresholdInput}
                        aria-invalid={!!thresholdError}
                        aria-describedby={
                          thresholdError ? "threshold-error" : undefined
                        }
                        onChange={(e) => {
                          setThresholdInput(e.target.value);
                          setThresholdError("");
                        }}
                        onBlur={() => {
                          const value = Number(thresholdInput);
                          if (
                            thresholdInput.trim() === "" ||
                            !Number.isFinite(value) ||
                            value < 0 ||
                            value > 1000
                          ) {
                            setThresholdError(
                              `Enter a number from 0 to 1000. Results still use ${threshold}.`,
                            );
                          } else {
                            setThreshold(value);
                            setThresholdInput(String(value));
                            setThresholdError("");
                          }
                        }}
                      />{" "}
                      deaths / 100 accidents
                    </label>
                    <label className="threshold">
                      Minimum accidents for severity set
                      <select
                        id="minimum"
                        value={minimum}
                        onChange={(e) => setMinimum(Number(e.target.value))}
                      >
                        {[0, 100, 500, 1000].map((v) => (
                          <option key={v} value={v}>
                            {v === 0
                              ? "No minimum (flag small counts)"
                              : fmt(v)}
                          </option>
                        ))}
                      </select>
                    </label>
                    {thresholdError && (
                      <p
                        id="threshold-error"
                        className="input-error"
                        role="alert"
                      >
                        {thresholdError}{" "}
                        <button
                          className="link"
                          onClick={() => {
                            setThresholdInput(String(threshold));
                            setThresholdError("");
                          }}
                        >
                          Restore {threshold}
                        </button>
                      </p>
                    )}
                    <p className="footnote">
                      An exploratory rule, not an official risk designation.
                      Complete paired observations are required for the severity
                      set; incomplete states remain unclassified. Small
                      denominators may produce unstable ratios.
                    </p>
                    <div className="table-scroll risk-table">
                      <table>
                        <thead>
                          <tr>
                            <th>STATE / UT</th>
                            <th>ACCIDENTS</th>
                            <th>SEVERITY</th>
                            <th>HIGH ACCIDENTS</th>
                            <th>HIGH SEVERITY</th>
                            <th>CLASSIFICATION</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.risk.map((r) => (
                            <tr key={r.state}>
                              <td>
                                <button
                                  className="link"
                                  onClick={() => selectState(r.state!)}
                                >
                                  {r.state}
                                </button>
                              </td>
                              <td>
                                {fmt(r.accidents)}
                                {(r.accidents || 0) < 100
                                  ? " · small count"
                                  : ""}
                              </td>
                              <td>{fmt(r.severity, "severity")}</td>
                              <td>{r.high_accidents ? "In set" : "—"}</td>
                              <td>{r.high_severity ? "In set" : "—"}</td>
                              <td>
                                <span
                                  className={
                                    "risk-pill " +
                                    (r.risk === "Combined high risk"
                                      ? "high"
                                      : "")
                                  }
                                >
                                  {r.risk}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Panel>
                </div>
              ) : (
                <div className="grid">
                  {page === "overview" ? (
                    <Panel
                      title="The geography of road safety"
                      subtitle={`${units} · ${result.query.years.join(", ")}`}
                      tag="STATE MAP"
                    >
                      {geo && (
                        <StateMap
                          geo={geo}
                          rows={result.states}
                          metric={activeMetric}
                          onSelect={selectState}
                          scale={
                            result.query.years.length > 1
                              ? Math.max(
                                  ...result.states.map((r) => r.value || 0),
                                  1,
                                )
                              : result.map_scale
                          }
                        />
                      )}
                      <DataTable
                        rows={result.states}
                        metric={activeMetric}
                        onState={selectState}
                      />
                    </Panel>
                  ) : (
                    <Panel
                      title={result.dataset.title}
                      subtitle={`${units} · category selection applies only to this dataset`}
                      tag={
                        dataset === "matrix"
                          ? "JOINT DATA"
                          : "CATEGORY ANALYSIS"
                      }
                    >
                      {categoryChart()}
                    </Panel>
                  )}
                  <Panel
                    title={`Top ${result.query.top_n} states & UTs`}
                    subtitle={`${units} · current dataset and selection`}
                  >
                    {bars(result.states, "state", result.query.top_n)}
                  </Panel>
                  <Panel
                    title="How the pattern changes"
                    subtitle={`${units} · ${result.dataset.years.join(", ")} prepared`}
                    wide
                  >
                    {trend()}
                  </Panel>
                  {result.dataset.note && (
                    <Panel title="Source definition & cautions" wide>
                      <p className="quality-note">{result.dataset.note}</p>
                    </Panel>
                  )}
                </div>
              )}
            </div>
          )}
          <footer>
            <span>ROADLENS INDIA · Evidence for safer mobility</span>
            <span>
              Official MoRTH extracts · No fabricated observations ·{" "}
              <button className="link" onClick={() => nav("evidence")}>
                Data quality ↗
              </button>
            </span>
          </footer>
        </main>
      </div>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
