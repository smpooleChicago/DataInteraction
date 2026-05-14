<script>
  import * as d3 from 'd3';
  import * as topojson from 'topojson-client';
  import { selectedCountries, selectedYearMonth } from '../lib/stores.js';

  export let topology = null;
  // Map<numericId, { fips, name, avgRatio, totalWar, totalAll }>
  export let countryAverages = new Map();
  export let interactive = true;   // false → hover tooltip only, no click selection
  export let highlightFips = new Set(); // FIPS codes to outline in dark blue

  const W = 960;
  const H = 500;
  const LEGEND_W = 180;
  const LEGEND_H = 10;
  const NO_DATA_COLOR = '#d4d4d4';
  const OCEAN_COLOR = '#c9dff0';

  // Static linear domain: global max when full date range is selected.
  const STATIC_MAX = 0.215; // 21.5%

  $: countries = topology
    ? topojson.feature(topology, topology.objects.countries)
    : null;

  $: projection = countries
    ? d3.geoEqualEarth().fitExtent([[2, 2], [W - 2, H - 2]], countries)
    : d3.geoEqualEarth();

  $: pathGen = d3.geoPath(projection);

  // Static linear scale — does not change with date range.
  const colorScale = d3.scaleSequential(d3.interpolateReds)
    .domain([0, STATIC_MAX])
    .clamp(true);

  // Pre-compute fills reactively so Svelte re-evaluates when selectedCountries changes.
  // When interactive=false the selection store is ignored (no greying on scrolly maps).
  $: fills = (() => {
    const map = new Map();
    for (const [numId, d] of countryAverages) {
      if (interactive && $selectedCountries.size > 0 && !$selectedCountries.has(d.fips)) {
        map.set(numId, '#c8c8c8');
      } else {
        map.set(numId, colorScale(d.avgRatio));
      }
    }
    return map;
  })();

  // Tooltip
  let tipVisible = false;
  let tipX = 0;
  let tipY = 0;
  let tipData = null;
  let containerEl;

  function handleClick(numId) {
    const d = countryAverages.get(numId);
    if (!d) return;
    selectedCountries.update(set => {
      const next = new Set(set);
      if (next.has(d.fips)) next.delete(d.fips);
      else next.add(d.fips);
      return next;
    });
  }

  function handleMouseover(event, numId) {
    const d = countryAverages.get(numId);
    if (!d) { tipVisible = false; return; }
    const rect = containerEl.getBoundingClientRect();
    tipX = event.clientX - rect.left + 12;
    tipY = event.clientY - rect.top - 10;
    tipData = d;
    tipVisible = true;
  }

  function handleMousemove(event, numId) {
    if (!tipVisible) return;
    const rect = containerEl.getBoundingClientRect();
    tipX = event.clientX - rect.left + 12;
    tipY = event.clientY - rect.top - 10;
  }

  function handleMouseleave() {
    tipVisible = false;
  }

  // Legend gradient stops — linearly spaced.
  const legendStops = d3.range(0, 1.01, 0.1).map(t => ({
    offset: `${(t * 100).toFixed(0)}%`,
    color: colorScale(t * STATIC_MAX),
  }));

  function fmtPct(v) {
    return `${(v * 100).toFixed(1)}%`;
  }
</script>

