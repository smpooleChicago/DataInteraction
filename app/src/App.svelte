<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';

  import Choropleth from './components/Choropleth.svelte';
  import TimeSeries from './components/TimeSeries.svelte';
  import DateRangeSlider from './components/DateRangeSlider.svelte';
  import ThemesPanel from './components/ThemesPanel.svelte';
  import Scrolly from './components/Scrolly.svelte';
  import Sparkline from './components/Sparkline.svelte';
  import TrendsScatter from './components/TrendsScatter.svelte';

  import { selectedCountries, dateRange, showEvents, selectedYearMonth } from './lib/stores.js';
  import {
    loadData,
    computeCountryAverages,
    computeTimeSeries,
    loadThemesData,
  } from './lib/data.js';

  // ── Scrolly stage definitions ───────────────────────────────────────────────
  const stages = [
    {
      id: 'intro',
      range: null,
      eyebrow: 'Setting the scene',
      title: 'How the world stopped watching',
      body: `When Russia invaded Ukraine on 24 February 2022, the world's
             newsrooms pivoted in unison. Four years on, the same war barely
             registers in most of them. Scroll to see how attention moved —
             and where it stayed.`,
    },
    {
      id: 'shock',
      range: ['2022-02-01', '2022-03-31'],
      rangeLabel: 'Feb–Mar 2022',
      eyebrow: 'February 2022',
      title: 'The shock',
      body: `In the weeks after the invasion, the share of news reports
             mentioning Ukraine or Russia roughly quadrupled in most
             countries. The map is uniformly red: from Reykjavík to Jakarta,
             it was the story.`,
      callout: `Coverage spiked even in countries with little direct
                exposure to the conflict — a rare moment of global news
                consensus.`,
    },
    {
      id: 'anniversary',
      range: ['2023-02-01', '2023-03-31'],
      rangeLabel: 'Feb–Mar 2023',
      eyebrow: 'February 2023',
      title: 'The anniversary',
      body: `One year on, coverage spiked again — about 1.5× the preceding
             months. Biden's surprise visit to Kyiv, the Munich Security
             Conference and a G7 summit clustered around the anniversary,
             pulling editorial attention back to the story.`,
      callout: `Anniversary journalism is its own genre: the news cycle
                remembers on schedule, even when the war itself does not
                follow one.`,
    },
    {
      id: 'fade',
      range: ['2024-08-01', '2024-09-30'],
      rangeLabel: 'Aug–Sep 2024',
      eyebrow: 'August 2024',
      title: 'The fade',
      body: `By late 2024 the war is in its third year. Ukraine launches a
             cross-border incursion into Russia's Kursk region — a story
             that would have dominated 2022 — and most of the world's
             media barely notice. Gaza has absorbed the attention budget.`,
      callout: `Only Ukraine's immediate neighbours and a handful of
                politically engaged outlets keep the story near the top of
                their agenda.`,
    },
    {
      id: 'now',
      range: ['2025-08-01', null],
      rangeLabel: 'Aug 2025 – present',
      eyebrow: 'Late 2025 onward',
      title: 'Back on the agenda',
      body: `A flurry of diplomatic activity — a US–Russia summit pitched as
             a path to a ceasefire, follow-on negotiations that produced
             none — has pulled the war back into the news. The map is not
             as red as 2022, but it is no longer pale.`,
      callout: `Attention now tracks the diplomatic calendar more than the
                battlefield.`,
    },
    {
      id: 'who-reports',
      range: null,
      eyebrow: 'Taking stock',
      title: 'Who keeps reporting?',
      body: `Averaged over the full period, three patterns explain who keeps
             covering the war. Toggle between them.`,
      highlightOptions: ['Proximity', 'Economic ties', 'Political ties'],
    },
    {
      id: 'audience',
      range: null,
      eyebrow: 'Search vs press',
      title: 'And what did the audience actually want?',
      body: `Press attention is not the same as public attention. We pair each
             country's share of war coverage in its own media — with its audience's share of Google searches
             for war-specific terms ("Ukraine war", "Russian invasion", and
             native-script equivalents) in the script they use most: English,
             Russian, Chinese, Arabic or Japanese. Countries above the dashed
             line searched more than their press supplied; countries below it
             were covered more heavily than their audience asked.`,
      callout: `Caveats: Google Trends excludes Yandex (Russia), Baidu (China)
                and Naver (Korea); the five-language max-aggregator is a
                heuristic`,
    },
  ];

  // FIPS 10-4 codes for regions of interest (who-reports stage)
  const EU_AS_ME_FIPS = new Set([
    // Europe
    'AL','AN','AU','BE','BO','BU','CY','EZ','DA','EN','FI','FR','GM','GR',
    'HU','IC','EI','IT','LG','LH','LO','LU','MK','MT','MD','MN','MJ','NL',
    'NO','PL','PO','RO','RI','SM','SI','SP','SW','SZ','UP','UK',
    'VT','RS','BK','HR','MW','KV','RB',
    // Asia
    'AF','BG','BX','BM','CB','CH','TW','IN','ID','JA','KZ','KG','KN','KS',
    'LA','MY','MV','MG','NP','PK','RP','SN','CE','TH','TI','TX','VM',
    // Middle East
    'AR','BA','IZ','IR','IS','JO','KU','LE','MU','OM','QA','SA','SY','TC',
    'TS','AE','YM','EG',
  ]);
  const ECONOMIC_FIPS = new Set(['AO', 'EG', 'SU']); // Angola, Egypt, Sudan
  const POLITICAL_FIPS = new Set(['ML', 'LY', 'CT', 'CU']); // Mali, Libya, CAR, Cuba

  // ── Scrolly state ───────────────────────────────────────────────────────────
  let activeStep = 0;
  let highlightMode = 'Proximity';

  $: activeStage = stages[activeStep];

  $: stageDateRange = (() => {
    if (!activeStage?.range || !minDate || !maxDate) return null;
    const [s, e] = activeStage.range;
    const start = s ? new Date(s) : minDate;
    const end   = e ? new Date(e) : maxDate;
    return [
      start < minDate ? minDate : start,
      end   > maxDate ? maxDate : end,
    ];
  })();

  $: scrollyCountryAverages =
    dateMap && fipsToNumeric && numericToName
      ? computeCountryAverages(
          dateMap,
          stageDateRange ?? [minDate ?? new Date('2022-02-01'), maxDate ?? new Date()],
          fipsToNumeric,
          numericToName
        )
      : new Map();

  $: sparklineSeries =
    dateMap && minDate && maxDate
      ? computeTimeSeries(dateMap, new Set(), [minDate, maxDate])
      : [];

  $: localHighEU_AS_ME = (() => {
    if (activeStage?.id !== 'who-reports') return new Set();
    if (!scrollyCountryAverages || scrollyCountryAverages.size === 0) return new Set();
    const out = new Set();
    for (const [, info] of scrollyCountryAverages) {
      if (info.avgRatio > 0.08 && EU_AS_ME_FIPS.has(info.fips)) out.add(info.fips);
    }
    return out;
  })();

  $: highlightedFips = (() => {
    if (activeStage?.id !== 'who-reports') return new Set();
    if (highlightMode === 'Proximity')     return localHighEU_AS_ME;
    if (highlightMode === 'Economic ties') return ECONOMIC_FIPS;
    if (highlightMode === 'Political ties') return POLITICAL_FIPS;
    return new Set();
  })();

  // Reactive scale so the choropleth fits the scrolly viz column
  let scrollyVizW = 0;
  $: choroplethScale = scrollyVizW > 0 ? Math.min(1, scrollyVizW / 960) : 1;
  $: choroplethScaledH = Math.round(536 * choroplethScale); // 500 + 36 legend

  // ── Loaded state ─────────────────────────────────────────────────────────────
  let ready = false;
  let loadError = null;

  let dateMap = null;
  let fipsToName = null;
  let fipsToNumeric = null;
  let numericToFips = null;
  let numericToName = null;
  let minDate = null;
  let maxDate = null;

  let topology = null;

  let globalThemes = null;
  let countryThemes = null;

  // ── Explore section reactives (unchanged) ────────────────────────────────────
  $: countryAverages =
    dateMap && $dateRange && fipsToNumeric && numericToName
      ? computeCountryAverages(dateMap, $dateRange, fipsToNumeric, numericToName)
      : new Map();

  $: timeSeriesData =
    dateMap && $dateRange
      ? computeTimeSeries(dateMap, $selectedCountries, $dateRange)
      : [];

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
      const [data, topo, themes] = await Promise.all([
        loadData(),
        d3.json('/data/countries-110m.json'),
        loadThemesData(),
      ]);

      ({ dateMap, fipsToName, fipsToNumeric, numericToFips, numericToName, minDate, maxDate } = data);
      topology = topo;
      ({ globalThemes, countryThemes } = themes);

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

    <!-- ── Prose intro ───────────────────────────────────────────────── -->
    <section class="intro">
      <p>
        Russia's invasion of Ukraine in February 2022 was, briefly, the only
        story in the world. Four years later, the same war competes for
        attention with Gaza, US politics, and a dozen other crises — and
        mostly loses. This piece tracks the share of news reports mentioning
        the war in each country's media, month by month, from the invasion
        to today.
      </p>
    </section>

    <!-- ── Scrolly ──────────────────────────────────────────────────── -->
    <Scrolly bind:activeStep autoScroll={true} stopAtStep={stages.length - 1}>
      {#each stages as stage}
        <section class="step step--{stage.id}">
          {#if stage.eyebrow}
            <div class="step-eyebrow">{stage.eyebrow}</div>
          {/if}
          <h2>{stage.title}</h2>
          <p>{stage.body}</p>
          {#if stage.callout}
            <div class="callout">{stage.callout}</div>
          {/if}
          {#if stage.id === 'who-reports'}
            <div class="highlight-toggle">
              {#each stage.highlightOptions as opt}
                <button
                  class:active={highlightMode === opt}
                  on:click={() => highlightMode = opt}
                >{opt}</button>
              {/each}
              <div class="highlight-legend">
                {#if highlightMode === 'Proximity'}
                  European, Asian and Middle Eastern countries averaging
                  over 8% war-related coverage.
                {:else if highlightMode === 'Economic ties'}
                  Major North African wheat importers from Russia and
                  Ukraine: Angola, Egypt, Sudan.
                {:else if highlightMode === 'Political ties'}
                  Countries with historic or current alignment with Russia:
                  Mali, Libya, the Central African Republic, Cuba.
                {/if}
              </div>
            </div>
          {/if}
        </section>
      {/each}

      <svelte:fragment slot="viz">
        <div class="scrolly-viz-stack" bind:clientWidth={scrollyVizW}>
          {#if activeStage?.id === 'audience'}
            <div
              class="scatter-scaler"
              style="width:960px; transform:scale({choroplethScale}); transform-origin:top left;"
            >
              <TrendsScatter />
            </div>
          {:else}
            <Sparkline
              data={sparklineSeries}
              activeRange={stageDateRange}
              label={activeStage?.rangeLabel ?? (activeStage?.id === 'intro' ? '' : 'Full period')}
            />
            <div
              class="choropleth-scaler"
              style="width:960px; height:{choroplethScaledH}px; transform:scale({choroplethScale}); transform-origin:top left;"
            >
              <Choropleth
                {topology}
                countryAverages={scrollyCountryAverages}
                interactive={false}
                highlightFips={activeStage?.id === 'who-reports' ? highlightedFips : new Set()}
              />
            </div>
          {/if}
        </div>
      </svelte:fragment>
    </Scrolly>

    <!-- ── Explore section ──────────────────────────────────────────── -->
    <section class="explore">
      <div class="explore-header">
        <h2>Now your turn</h2>
        <p>
          Scrub the date range, click countries on the map to build a
          comparison, toggle key events on the time series, and explore
          the themes dominating coverage in each month.
        </p>
      </div>

      <div class="controls">
        {#if $selectedCountries.size > 0}
          <button class="clear-btn" on:click={clearSelection}>
            Clear selection ({$selectedCountries.size} {$selectedCountries.size === 1 ? 'country' : 'countries'})
          </button>
        {:else}
          <span class="hint">Click a country on the map to compare its coverage rate</span>
        {/if}
      </div>

      <section class="section-map">
        <Choropleth {topology} {countryAverages} />
      </section>

      <section class="section-ts">
        <div class="ts-header">
          <span class="ts-title">
            {$selectedCountries.size === 0 ? 'Global coverage rate' : `Coverage rate – ${tsLabel}`}
          </span>
          <span class="ts-note">7-day rolling average</span>
          <label class="events-toggle">
            <input type="checkbox" bind:checked={$showEvents} />
            Show key events
          </label>
        </div>
        <TimeSeries
          {timeSeriesData}
          dateRange={$dateRange}
          label={tsLabel}
          showEvents={$showEvents}
          highlightMonth={$selectedYearMonth}
        />
      </section>

      <section class="section-brush">
        <div class="brush-label">Filter date range</div>
        <DateRangeSlider {minDate} {maxDate} />
      </section>

      {#if globalThemes && countryThemes}
        <ThemesPanel {globalThemes} {countryThemes} />
      {/if}
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

  /* ── Header ─────────────────────────────────────────────────────────── */
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

  /* ── Prose intro ─────────────────────────────────────────────────────── */
  .intro {
    max-width: 640px;
    margin: 2rem 0 1rem;
    font-family: var(--serif);
    font-size: 17px;
    line-height: 1.6;
    color: #222;
  }

  /* ── Scrolly viz stack ───────────────────────────────────────────────── */
  .scrolly-viz-stack {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    overflow: hidden;
    width: 100%;
  }

  .choropleth-scaler {
    overflow: hidden;
  }

  /* ── Step heights ────────────────────────────────────────────────────── */
  :global(.step--intro)        { min-height: 70vh; }
  :global(.step--shock)        { min-height: 110vh; }
  :global(.step--anniversary)  { min-height: 85vh; }
  :global(.step--fade)         { min-height: 115vh; }
  :global(.step--now)          { min-height: 90vh; }
  :global(.step--who-reports)  { min-height: 130vh; }
  :global(.step--audience)     { min-height: 110vh; }

  /* ── Who-reports toggle ──────────────────────────────────────────────── */
  .highlight-toggle {
    margin-top: 1rem;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    font-family: var(--sans);
  }
  .highlight-toggle button {
    background: #f3f3f3;
    border: 1px solid #ddd;
    color: #333;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 3px;
    cursor: pointer;
  }
  .highlight-toggle button.active {
    background: #1a3a6b;
    color: #fff;
    border-color: #1a3a6b;
  }
  .highlight-legend {
    flex-basis: 100%;
    font-family: var(--sans);
    font-size: 12px;
    color: #555;
    margin-top: 0.4rem;
    line-height: 1.4;
  }

  /* ── Explore section ─────────────────────────────────────────────────── */
  .explore {
    border-top: 1px solid #ddd;
    margin-top: 4rem;
    padding-top: 2rem;
  }
  .explore-header {
    max-width: 640px;
    margin: 0 0 1.5rem;
  }
  .explore-header h2 {
    font-family: var(--serif);
    font-size: 22px;
    margin: 0 0 0.5rem;
    color: #111;
  }
  .explore-header p {
    font-family: var(--serif);
    font-size: 15px;
    line-height: 1.55;
    color: #333;
    margin: 0;
  }

  /* ── Controls ────────────────────────────────────────────────────────── */
  .controls {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 10px 0 4px;
    font-family: var(--sans);
    font-size: 13px;
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

  /* ── Explore chart sections ───────────────────────────────────────────── */
  .section-map {
    margin-top: 6px;
  }

  .section-ts {
    margin-top: 20px;
  }

  .ts-header {
    display: flex;
    align-items: center;
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

  .events-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    cursor: pointer;
    color: #333;
    font-family: var(--sans);
    font-size: 13px;
  }

  .events-toggle input {
    cursor: pointer;
    accent-color: #c0392b;
  }

  .section-brush {
    margin-top: 12px;
  }

  .brush-label {
    font-family: var(--sans);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #999;
    margin-bottom: 2px;
  }

  /* ── Loading / error ─────────────────────────────────────────────────── */
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

  /* ── Footer ──────────────────────────────────────────────────────────── */
  .page-footer {
    margin-top: 32px;
    border-top: 1px solid #eee;
    padding-top: 10px;
    font-family: var(--sans);
    font-size: 11px;
    color: #bbb;
  }
</style>
