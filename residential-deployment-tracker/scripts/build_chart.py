"""Build the interactive HTML chart (docs/index.html) from the tracker CSVs."""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
OUTPUT_HTML = REPO_ROOT / "docs" / "index.html"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def quarter_sort_key(q: str) -> tuple[int, int]:
    year, qtr = q.split(" Q")
    return int(year), int(qtr)


def build_heat_pump_series() -> dict:
    rows = read_csv(DATA_DIR / "heat_pump.csv")
    rows.sort(key=lambda r: quarter_sort_key(r["quarter"]))
    points = [{"period": r["quarter"], "value": int(r["total_installs"])} for r in rows]
    return {
        "id": "heat_pump",
        "title": "Heat pump installations",
        "unit": "installations / quarter",
        "cadence": "quarterly",
        "period_step": 1,
        "year_step": 4,
        "color_light": "#2a78d6",
        "color_dark": "#3987e5",
        "points": points,
    }


def build_battery_series() -> dict:
    rows = read_csv(DATA_DIR / "battery.csv")
    rows.sort(key=lambda r: r["year_month"])
    points = [{"period": r["year_month"], "value": int(r["installs"])} for r in rows]
    return {
        "id": "battery",
        "title": "Battery installations",
        "unit": "installations / month",
        "cadence": "monthly",
        "period_step": 1,
        "year_step": 12,
        "color_light": "#1baf7a",
        "color_dark": "#199e70",
        "points": points,
    }


