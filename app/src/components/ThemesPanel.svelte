<script>
  import { onMount, onDestroy } from 'svelte';
  import { selectedCountries, selectedYearMonth } from '../lib/stores.js';
  import { computeTopThemes, ensureArticlesLoaded, queryArticles } from '../lib/data.js';
  import MonthYearPicker from './MonthYearPicker.svelte';
  import ThemeChips from './ThemeChips.svelte';
  import ArticleList from './ArticleList.svelte';

  // Pre-loaded theme maps passed from App.svelte
  export let globalThemes;   // Map<year_month, Array<{theme, theme_count, rank}>>
  export let countryThemes;  // Map<year_month, Map<fips, Array<{theme, theme_count, rank}>>>

  let selectedTheme = null;
  let articles = null;
  let loadingArticles = false;

  // Info bubble state
  let infoOpen = false;
  let infoEl;   // wraps the "i" button + popup — used for click-outside detection

  function handleDocClick(e) {
    if (infoOpen && infoEl && !infoEl.contains(e.target)) infoOpen = false;
  }
  onMount(()  => document.addEventListener('click', handleDocClick, true));
  onDestroy(() => document.removeEventListener('click', handleDocClick, true));

  // Top-5 themes for the current (yearMonth × country selection) combination.
  $: top5 = computeTopThemes($selectedYearMonth, $selectedCountries, globalThemes, countryThemes);

  // Reset chip and article pane whenever the data context changes.
  let _prevYM = null;
  let _prevCountries = null;
  $: {
    const ym = $selectedYearMonth;
    const countries = $selectedCountries;
    if (ym !== _prevYM || countries !== _prevCountries) {
      selectedTheme = null;
      articles = null;
      _prevYM = ym;
      _prevCountries = countries;
    }
  }

  async function handleThemeSelect(event) {
    const theme = event.detail;
    selectedTheme = theme;
    articles = null;

    if (!theme || !$selectedYearMonth) return;

    loadingArticles = true;
    try {
      await ensureArticlesLoaded();
      articles = queryArticles($selectedYearMonth, $selectedCountries, theme);
    } finally {
      loadingArticles = false;
    }
  }

  // Human-readable month label for the panel header.
  const MONTH_NAMES = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December',
  ];

  function ymLabel(ym) {
    if (!ym) return '';
    const [y, m] = ym.split('-');
    return `${MONTH_NAMES[+m - 1]} ${y}`;
  }
</script>

<!-- Stop propagation so clicks inside the panel don't bubble to choropleth/timeseries -->
<!-- svelte-ignore a11y-no-static-element-interactions a11y-click-events-have-key-events -->
<section
  class="themes-panel"
  on:click|stopPropagation
  on:mousedown|stopPropagation
>
  <div class="panel-header">
    <span class="panel-title">Top themes by month</span>
    {#if $selectedCountries.size > 0}
      <span class="panel-scope">
        · {$selectedCountries.size === 1 ? '1 country selected' : `${$selectedCountries.size} countries selected`}
      </span>
    {:else}
      <span class="panel-scope">· global</span>
    {/if}
  </div>

  <div class="picker-row">
    <MonthYearPicker />
    <div class="info-wrap" bind:this={infoEl}>
      <!-- svelte-ignore a11y-no-static-element-interactions a11y-click-events-have-key-events -->
      <button
        class="info-btn"
        aria-label="How this works"
        aria-expanded={infoOpen}
        on:click|stopPropagation={() => infoOpen = !infoOpen}
      >i</button>
      {#if infoOpen}
        <div class="info-bubble" role="tooltip">
          Choose a year and month to reveal the top&nbsp;5 news themes dominating
          coverage during that period. If countries are selected on the map,
          themes reflect their media only; otherwise they show global totals.
          Click a theme chip to load sample article links sourced directly
          from GDELT.
        </div>
      {/if}
    </div>
  </div>

  {#if $selectedYearMonth}
    <div class="themes-box">
      <div class="box-head">
        <span class="box-period">{ymLabel($selectedYearMonth)}</span>
        <span class="box-hint">— top 5 themes, click to see sample articles</span>
      </div>

      {#if top5.length > 0}
        <ThemeChips
          themes={top5}
          selected={selectedTheme}
          on:select={handleThemeSelect}
        />

        <ArticleList
          articles={selectedTheme ? articles : null}
          loading={loadingArticles}
        />
      {:else}
        <p class="no-themes">No theme data for this month/selection.</p>
      {/if}
    </div>
  {/if}
</section>

<style>
  .themes-panel {
    border-top: 1px solid #ddd;
    padding-top: 24px;
    margin-top: 28px;
    font-family: var(--sans);
  }

  /* ── Header ── */
  .panel-header {
    display: flex;
    align-items: baseline;
    gap: 6px;
    margin-bottom: 14px;
  }

  .panel-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #999;
    font-weight: 600;
  }

  .panel-scope {
    font-size: 11px;
    color: #bbb;
  }

  /* ── Picker row ── */
  .picker-row {
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  /* ── Info bubble ── */
  .info-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }

  .info-btn {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 1px solid #bbb;
    background: none;
    font-family: var(--serif);
    font-size: 11px;
    font-style: italic;
    color: #888;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    flex-shrink: 0;
    line-height: 1;
    transition: border-color 0.12s, color 0.12s;
  }

  .info-btn:hover {
    border-color: #777;
    color: #444;
  }

  .info-bubble {
    position: absolute;
    top: calc(100% + 7px);
    left: 0;
    z-index: 200;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px 13px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.1);
    font-family: var(--sans);
    font-size: 12.5px;
    color: #444;
    line-height: 1.55;
    width: 280px;
  }

  /* ── Themes box ── */
  .themes-box {
    border: 1px solid #e8e8e8;
    padding: 16px 18px 18px;
    border-radius: 2px;
  }

  .box-head {
    margin-bottom: 14px;
  }

  .box-period {
    font-size: 13.5px;
    font-weight: 600;
    color: #111;
  }

  .box-hint {
    font-size: 12px;
    color: #bbb;
    margin-left: 4px;
  }

  .no-themes {
    font-size: 12.5px;
    color: #aaa;
    margin: 0;
  }
</style>
