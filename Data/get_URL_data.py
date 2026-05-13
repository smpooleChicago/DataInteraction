"""
Article URL sampling per (country, year_month, theme).
========================================================

Adds Level 1 article provenance to your dashboard: 5 sample article URLs
per (country, year_month, theme) for every (country, year_month, theme)
already in your themes_by_country_month table.

Output:
  articles_by_country_month_theme.csv
    columns: year_month, country, theme, url, source_name, sample_rank

Assumes themes_by_country_month already exists in BigQuery from the
previous step. If not, run that pipeline first.

Test-run parameters: see TEST RUN block below.
"""

import os
from google.cloud import bigquery

# ---- CONFIG --------------------------------------------------------------
PROJECT_ID    = "project-88c1534c-6f20-45b7-a22"
DATASET_ID    = "gdelt_ru_ua"
LOOKUP_TABLE  = "domain_country_lookup"
THEMES_TABLE  = "themes_by_country_month"     # pre-existing from prior step
ARTICLES_TABLE = "articles_by_country_month_theme"
OUT_CSV       = "articles_by_country_month_theme.csv"
# Keep these in sync with get_themes.py
NOISE_PREFIXES = [
    "TAX_FNCACT_",
    "TAX_ETHNICITY_",
    "TAX_RELIGION_",
    "TAX_WORLDLANGUAGES_",
    "TAX_WORLDMAMMALS_",
    "TAX_WORLDBIRDS_",
    "TAX_FOODSTAPLES_",
    "TAX_WORLDFISH_",
    "TAX_DISEASE_",
    "EPU_",
    "WB_",
    "CRISISLEX_",
    "USPEC_",
    "SOC_",
    "EDUCATION",
    "GENERAL_",
    "MOVEMENT_GENERAL",
    "LEADER",
    "GOV_",
    "MEDIA_",
    "BUREAUCRACY",
    "ECON_",
    "UNGP_",
    "HEALTH_",
]

NOISE_EXACT = [
    "MANMADE_DISASTER_IMPLIED",
    "MEDICAL",
    "TAX_ECON_PRICE",
    "AFFECT",
    "DELAY",
    "SCIENCE",
    "LEGISLATION",
    "TRIAL",
]

# ============================================================
# TEST RUN: set to one month first to verify cost + correctness.
# For the full run, change to your full data range.
# ------------------------------------------------------------
START_DATE    = "2022-02-01"
#END_DATE      = "2022-04-01"     # <-- TEST: one month
END_DATE    = "2026-06-01"     # <-- FULL: uncomment for production run
# ============================================================

SAMPLES_PER_THEME = 5     # URLs per (country, year_month, theme)

client = bigquery.Client(project=PROJECT_ID)