<div class="wrap" bind:this={containerEl}>
  {#if countries}
    <!-- Any click on the choropleth (country or ocean) clears the themes month selection -->
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-noninteractive-element-interactions -->
    <svg width={W} height={H + 36} style="display:block;" role="img" aria-label="World map" on:click={() => interactive && selectedYearMonth.set(null)}>
      <!-- Ocean -->
      <path d={pathGen({ type: 'Sphere' })} fill={OCEAN_COLOR} />

      <!-- Countries -->
      {#each countries.features as feat}
        {@const id = +feat.id}
        {@const hasData = countryAverages.has(id)}
        <path
          d={pathGen(feat)}
          fill={fills.get(id) ?? NO_DATA_COLOR}
          stroke="#fff"
          stroke-width="0.5"
          style="cursor:{hasData && interactive ? 'pointer' : 'default'}"
          role={hasData && interactive ? 'button' : 'img'}
          tabindex={hasData && interactive ? 0 : -1}
          aria-label={hasData ? `${countryAverages.get(id)?.name ?? ''}` : undefined}
          on:click={() => interactive && handleClick(id)}
          on:keydown={e => interactive && (e.key === 'Enter' || e.key === ' ') && handleClick(id)}
          on:mouseover={e => handleMouseover(e, id)}
          on:focus={e => handleMouseover(e, id)}
          on:mousemove={e => handleMousemove(e, id)}
          on:mouseleave={handleMouseleave}
          on:blur={handleMouseleave}
        />
      {/each}

      <!-- Sphere border -->
      <path d={pathGen({ type: 'Sphere' })} fill="none" stroke="#aaa" stroke-width="0.5" />

      <!-- Highlight overlay: dark blue stroke on top for highlighted FIPS -->
      {#if highlightFips.size > 0}
        {#each countries.features as feat}
          {@const id = +feat.id}
          {@const d = countryAverages.get(id)}
          {#if d && highlightFips.has(d.fips)}
            <path d={pathGen(feat)} fill="none" stroke="#1a3a6b" stroke-width="1.5" pointer-events="none" />
          {/if}
        {/each}
      {/if}

      <!-- Legend -->
      <g transform="translate({W - LEGEND_W - 16}, {H + 4})">
        <text y="-4" font-size="10" fill="#666" font-family="var(--sans)">
          Share of reports that are war-related
        </text>
        <defs>
          <linearGradient id="cmap" x1="0%" x2="100%">
            {#each legendStops as s}
              <stop offset={s.offset} stop-color={s.color} />
            {/each}
          </linearGradient>
        </defs>
        <rect width={LEGEND_W} height={LEGEND_H} fill="url(#cmap)" rx="1" />
        <text x="0" y={LEGEND_H + 12} font-size="9.5" fill="#555" font-family="var(--sans)" text-anchor="start">0%</text>
        <text x={LEGEND_W / 2} y={LEGEND_H + 12} font-size="9.5" fill="#555" font-family="var(--sans)" text-anchor="middle">{(STATIC_MAX / 2 * 100).toFixed(1)}%</text>
        <text x={LEGEND_W} y={LEGEND_H + 12} font-size="9.5" fill="#555" font-family="var(--sans)" text-anchor="end">{(STATIC_MAX * 100).toFixed(1)}%+</text>
      </g>
    </svg>

    <!-- Tooltip rendered in HTML for clean overflow -->
    {#if tipVisible && tipData}
      <div class="tip" style="left:{tipX}px;top:{tipY}px;">
        <div class="tip-name">{tipData.name}</div>
        <div>War coverage: <b>{fmtPct(tipData.avgRatio)}</b></div>
        <div>War reports: <b>{tipData.totalWar.toLocaleString()}</b></div>
        <div>Total reports: <b>{tipData.totalAll.toLocaleString()}</b></div>
        <div class="tip-hint">Click to {$selectedCountries.has(tipData.fips) ? 'deselect' : 'select'}</div>
      </div>
    {/if}
  {:else}
    <div class="placeholder">Loading map…</div>
  {/if}
</div>

<style>
  .wrap {
    position: relative;
    width: 100%;
  }

  .tip {
    position: absolute;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px 11px;
    font-size: 12.5px;
    font-family: var(--sans);
    pointer-events: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    z-index: 20;
    line-height: 1.55;
    min-width: 160px;
  }

  .tip-name {
    font-weight: 700;
    font-size: 13px;
    margin-bottom: 3px;
  }

  .tip-hint {
    margin-top: 4px;
    color: #888;
    font-size: 11px;
  }

  .placeholder {
    padding: 80px;
    text-align: center;
    color: #aaa;
    font-family: var(--sans);
  }

  :global(svg path:focus) {
    outline: none;
  }
</style>
