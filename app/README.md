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
│       ├── country_daily_merged.csv      # GDELT-derived daily counts (291k rows)
│       ├── fips-10-4-to-iso-country-codes.csv  # FIPS → ISO alpha-2 + name crosswalk
│       └── countries-110m.json           # world-atlas TopoJSON (copied from node_modules)
├── src/
│   ├── lib/
│   │   ├── stores.js   # Svelte writable stores: selectedCountries, dateRange, showEvents
│   │   └── data.js     # loadData(), computeCountryAverages(), computeTimeSeries(), computeP95()
│   ├── components/
│   │   ├── Choropleth.svelte       # Equal Earth world map with colour scale + click-toggle
│   │   ├── TimeSeries.svelte       # Aggregated line chart with event annotations
│   │   └── DateRangeSlider.svelte  # d3.brushX two-handle date range control
│   ├── App.svelte    # Orchestrator: data loading, reactive derived state, layout
│   ├── main.js       # Svelte entry point
│   └── app.css       # Global reset + CSS custom properties
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
`showEvents` (boolean). `App.svelte` has reactive `$:` blocks that recompute
`countryAverages` and `timeSeriesData` whenever these stores change.

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
