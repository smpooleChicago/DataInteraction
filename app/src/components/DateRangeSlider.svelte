<script>
  import * as d3 from 'd3';
  import { onMount } from 'svelte';
  import { dateRange, selectedYearMonth } from '../lib/stores.js';

  export let minDate;
  export let maxDate;

  // Match the 960px chart width and left margin so the brush aligns with the axes.
  const W = 960;
  const ML = 54;
  const MR = 32;
  const IW = W - ML - MR;
  const BRUSH_H = 26;
  const SVG_H = 48;

  let svgEl;

  $: xScale = minDate && maxDate
    ? d3.scaleTime().domain([minDate, maxDate]).range([0, IW])
    : null;

  $: yearTicks = xScale ? xScale.ticks(d3.timeYear.every(1)) : [];
  const fmtYear = d3.timeFormat('%Y');

  onMount(() => {
    if (!xScale) return;

    const g = d3.select(svgEl).select('.brush-g');

    const brush = d3.brushX()
      .extent([[0, 0], [IW, BRUSH_H]])
      .on('end', ({ selection }) => {
        if (!selection) {
          // Snap back to full range when user clears brush
          d3.select(svgEl).select('.brush-g').call(brush.move, [0, IW]);
          dateRange.set([minDate, maxDate]);
          return;
        }
        const [x0, x1] = selection;
        const d0 = xScale.invert(x0);
        const d1 = xScale.invert(x1);
        dateRange.set([d0, d1]);
      });

    g.call(brush);
    // Select full range on init
    g.call(brush.move, [0, IW]);
  });
</script>

<div class="slider-outer" on:mousedown={() => selectedYearMonth.set(null)} role="presentation">
  <svg width={W} height={SVG_H} bind:this={svgEl} style="display:block;">
    <g transform="translate({ML}, 4)">
      <!-- Track background -->
      <rect width={IW} height={BRUSH_H} fill="#f0f0f0" rx="2" />

      <!-- Year tick marks and labels -->
      {#if xScale}
        {#each yearTicks as tick}
          {@const x = xScale(tick)}
          <line x1={x} x2={x} y1={BRUSH_H} y2={BRUSH_H + 5} stroke="#aaa" stroke-width="1" />
          <text
            x={x}
            y={BRUSH_H + 16}
            text-anchor="middle"
            font-size="10"
            fill="#888"
            font-family="var(--sans)"
          >{fmtYear(tick)}</text>
        {/each}
      {/if}

      <!-- D3 brush overlays on top -->
      <g class="brush-g" />
    </g>
  </svg>
</div>

<style>
  .slider-outer {
    width: 100%;
    margin-bottom: 2px;
  }

  /* Style the brush selection rectangle */
  :global(.brush-g .selection) {
    fill: #c0392b;
    fill-opacity: 0.12;
    stroke: #c0392b;
    stroke-width: 1px;
  }

  :global(.brush-g .handle) {
    fill: #c0392b;
    fill-opacity: 0.75;
    rx: 2;
  }

  :global(.brush-g .overlay) {
    cursor: crosshair;
  }
</style>
