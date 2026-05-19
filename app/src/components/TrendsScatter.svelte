<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';

  // Layout matches the choropleth's 960-px column so the section visually aligns.
  // Bottom margin is widened to host the size legend below the axis label.
  const W = 960;
  const H = 580;
  const M = { top: 40, right: 50, bottom: 110, left: 64 };
  const innerW = W - M.left - M.right;
  const innerH = H - M.top - M.bottom;

  // Inset the scale ranges by the max point radius so the largest dots
  // (e.g. Russia at rank ~1.0) stay fully inside the plot area.
  const MAX_R = 9;
  const x = d3.scaleLinear().domain([0, 1]).range([MAX_R, innerW - MAX_R]);
  const y = d3.scaleLinear().domain([0, 1]).range([innerH - MAX_R, MAX_R]);

  let data = [];
  let labeled = [];             // top 5 by volume in each gap group — get persistent labels
  let highlighted = new Set();  // iso2 codes of the labelled points
  let maxReports = 1;  // module-scope so the legend can reuse sizeFor()
  let hovered = null;
  let ready = false;
  let loadError = null;

  // Sample sizes for the legend — round powers of ten spanning the empirical
  // GDELT range (~1 → ~15M reports).
  const LEGEND_SAMPLES = [
    { value: 1_000, label: '1k' },
    { value: 100_000, label: '100k' },
    { value: 10_000_000, label: '10M' },
  ];

  // Point size encodes GDELT volume so micro-countries (Brunei, Tonga) appear
  // small even when their pct-rank places them at the extremes.
  const sizeFor = (totalReports, max) =>
    d3.scaleSqrt().domain([0, 1]).range([1.8, 9])(totalReports / max);

  // Hand-tuned offsets for labels that still collide after the default
  // left-of-dot placement. Each entry is [dx, dy] in SVG pixels, keyed by
  // country_name. Kept centralised so the overrides are auditable in one
  // place and easy to remove if the data is regenerated.
  const LABEL_OFFSETS = {
    'Russia':         [0, 14],   // sits below the Ukraine/Russia dot cluster
    'United Kingdom': [110, -5],   // lift clear of its own dot
  };

  onMount(async () => {
    try {
      const raw = await d3.csv('/data/trends_vs_coverage.csv', d3.autoType);
      maxReports = d3.max(raw, d => d.total_reports);
      data = raw.map(d => ({ ...d, _r: sizeFor(d.total_reports, maxReports) }));

      // Highlight the top 5 by volume on each side of the diagonal:
      // blue (gap < 0, search > coverage) and red (gap > 0, coverage > search).
      const byVolDesc = (a, b) => b.total_reports - a.total_reports;
      const negTop = raw.filter(d => d.gap < 0).sort(byVolDesc).slice(0, 5);
      const posTop = raw.filter(d => d.gap > 0).sort(byVolDesc).slice(0, 5);
      const labelIsos = new Set([...negTop, ...posTop].map(d => d.iso2));
      labeled = data.filter(d => labelIsos.has(d.iso2));
      highlighted = labelIsos;

      ready = true;
    } catch (e) {
      loadError = e.message;
      console.error('TrendsScatter load error:', e);
    }
  });

  // Format the tooltip rank as a percentile integer
  const pct = v => Math.round(v * 100);
</script>