def build_articles_table():
    """
    Pulls one URL sample per (country, year_month, theme) where the theme
    is in the top-N for that (country, year_month) per the existing
    themes_by_country_month table.

    Why filter to top-N themes? Otherwise we'd be sampling URLs for every
    one of ~12,000 GDELT themes per (country, month) — millions of rows
    of mostly useless data. We only care about themes the user can
    actually see in the dashboard.
    """
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{ARTICLES_TABLE}"
    noise_clause = " AND ".join(
    f"NOT STARTS_WITH(theme, '{p}')" for p in NOISE_PREFIXES)
    exact_clause = "AND theme NOT IN ({})".format(
        ", ".join(f"'{t}'" for t in NOISE_EXACT))
    sql = f"""
    CREATE OR REPLACE TABLE `{table_id}` AS

    WITH
    -- Step 1: get (country, year_month, theme) combos we care about
    -- (i.e., themes that made the top-N list in the themes table).
    target_themes AS (
      SELECT DISTINCT country, year_month, theme
      FROM `{PROJECT_ID}.{DATASET_ID}.{THEMES_TABLE}`
    ),

    -- Step 2: re-explode GKG over the date range, keeping URL + outlet
    -- alongside each theme. Same shape as the themes pipeline, but we
    -- preserve DocumentIdentifier and SourceCommonName.
    article_themes AS (
      SELECT
        FORMAT_DATE('%Y-%m',
          DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING)))
        ) AS year_month,
        NET.REG_DOMAIN(DocumentIdentifier) AS domain,
        DocumentIdentifier AS url,
        SourceCommonName AS source_name,
        SPLIT(theme_with_offset, ',')[OFFSET(0)] AS theme
      FROM `gdelt-bq.gdeltv2.gkg_partitioned`,
      UNNEST(SPLIT(V2Themes, ';')) AS theme_with_offset
      WHERE _PARTITIONTIME BETWEEN TIMESTAMP('{START_DATE}') AND TIMESTAMP('{END_DATE}')
        AND LOWER(DocumentIdentifier) LIKE 'http%'
        AND V2Themes IS NOT NULL
        AND V2Themes != ''
        AND theme_with_offset != ''
    ),

    -- Step 3: attach country via the domain lookup.
    joined AS (
      SELECT
        a.year_month, a.theme, a.url, a.source_name,
        l.source_country AS country
      FROM article_themes a
      JOIN `{PROJECT_ID}.{DATASET_ID}.{LOOKUP_TABLE}` l USING (domain)
      WHERE a.theme IS NOT NULL AND a.theme != ''
      AND {noise_clause}
        {exact_clause}
    ),

    -- Step 4: restrict to (country, year_month, theme) combos that
    -- actually appear in the themes table. Inner join filters out the
    -- ~12k themes we don't display.
    -- Filter to top-N themes
    filtered AS (
    SELECT j.year_month, j.country, j.theme, j.url, j.source_name
    FROM joined j
    JOIN target_themes t
    USING (country, year_month, theme)
    ),

    -- NEW STEP: deduplicate URLs within each (country, year_month, theme)
    deduped AS (
    SELECT
        year_month, country, theme, url,
        ANY_VALUE(source_name) AS source_name
    FROM filtered
    GROUP BY year_month, country, theme, url
    ),

    -- Now the ranking step operates on unique URLs
    ranked AS (
    SELECT
        year_month, country, theme, url, source_name,
        ROW_NUMBER() OVER (
        PARTITION BY country, year_month, theme
        ORDER BY FARM_FINGERPRINT(url)
        ) AS sample_rank
    FROM deduped
    )

    SELECT *
    FROM ranked
    WHERE sample_rank <= {SAMPLES_PER_THEME}
    """

    # Dry run for cost
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = dry.total_bytes_processed / 1e9
    print(f"Will scan ~{gb:.1f} GB (≈ ${gb * 6.25 / 1000:.2f} on-demand)")
    print(f"Date range: {START_DATE} -> {END_DATE}")
    print(f"Samples per (country, year_month, theme): {SAMPLES_PER_THEME}")

    if input("Proceed? [y/N]: ").strip().lower() != "y":
        print("Aborted.")
        return None

    print("Running query...")
    client.query(sql).result()

    n = client.get_table(table_id).num_rows
    print(f"Materialized {n:,} article samples")
    return table_id


def export_csv():
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{ARTICLES_TABLE}"

    sql = f"""
        SELECT year_month, country, theme, url, source_name, sample_rank
        FROM `{table_id}`
        ORDER BY year_month, country, theme, sample_rank
    """
    df = client.query(sql).to_dataframe()
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(df):,} rows to {OUT_CSV}")

    # Quick spot-check
    print(f"\n  Distinct (country, year_month, theme) combos: "
          f"{df.groupby(['country','year_month','theme']).ngroups:,}")
    print(f"  Distinct outlets:    {df['source_name'].nunique():,}")
    print(f"  Date range:          {df['year_month'].min()} -> {df['year_month'].max()}")
    print(f"  Countries:           {df['country'].nunique()}")

    print("\n  Sample rows for theme=ARMEDCONFLICT, country=US:")
    sample = df[(df['country'] == 'US') & (df['theme'] == 'ARMEDCONFLICT')].head(10)
    if len(sample):
        print(sample[['year_month','source_name','url']].to_string(index=False))
    else:
        print("  (no rows — theme/country may not be in test month)")


if __name__ == "__main__":
    if build_articles_table() is not None:
        export_csv()