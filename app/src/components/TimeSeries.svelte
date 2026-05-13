<script>
  import * as d3 from 'd3';
  import { selectedYearMonth } from '../lib/stores.js';

  // [{date: Date, value: number|null}] – already 7-day smoothed
  export let timeSeriesData = [];
  // [Date, Date] – drives x-axis zoom
  export let dateRange = null;
  export let label = 'Global';
  export let showEvents = false;
  // "YYYY-MM" or null – renders a grey background rect for the selected month
  export let highlightMonth = null;

  const KEY_EVENTS = [
    { date: new Date('2022-02-24'), label: 'Invasion begins' },
    { date: new Date('2022-09-21'), label: 'Partial mobilisation' },
    { date: new Date('2022-11-11'), label: 'Kherson liberated' },
    { date: new Date('2023-02-24'), label: '1-year anniversary' },
    { date: new Date('2023-06-23'), label: 'Wagner mutiny' },
    { date: new Date('2023-10-07 '), label: 'Gaza war begins' },
    { date: new Date('2024-08-06'), label: 'Kursk incursion' },
    { date: new Date('2025-02-12'), label: 'Trump–Putin call' },
    { date: new Date('2025-08-15'), label: 'Anchorage summit' },
    { date: new Date('2025-10-10 '), label: 'Gaza Ceasefire' },
  ];

  const W = 960;
  const H = 300;
  const M = { top: 24, right: 32, bottom: 38, left: 54 };
  const IW = W - M.left - M.right;
  const IH = H - M.top - M.bottom;

  // X domain: zoom to selected range (falls back to data extent)
  $: xDomain = dateRange
    ? dateRange
    : timeSeriesData.length > 0
      ? [d3.min(timeSeriesData, d => d.date), d3.max(timeSeriesData, d => d.date)]
      : [new Date('2022-02-01'), new Date('2026-05-10')];

  $: xScale = d3.scaleTime().domain(xDomain).range([0, IW]);

  // Y domain: 0 to max of smoothed values (or fallback)
  $: validVals = timeSeriesData.filter(d => d.value != null).map(d => d.value);
  $: yMax = validVals.length > 0 ? Math.max(d3.max(validVals) * 1.08, 2) : 10;
  $: yScale = d3.scaleLinear().domain([0, yMax]).range([IH, 0]).nice();

  // Axis ticks
  $: xTicks = xScale.ticks(d3.timeMonth.every(3));
  $: yTicks = yScale.ticks(5);
  const fmtMonth = d3.timeFormat('%b %Y');
  const fmtY = v => `${v.toFixed(0)}%`;

  // Line path – only connect defined segments
  $: lineGen = d3.line()
    .x(d => xScale(d.date))
    .y(d => yScale(d.value))
    .defined(d => d.value != null)
    .curve(d3.curveMonotoneX);

  $: linePath = timeSeriesData.length > 0 ? lineGen(timeSeriesData) : '';

  // Last visible defined point for label anchor
  $: lastDefined = [...timeSeriesData].reverse().find(d => d.value != null && xScale(d.date) <= IW && xScale(d.date) >= 0);

  // Events within visible date range
  $: visibleEvents = showEvents
    ? KEY_EVENTS.filter(e => e.date >= xDomain[0] && e.date <= xDomain[1])
    : [];

  // Show every other x tick label to avoid crowding
  $: xTicksLabeled = xTicks.filter((_, i) => i % 2 === 0 || xTicks.length <= 8);

  // Grey highlight rect for selected month
  const parseYM = d3.timeParse('%Y-%m');
  $: monthRect = (() => {
    if (!highlightMonth) return null;
    const d0 = parseYM(highlightMonth);
    if (!d0) return null;
    const d1 = d3.timeMonth.offset(d0, 1);
    const x0 = xScale(d0);
    const x1 = xScale(d1);
    if (x1 <= 0 || x0 >= IW) return null; // outside visible window
    return { x: Math.max(0, x0), width: Math.min(IW, x1) - Math.max(0, x0) };
  })();
</script>

<div class="ts-wrap" on:click={() => selectedYearMonth.set(null)} role="presentation">
  <svg width={W} height={H} style="overflow:visible;display:block;">
    <g transform="translate({M.left},{M.top})">

      <!-- Horizontal gridlines -->
      {#each yTicks as tick}
        <line
          x1="0" x2={IW}
          y1={yScale(tick)} y2={yScale(tick)}
          stroke="#e8e8e8" stroke-width="1"
        />
      {/each}

      <!-- Zero line -->
      <line x1="0" x2={IW} y1={yScale(0)} y2={yScale(0)} stroke="#ccc" stroke-width="1" />

      <!-- Selected-month highlight rect (behind line, in front of gridlines) -->
      {#if monthRect}
        <rect
          x={monthRect.x}
          y="0"
          width={monthRect.width}
          height={IH}
          fill="#999"
          fill-opacity="0.15"
          pointer-events="none"
        />
      {/if}

      <!-- Event annotations (vertical dashed lines + rotated labels) -->
      {#each visibleEvents as ev}
        {@const ex = xScale(ev.date)}
        <g class="event-annotation">
          <line
            x1={ex} x2={ex}
            y1={-8} y2={IH}
            stroke="#b0b0b0"
            stroke-width="1"
            stroke-dasharray="4 3"
          />
          <text
            transform="translate({ex - 3},{-10}) rotate(-55)"
            font-size="9"
            fill="#888"
            font-family="var(--sans)"
            text-anchor="start"
          >{ev.label}</text>
        </g>
      {/each}

      <!-- Data line -->
      {#if linePath}
        <path
          d={linePath}
          fill="none"
          stroke="#c0392b"
          stroke-width="2.2"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
      {/if}

      <!-- Line label at right end -->
      {#if lastDefined}
        <text
          x={xScale(lastDefined.date) + 5}
          y={yScale(lastDefined.value)}
          dominant-baseline="middle"
          font-size="11"
          font-weight="600"
          fill="#c0392b"
          font-family="var(--sans)"
        >{label}</text>
      {/if}

      <!-- X axis -->
      <g transform="translate(0,{IH})">
        <line x1="0" x2={IW} stroke="#ccc" stroke-width="1" />
        {#each xTicks as tick}
          {@const x = xScale(tick)}
          <line x1={x} x2={x} y1="0" y2="5" stroke="#ccc" />
        {/each}
        {#each xTicksLabeled as tick}
          <text
            x={xScale(tick)}
            y="18"
            text-anchor="middle"
            font-size="11"
            fill="#777"
            font-family="var(--sans)"
          >{fmtMonth(tick)}</text>
        {/each}
      </g>

      <!-- Y axis -->
      <g>
        <line x1="0" x2="0" y1="0" y2={IH} stroke="#ccc" stroke-width="1" />
        {#each yTicks as tick}
          <g transform="translate(0,{yScale(tick)})">
            <line x1="-4" x2="0" stroke="#ccc" />
            <text
              x="-8"
              dominant-baseline="middle"
              text-anchor="end"
              font-size="11"
              fill="#777"
              font-family="var(--sans)"
            >{fmtY(tick)}</text>
          </g>
        {/each}
        <!-- Y axis label -->
        <text
          transform="rotate(-90)"
          x={-IH / 2}
          y="-44"
          text-anchor="middle"
          font-size="11"
          fill="#666"
          font-family="var(--sans)"
        >% of reports mentioning the war</text>
      </g>

    </g>
  </svg>
</div>

<style>
  .ts-wrap {
    width: 100%;
  }
</style>
