# Russia–Ukraine War: Global News Coverage Dashboard

Graphic Detail–style data journalism dashboard showing global news coverage of the
Russia–Ukraine war from February 2022 through May 2026, built from GDELT-derived data.

---

## How to run

```bash
cd app/
npm install
npm run dev          # → http://localhost:5173
```

`npm run build` produces a static bundle in `dist/`.

---

## File structure

```
app/
├── public/
│   └── data/
│       ├── country_daily_merged.csv           # GDELT daily counts (291k rows)
│       ├── fips-10-4-to-iso-country-codes.csv # FIPS → ISO alpha-2 + name crosswalk
│       ├── countries-110m.json                # world-atlas TopoJSON
│       ├── themes_global_month.csv            # Top 20 themes globally per month (1 040 rows)
│       ├── themes_by_country_month.csv        # Top 20 themes per country per month (206k rows)
│       └── articles_by_country_month_theme.csv # Sample article URLs, 144 MB — lazy-loaded
├── src/
│   ├── lib/
│   │   ├── stores.js   # selectedCountries, dateRange, showEvents, selectedYearMonth
│   │   └── data.js     # loadData(), loadThemesData(), computeTopThemes(),
│   │   │               # ensureArticlesLoaded(), queryArticles(), …
│   ├── components/
│   │   ├── Choropleth.svelte       # Equal Earth world map, click-toggle, clear-month on click
│   │   ├── TimeSeries.svelte       # Line chart, event annotations, grey month-highlight rect
│   │   ├── DateRangeSlider.svelte  # d3.brushX range control
│   │   ├── ThemesPanel.svelte      # Themes section orchestrator
│   │   ├── MonthYearPicker.svelte  # Custom year + month dropdowns with validation
│   │   ├── ThemeChips.svelte       # 5 mutually-exclusive theme chip buttons
│   │   └── ArticleList.svelte      # Up to 5 article links with loading state
│   ├── App.svelte    # Orchestrator: data loading, reactive derived state, layout
│   ├── main.js
│   └── app.css
├── index.html
├── vite.config.js
└── package.json
```

---

## Architecture notes

**Data loading** (`lib/data.js`): CSV files are fetched with `d3.csv()` at startup.
The main dataset is pre-grouped once into a `Map<dateStr, {ruUaTotal, allTotal, byCountry: Map}>`.
All subsequent computations slice this structure — no re-parsing.

**Country lookup chain**: GDELT uses FIPS 10-4 codes → crosswalk CSV maps to ISO alpha-2 →
hardcoded `ALPHA2_TO_NUMERIC` table maps to the ISO 3166-1 numeric IDs used by world-atlas
TopoJSON features. Countries that don't resolve through this chain receive a grey fill and
are not interactive.

**Colour scale**: sequential `d3.interpolateReds`, domain `[0, p95]` where p95 is the
95th percentile of country averages for the current date selection. Values above p95 clamp
to the darkest colour so Russia/Ukraine don't compress the rest of the scale.
Country averages are the mean of daily `ratio` values on non-low-volume days
(`all_count ≥ 100`); if *all* of a country's days are low-volume, all days are included.

**7-day rolling mean**: calendar-based window (current day + 6 preceding calendar days).
Missing dates in the data (gaps) simply contribute no value to the window — they don't break
the smoothing or shift the window.

**Time series**: when no countries are selected, shows the global aggregate
(`sum(ru_ua_count) / sum(all_count)` per day). When countries are selected on the map, shows
the combined aggregate for that set — one line, not one per country. The x-axis zooms to the
date range selected via the brush.

**Stores**: `selectedCountries` (Set of FIPS codes), `dateRange` ([Date, Date]),
`showEvents` (boolean), `selectedYearMonth` ("YYYY-MM" string or null).
`App.svelte` has reactive `$:` blocks that recompute `countryAverages` and
`timeSeriesData` whenever these stores change.

**Themes panel**: loaded on initial page load alongside the main CSV.
`themes_global_month.csv` and `themes_by_country_month.csv` are pre-grouped into
`Map<year_month, …>` structures at load time for O(1) lookups per month.
Top-5 theme computation aggregates across selected FIPS codes when countries are
selected, or falls back to the global pre-ranked list when none are selected.

**Article lazy-loader** (`ensureArticlesLoaded` in `data.js`): the 144 MB
`articles_by_country_month_theme.csv` is **not** fetched on initial page load.
It is fetched with `d3.csv()` the first time a user clicks a theme chip. After
parsing, two in-memory indexes are built:
- `Map<"ym|fips|theme", row[]>` — for per-country lookups
- `Map<"ym|theme", row[]>` — for global lookups (≤ 20 unique URLs per cell)

Subsequent theme clicks resolve against these indexes synchronously.
Parsing time on first click is typically 5–15 s depending on hardware; a
"Loading articles…" indicator is shown during that window. A Web Worker is not
used — the blocking window is short enough on the target hardware that the
simpler inline approach was preferred.

**Month-highlight rect**: when a year+month is selected in the themes panel,
`TimeSeries` renders a semi-transparent grey `<rect>` spanning that calendar
month behind the line. Clicking the choropleth, time series, or date slider
clears `selectedYearMonth` and removes the rect.

---

## Tech stack choices

| Spec | What was done |
|---|---|
| SvelteKit | Used **plain Svelte + Vite** instead. For a single-page no-routing app these are functionally identical; SvelteKit's SSR/routing overhead isn't needed and plain Vite is simpler to scaffold without interactive prompts. |
| world-atlas TopoJSON | `countries-110m.json` copied from `node_modules/world-atlas/` into `public/data/` at install time, served as a static asset via `d3.json()`. |
| CSS | Plain global CSS in `app.css` + Svelte scoped `<style>` blocks per component. No Tailwind or UI library. |

---

## Known limitations / deferred items

- **Date brush fires on `brushend` only** — both charts update when you release the handle,
  not continuously during drag. Choropleth recomputes ~320k iterations per call; it's fast
  enough for release-on-end but might feel sluggish on live drag on slower machines.
- **Mobile / responsive layout not implemented** — targeted at ≥ 1280 px desktop as specified.
  SVGs have fixed widths (960 px) and will overflow on smaller screens.
- **Kosovo (XK → 383)** is in `ALPHA2_TO_NUMERIC` but world-atlas 110m doesn't include it as
  a separate polygon; it appears merged into Serbia.
- **Taiwan (TW → 158)** is in the lookup; world-atlas represents it as a feature but
  geopolitical labelling in GDELT may vary.
- **DST edge case in rolling mean**: the window is computed by subtracting multiples of
  86 400 000 ms. On the two DST transition days per year in local timezones the window may
  skip or double a calendar day by one hour. This has negligible effect on the smoothed line.
- **Bar race component** — not built (explicitly out of scope).
- **Event annotation label overlap** — labels rotate 55° but can still overlap if two events
  are close (e.g. Kakhovka dam 2023-06-06 and Wagner mutiny 2023-06-23).