def build_solar_monthly_series() -> dict:
    rows = read_csv(DATA_DIR / "solar.csv")
    rows = [r for r in rows if r["cumulative_installs"]]
    rows.sort(key=lambda r: r["year_month"])
    points = []
    for prev, cur in zip(rows, rows[1:]):
        added = int(float(cur["cumulative_installs"])) - int(float(prev["cumulative_installs"]))
        points.append({"period": cur["year_month"], "value": added})
    return {
        "id": "solar_monthly",
        "title": "Solar PV installations added",
        "unit": "installations / month",
        "cadence": "monthly",
        "period_step": 1,
        "year_step": 12,
        "color_light": "#eda100",
        "color_dark": "#c98500",
        "points": points,
    }


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>GFI Residential Deployment Tracker</title>
<style>
  :root {{
    color-scheme: light;
    --surface-1: #fcfcfb;
    --page: #f9f9f7;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --muted: #898781;
    --grid: #e1e0d9;
    --baseline: #c3c2b7;
    --good: #006300;
    --bad: #d03b3b;
    --border: rgba(11,11,11,0.10);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:where(:not([data-theme="light"])) {{
      color-scheme: dark;
      --surface-1: #1a1a19;
      --page: #0d0d0d;
      --text-primary: #f0efec;
      --text-secondary: #c3c2b7;
      --muted: #898781;
      --grid: #2c2c2a;
      --baseline: #383835;
      --good: #0ca30c;
      --bad: #e66767;
      --border: rgba(255,255,255,0.10);
    }}
  }}
  :root[data-theme="dark"] {{
    color-scheme: dark;
    --surface-1: #1a1a19;
    --page: #0d0d0d;
    --text-primary: #f0efec;
    --text-secondary: #c3c2b7;
    --muted: #898781;
    --grid: #2c2c2a;
    --baseline: #383835;
    --good: #0ca30c;
    --bad: #e66767;
    --border: rgba(255,255,255,0.10);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--page);
    color: var(--text-primary);
    font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
    padding: 24px 16px 64px;
  }}
  .wrap {{ max-width: 920px; margin: 0 auto; }}
  h1 {{ font-size: 1.4rem; margin: 0 0 4px; }}
  .subtitle {{ color: var(--text-secondary); margin: 0 0 24px; font-size: 0.9rem; }}
  .card {{
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px 20px 12px;
    margin-bottom: 20px;
  }}
  .card-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
  .card h2 {{ font-size: 1.05rem; margin: 0 0 2px; }}
  .card .unit {{ color: var(--muted); font-size: 0.8rem; margin: 0 0 8px; }}
  .dl-btn {{
    flex-shrink: 0;
    font: inherit;
    font-size: 0.78rem;
    color: var(--text-secondary);
    background: var(--page);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 5px 10px;
    cursor: pointer;
  }}
  .dl-btn:hover {{ color: var(--text-primary); border-color: var(--baseline); }}
  svg {{ width: 100%; height: 220px; display: block; overflow: visible; }}
  .line {{ fill: none; stroke-width: 2px; }}
  .grid-line {{ stroke: var(--grid); stroke-width: 1px; }}
  .baseline {{ stroke: var(--baseline); stroke-width: 1px; }}
  .hover-dot {{ fill: var(--surface-1); stroke-width: 2px; r: 5px; }}
  .crosshair {{ stroke: var(--muted); stroke-width: 1px; stroke-dasharray: 3 3; }}
  .tooltip {{
    position: absolute;
    pointer-events: none;
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 0.82rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    white-space: nowrap;
    display: none;
    z-index: 10;
  }}
  .tooltip .period {{ color: var(--text-secondary); font-size: 0.75rem; margin-bottom: 2px; }}
  .tooltip .value {{ font-weight: 600; }}
  .tooltip .delta {{ color: var(--text-secondary); }}
  .tooltip .delta.up {{ color: var(--good); }}
  .tooltip .delta.down {{ color: var(--bad); }}
  footer {{ color: var(--muted); font-size: 0.78rem; margin-top: 8px; }}
  .chart-pos {{ position: relative; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>GFI Residential Deployment Tracker</h1>
  <p class="subtitle">UK domestic heat pump, battery and solar PV installations over time.<br>Data last checked against source: {last_checked}. Page built {generated_at}.</p>
  <div id="charts"></div>
  <footer>
    Sources: DESNZ heat pump deployment statistics, MCS domestic battery installation statistics, DESNZ Energy Trends 6.3 (solar PV).
    Heat pump and solar figures are UK domestic/retrofit only.
  </footer>
</div>
<div class="tooltip" id="tooltip"></div>
<script>
const SERIES = {series_json};

function fmt(n) {{
  return n.toLocaleString();
}}

function periodStepBack(points, idx, step) {{
  const j = idx - step;
  return j >= 0 ? points[j] : null;
}}

function downloadChartPNG(svg, idBase) {{
  const ns = 'http://www.w3.org/2000/svg';
  const clone = svg.cloneNode(true);
  const originals = Array.from(svg.querySelectorAll('*'));
  const clones = Array.from(clone.querySelectorAll('*'));

  // Hover-only elements (crosshair/dot) have no place in a static export -
  // drop them rather than rely on their hidden opacity carrying over.
  clones.forEach((cloneEl, i) => {{
    const origEl = originals[i];
    if (origEl.classList.contains('crosshair') || origEl.classList.contains('hover-dot')) {{
      cloneEl.remove();
    }}
  }});

  // Resolve every CSS custom property (var(--...)) to its actual used
  // color before export, since a standalone exported SVG has no
  // stylesheet of its own to resolve them against. Always set both
  // fill and stroke explicitly - e.g. the line path relies on a
  // stylesheet rule (fill: none) that disappears once class is
  // stripped, and would otherwise fall back to SVG's default black fill.
  originals.forEach((origEl, i) => {{
    const cloneEl = clones[i];
    // Note: cloneEl.isConnected is always false here - clone is a detached
    // tree, never inserted into the document - so that can't be used to
    // detect removed elements. Just skip ones the earlier pass deleted.
    if (!cloneEl || cloneEl.parentNode === null) return;
    const computed = getComputedStyle(origEl);
    cloneEl.setAttribute('fill', computed.fill);
    cloneEl.setAttribute('stroke', computed.stroke);
    cloneEl.removeAttribute('class');
  }});

  const vb = svg.viewBox.baseVal;
  clone.setAttribute('xmlns', ns);
  clone.setAttribute('width', vb.width);
  clone.setAttribute('height', vb.height);

  const bg = getComputedStyle(document.querySelector('.card')).backgroundColor;
  const bgRect = document.createElementNS(ns, 'rect');
  bgRect.setAttribute('x', vb.x);
  bgRect.setAttribute('y', vb.y);
  bgRect.setAttribute('width', vb.width);
  bgRect.setAttribute('height', vb.height);
  bgRect.setAttribute('fill', bg);
  clone.insertBefore(bgRect, clone.firstChild);

  const svgText = new XMLSerializer().serializeToString(clone);
  const svgBlob = new Blob([svgText], {{ type: 'image/svg+xml;charset=utf-8' }});
  const url = URL.createObjectURL(svgBlob);

  const img = new Image();
  img.onload = () => {{
    const scale = 2;
    const canvas = document.createElement('canvas');
    canvas.width = vb.width * scale;
    canvas.height = vb.height * scale;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(url);

    canvas.toBlob((blob) => {{
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `gfi-${{idBase}}-chart.png`;
      a.click();
      URL.revokeObjectURL(a.href);
    }}, 'image/png');
  }};
  img.src = url;
}}

function buildChart(series) {{
  const card = document.createElement('div');
  card.className = 'card';
  const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const rootTheme = document.documentElement.getAttribute('data-theme');
  const isDark = rootTheme === 'dark' || (rootTheme !== 'light' && dark);
  const color = isDark ? series.color_dark : series.color_light;

  card.innerHTML = `
    <div class="card-head">
      <div>
        <h2>${{series.title}}</h2>
        <p class="unit">${{series.unit}}</p>
      </div>
      <button class="dl-btn" type="button">Download PNG</button>
    </div>
    <div class="chart-pos"><svg viewBox="0 0 860 220" preserveAspectRatio="none"></svg></div>
  `;
  document.getElementById('charts').appendChild(card);

  const svg = card.querySelector('svg');
  card.querySelector('.dl-btn').addEventListener('click', () => downloadChartPNG(svg, series.id));
  const points = series.points;
  if (points.length === 0) {{
    card.querySelector('.chart-pos').innerHTML = '<p style="color:var(--muted)">No data yet.</p>';
    return;
  }}

  const padL = 72, padR = 10, padT = 10, padB = 24;
  const w = 860, h = 220;
  const values = points.map(p => p.value);
  const minV = Math.min(...values, 0);
  const maxV = Math.max(...values, minV + 1);
  const range = (maxV - minV) || 1;

  const x = i => padL + (i / Math.max(points.length - 1, 1)) * (w - padL - padR);
  const y = v => padT + (1 - (v - minV) / range) * (h - padT - padB);

  function fmtAxis(n) {{
    const abs = Math.abs(n);
    if (abs >= 1e6) return (n / 1e6).toFixed(abs % 1e6 === 0 ? 0 : 1) + 'm';
    if (abs >= 1e3) return (n / 1e3).toFixed(abs % 1e3 === 0 ? 0 : 1) + 'k';
    return String(Math.round(n));
  }}

  const ns = 'http://www.w3.org/2000/svg';
  function el(tag, attrs) {{
    const e = document.createElementNS(ns, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }}

  // gridlines + y-axis labels (4 horizontal bands)
  for (let i = 0; i <= 3; i++) {{
    const v = minV + (range * i / 3);
    svg.appendChild(el('line', {{ x1: padL, x2: w - padR, y1: y(v), y2: y(v), class: 'grid-line' }}));
    const t = el('text', {{ x: padL - 10, y: y(v) + 3, 'text-anchor': 'end', fill: 'var(--muted)', 'font-size': '10' }});
    t.textContent = fmtAxis(v);
    svg.appendChild(t);
  }}
  svg.appendChild(el('line', {{ x1: padL, x2: w - padR, y1: h - padB, y2: h - padB, class: 'baseline' }}));

  // line path (only draws between 2+ points)
  if (points.length > 1) {{
    const d = points.map((p, i) => `${{i === 0 ? 'M' : 'L'}} ${{x(i)}} ${{y(p.value)}}`).join(' ');
    svg.appendChild(el('path', {{ d, class: 'line', stroke: color }}));
  }}

  // permanent markers at every data point
  points.forEach((p, i) => {{
    svg.appendChild(el('circle', {{ cx: x(i), cy: y(p.value), r: points.length > 60 ? 2 : 3.5, fill: color }}));
  }});

  // x-axis labels (first, last, and a few in between) - anchor the first/
  // last labels to the inside edge so they don't clip past the viewBox
  const labelCount = Math.min(6, points.length);
  for (let k = 0; k < labelCount; k++) {{
    const i = Math.round(k * (points.length - 1) / Math.max(labelCount - 1, 1));
    const anchor = k === 0 ? 'start' : (k === labelCount - 1 ? 'end' : 'middle');
    const t = el('text', {{ x: x(i), y: h - 6, 'text-anchor': anchor, fill: 'var(--muted)', 'font-size': '10' }});
    t.textContent = points[i].period;
    svg.appendChild(t);
  }}

  // hover interaction (hidden via opacity, never relies on off-canvas position)
  const crosshair = el('line', {{ class: 'crosshair', y1: padT, y2: h - padB, x1: 0, x2: 0, opacity: 0 }});
  const dot = el('circle', {{ class: 'hover-dot', stroke: color, cx: 0, cy: 0, opacity: 0 }});
  svg.appendChild(crosshair);
  svg.appendChild(dot);

  const tooltip = document.getElementById('tooltip');
  const overlay = el('rect', {{ x: padL, y: padT, width: w - padL - padR, height: h - padT - padB, fill: 'transparent' }});
  svg.appendChild(overlay);

  overlay.addEventListener('mousemove', (ev) => {{
    const rect = svg.getBoundingClientRect();
    const relX = (ev.clientX - rect.left) / rect.width * w;
    let idx = Math.round((relX - padL) / (w - padL - padR) * (points.length - 1));
    idx = Math.max(0, Math.min(points.length - 1, idx));
    const p = points[idx];

    crosshair.setAttribute('x1', x(idx));
    crosshair.setAttribute('x2', x(idx));
    crosshair.setAttribute('opacity', 1);
    dot.setAttribute('cx', x(idx));
    dot.setAttribute('cy', y(p.value));
    dot.setAttribute('opacity', 1);

    const prevPeriod = periodStepBack(points, idx, series.period_step);
    const prevYear = periodStepBack(points, idx, series.year_step);

    function deltaLine(label, prev) {{
      if (!prev) return `<div class="delta">${{label}}: n/a</div>`;
      const diff = p.value - prev.value;
      const pct = prev.value !== 0 ? (diff / prev.value * 100) : null;
      const cls = diff > 0 ? 'up' : (diff < 0 ? 'down' : '');
      const sign = diff > 0 ? '+' : '';
      const pctStr = pct !== null ? ` (${{sign}}${{pct.toFixed(1)}}%)` : '';
      return `<div class="delta ${{cls}}">${{label}}: ${{sign}}${{fmt(diff)}}${{pctStr}}</div>`;
    }}

    tooltip.innerHTML = `
      <div class="period">${{p.period}}</div>
      <div class="value">${{fmt(p.value)}}</div>
      ${{deltaLine(series.cadence === 'quarterly' ? 'QoQ' : 'MoM', prevPeriod)}}
      ${{deltaLine('YoY', prevYear)}}
    `;
    tooltip.style.display = 'block';
    tooltip.style.left = (ev.clientX + 14) + 'px';
    tooltip.style.top = (ev.clientY + 14) + 'px';
  }});

  overlay.addEventListener('mouseleave', () => {{
    tooltip.style.display = 'none';
    crosshair.setAttribute('opacity', 0);
    dot.setAttribute('opacity', 0);
  }});
}}

SERIES.forEach(buildChart);
</script>
</body>
</html>
"""


def build() -> None:
    from datetime import datetime, timezone

    series = [
        build_heat_pump_series(),
        build_battery_series(),
        build_solar_monthly_series(),
    ]
    status_file = DATA_DIR / "last_checked.json"
    last_checked = "never"
    if status_file.exists():
        status = json.loads(status_file.read_text())
        checked_ats = [v["checked_at"] for v in status.values() if v.get("checked_at")]
        if checked_ats:
            last_checked = datetime.fromisoformat(min(checked_ats)).strftime("%Y-%m-%d %H:%M UTC")

    html = TEMPLATE.format(
        series_json=json.dumps(series),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        last_checked=last_checked,
    )
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html)
    print(f"Wrote {OUTPUT_HTML}")


if __name__ == "__main__":
    build()
