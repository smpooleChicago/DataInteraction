<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';

  import Choropleth from './components/Choropleth.svelte';
  import TimeSeries from './components/TimeSeries.svelte';
  import DateRangeSlider from './components/DateRangeSlider.svelte';

  import { selectedCountries, dateRange, showEvents } from './lib/stores.js';
  import {
    loadData,
    computeCountryAverages,
    computeTimeSeries,
    computeP95,
  } from './lib/data.js';

  // Loaded state
  let ready = false;
  let loadError = null;

  // Raw data returned by loadData()
  let dateMap = null;
  let fipsToName = null;
  let fipsToNumeric = null;
  let numericToFips = null;
  let numericToName = null;
  let minDate = null;
  let maxDate = null;

  // TopoJSON topology
  let topology = null;

  // Derived: country averages for current date range
  $: countryAverages =
    dateMap && $dateRange && fipsToNumeric && numericToName
      ? computeCountryAverages(dateMap, $dateRange, fipsToNumeric, numericToName)
      : new Map();

  // Derived: p95 of current averages (color scale domain)
  $: p95 = countryAverages.size > 0 ? computeP95(countryAverages) : 0.05;

  // Derived: time series for selected countries (or global)
  $: timeSeriesData =
    dateMap && $dateRange
      ? computeTimeSeries(dateMap, $selectedCountries, $dateRange)
      : [];

  // Label for the time series line
  $: tsLabel =
    $selectedCountries.size === 0
      ? 'Global'
      : $selectedCountries.size <= 3
        ? [...$selectedCountries]
            .map(fips => fipsToName?.get(fips) || fips)
            .join(', ')
        : `${$selectedCountries.size} countries`;

  onMount(async () => {
    try {
      const [data, topo] = await Promise.all([
        loadData(),
        d3.json('/data/countries-110m.json'),
      ]);

      ({ dateMap, fipsToName, fipsToNumeric, numericToFips, numericToName, minDate, maxDate } = data);
      topology = topo;

      dateRange.set([minDate, maxDate]);
      ready = true;
    } catch (e) {
      loadError = e.message;
      console.error('Load error:', e);
    }
  });

  function clearSelection() {
    selectedCountries.set(new Set());
  }
</script>

<main>
  <header class="page-header">
    <div class="header-rule"></div>
    <div class="header-content">
      <h1>The war the world watched</h1>
      <p class="deck">
        Share of news reports mentioning the Russia–Ukraine war, by country of
        origin · Feb 2022 – May 2026 · Source: GDELT
      </p>
    </div>
    <div class="header-rule header-rule--bottom"></div>
  </header>

  {#if loadError}
    <div class="state-msg error">Failed to load data: {loadError}</div>
  {:else if !ready}
    <div class="state-msg">Loading 290 000 rows…</div>
  {:else}

    <!-- ── Controls ─────────────────────────────────────────────── -->
    <div class="controls">
      <label class="events-toggle">
        <input type="checkbox" bind:checked={$showEvents} />
        Show key events
      </label>

      {#if $selectedCountries.size > 0}
        <button class="clear-btn" on:click={clearSelection}>
          Clear selection ({$selectedCountries.size} {$selectedCountries.size === 1 ? 'country' : 'countries'})
        </button>
      {:else}
        <span class="hint">Click a country on the map to compare its coverage rate</span>
      {/if}
    </div>

    <!-- ── Date brush ─────────────────────────────────────────────── -->
    <section class="section-brush">
      <div class="brush-label">Filter date range</div>
      <DateRangeSlider {minDate} {maxDate} />
    </section>

    <!-- ── Choropleth ─────────────────────────────────────────────── -->
    <section class="section-map">
      <Choropleth {topology} {countryAverages} {p95} />
    </section>

    <!-- ── Time series ───────────────────────────────────────────── -->
    <section class="section-ts">
      <div class="ts-header">
        <span class="ts-title">
          {$selectedCountries.size === 0 ? 'Global coverage rate' : `Coverage rate – ${tsLabel}`}
        </span>
        <span class="ts-note">7-day rolling average</span>
      </div>
      <TimeSeries
        {timeSeriesData}
        dateRange={$dateRange}
        label={tsLabel}
        showEvents={$showEvents}
      />
    </section>

  {/if}

  <footer class="page-footer">
    Data: GDELT Project · Graphic detail–style dashboard · Desktop optimised
  </footer>
</main>

<style>
  main {
    max-width: 1000px;
    margin: 0 auto;
    padding: 0 20px 40px;
  }

  /* Header */
  .page-header {
    padding: 0 0 8px;
  }

  .header-rule {
    height: 3px;
    background: #e3120b;
    margin-bottom: 10px;
  }

  .header-rule--bottom {
    height: 1px;
    background: #ccc;
    margin-top: 10px;
    margin-bottom: 0;
  }

  h1 {
    font-family: var(--serif);
    font-size: 28px;
    font-weight: 700;
    color: #111;
    margin: 0 0 6px;
    line-height: 1.2;
  }

  .deck {
    font-family: var(--sans);
    font-size: 13.5px;
    color: #555;
    margin: 0;
    line-height: 1.45;
  }

  /* Controls */
  .controls {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 10px 0 4px;
    font-family: var(--sans);
    font-size: 13px;
  }

  .events-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    color: #333;
  }

  .events-toggle input {
    cursor: pointer;
    accent-color: #c0392b;
  }

  .clear-btn {
    background: none;
    border: 1px solid #1a3a6b;
    color: #1a3a6b;
    font-family: var(--sans);
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 3px;
    cursor: pointer;
  }

  .clear-btn:hover {
    background: #1a3a6b;
    color: #fff;
  }

  .hint {
    color: #999;
    font-size: 12px;
  }

  /* Sections */
  .section-brush {
    margin-top: 8px;
  }

  .brush-label {
    font-family: var(--sans);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #999;
    margin-bottom: 2px;
  }

  .section-map {
    margin-top: 6px;
  }

  .section-ts {
    margin-top: 20px;
  }

  .ts-header {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 50px;
  }

  .ts-title {
    font-family: var(--sans);
    font-size: 14px;
    font-weight: 600;
    color: #222;
  }

  .ts-note {
    font-family: var(--sans);
    font-size: 12px;
    color: #999;
  }

  /* Loading / error */
  .state-msg {
    padding: 80px 0;
    text-align: center;
    font-family: var(--sans);
    color: #aaa;
    font-size: 15px;
  }

  .state-msg.error {
    color: #c0392b;
  }

  /* Footer */
  .page-footer {
    margin-top: 32px;
    border-top: 1px solid #eee;
    padding-top: 10px;
    font-family: var(--sans);
    font-size: 11px;
    color: #bbb;
  }
</style>