{#if loadError}
  <div class="err">Failed to load trends_vs_coverage.csv: {loadError}</div>
{:else if !ready}
  <div class="loading">Loading search-vs-coverage data…</div>
{:else}
  <svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" role="img"
       aria-label="Scatterplot of country news coverage rank vs Google search interest rank">
    <g transform="translate({M.left},{M.top})">

      <!-- Shaded regions: blue above the diagonal, red below. -->
      <polygon points="0,0 {innerW},0 0,{innerH}" fill="#1a3a6b" opacity="0.05" />
      <polygon points="{innerW},0 {innerW},{innerH} 0,{innerH}" fill="#e3120b" opacity="0.05" />

      <!-- 45° reference: press attention matches search interest. -->
      <line x1="0" y1={innerH} x2={innerW} y2="0"
            stroke="#999" stroke-dasharray="3 3" />

      <!-- Region annotations -->
      <text x="12" y="20" class="region-label region-label--blue">
        Audiences searched more than press covered
      </text>
      <text x={innerW - 12} y={innerH - 12} text-anchor="end"
            class="region-label region-label--red">
        Press covered more than audiences searched
      </text>

      <!-- Axes -->
      <g class="axis">
        <line x1="0" y1={innerH} x2={innerW} y2={innerH} />
        {#each [0, 0.25, 0.5, 0.75, 1] as t}
          <g transform="translate({x(t)},{innerH})">
            <line y1="0" y2="5" />
            <text y="20" text-anchor="middle" class="tick">{pct(t)}</text>
          </g>
        {/each}
        <text x={innerW / 2} y={innerH + 44} text-anchor="middle" class="axis-label">
          Within-country share of war coverage (percentile rank)
        </text>
      </g>

      <g class="axis">
        <line x1="0" y1="0" x2="0" y2={innerH} />
        {#each [0, 0.25, 0.5, 0.75, 1] as t}
          <g transform="translate(0,{y(t)})">
            <line x1="0" x2="-5" />
            <text x="-9" dy="0.32em" text-anchor="end" class="tick">{pct(t)}</text>
          </g>
        {/each}
        <text transform="translate(-46,{innerH / 2}) rotate(-90)"
              text-anchor="middle" class="axis-label">
          Search interest in Russia–Ukraine war terms
        </text>
      </g>

      <!-- Size legend, placed beneath the x-axis label. -->
      <g transform="translate({innerW / 2},{innerH + 70})">
        <text x="0" y="0" text-anchor="middle" class="legend-title">
          Point size = country's total GDELT war coverage
        </text>
        <g transform="translate(-150, 22)">
          {#each LEGEND_SAMPLES as ex, i}
            <g transform="translate({i * 110}, 0)">
              <circle r={sizeFor(ex.value, maxReports)}
                      fill="#999" fill-opacity="0.6"
                      stroke="#fff" stroke-width="0.6" />
              <text x="14" dy="0.32em" class="legend-label">
                {ex.label} reports
              </text>
            </g>
          {/each}
        </g>
      </g>

      <!-- Points. Highlighted (top-3-per-group) dots get full opacity and
           a dark stroke so they read as the focus; others fade into the
           background. -->
      {#each data as d}
        {@const isHi = highlighted.has(d.iso2)}
        {@const isHover = hovered && hovered.iso2 === d.iso2}
        <circle
          role="graphics-symbol"
          aria-label="{d.country_name}"
          cx={x(d.coverage_pct_rank)}
          cy={y(d.trends_pct_rank)}
          r={d._r}
          fill={d.gap < 0 ? '#1a3a6b' : '#e3120b'}
          fill-opacity={isHover ? 0.95 : isHi ? 0.95 : 0.25}
          stroke={isHover || isHi ? '#111' : '#fff'}
          stroke-width={isHi ? 1.2 : 0.6}
          on:mouseenter={() => hovered = d}
          on:mouseleave={() => hovered = null}
        />
      {/each}

<!-- Persistent labels for the 10 highlighted points (top 5 per group).
           Transparent — no background rect — with a white text halo so the
           name stays legible when it crosses faded dots. Anchored to the
           LEFT of each dot since the labelled countries all sit on the
           right half of the chart. Per-country dx/dy overrides come from
           LABEL_OFFSETS for the few labels that still collide. -->
      {#each labeled as d}
        {@const off = LABEL_OFFSETS[d.country_name] ?? [0, 0]}
        <g transform="translate({x(d.coverage_pct_rank) - d._r - 5 + off[0]},{y(d.trends_pct_rank) + off[1]})">
          <text x="0" y="-2" text-anchor="end" class="callout-name">{d.country_name}</text>
        </g>
      {/each}

      <!-- Hover tooltip (suppressed for already-labelled points). -->
      {#if hovered && !highlighted.has(hovered.iso2)}
        <g transform="translate({x(hovered.coverage_pct_rank) + 10},{y(hovered.trends_pct_rank) - 10})">
          <rect x="0" y="-30" width="170" height="42" fill="#fff" stroke="#333" rx="2" />
          <text x="8" y="-14" class="tip-name">{hovered.country_name}</text>
          <text x="8" y="2" class="tip-detail">
            press {pct(hovered.coverage_pct_rank)} · search {pct(hovered.trends_pct_rank)}
          </text>
        </g>
      {/if}
    </g>
  </svg>
{/if}

<style>
  svg {
    width: 100%;
    height: auto;
    max-width: 960px;
    display: block;
    margin: 0 auto;
  }
  .axis line { stroke: #333; }
  .tick {
    font-family: var(--sans);
    font-size: 11px;
    fill: #666;
  }
  .axis-label {
    font-family: var(--sans);
    font-size: 12px;
    fill: #333;
  }
  .region-label {
    font-family: var(--serif);
    font-size: 13px;
    font-style: italic;
  }
  .region-label--blue { fill: #1a3a6b; }
  .region-label--red  { fill: #e3120b; }
.legend-title {
    font-family: var(--sans);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    fill: #888;
  }
  .legend-label {
    font-family: var(--sans);
    font-size: 11px;
    fill: #555;
  }
  .tip-name {
    font-family: var(--sans);
    font-size: 12px;
    font-weight: 600;
    fill: #111;
  }
  .tip-detail {
    font-family: var(--sans);
    font-size: 11px;
    fill: #555;
  }
  .callout-name,
  .callout-detail {
    font-family: var(--sans);
    pointer-events: none;
    paint-order: stroke;
    stroke: #fff;
    stroke-width: 3px;
    stroke-linejoin: round;
  }
  .callout-name {
    font-size: 12px;
    font-weight: 600;
    fill: #111;
  }
  .callout-detail {
    font-size: 11px;
    fill: #555;
  }
  .loading, .err {
    padding: 60px 0;
    text-align: center;
    font-family: var(--sans);
    color: #aaa;
    font-size: 14px;
  }
  .err { color: #c0392b; }
  circle { cursor: pointer; transition: fill-opacity 120ms; }
</style>
