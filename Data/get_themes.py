"""
Per-country monthly theme frequency for GDELT GKG.
====================================================

Produces two CSVs:
  - themes_by_country_month.csv : top 20 themes per (country, year_month)
  - themes_global_month.csv     : top 20 themes globally per year_month

Strategy:
  1. Unnest V2Themes (semicolon-delimited) into one row per (article, theme)
  2. Join domain -> country
  3. Filter out known-noise theme prefixes
  4. Count per (country, year_month, theme); keep top 20 per (country, year_month)
  5. Roll up globally for the global CSV

Run THIS FIRST. The article-sampling script depends on the materialized
themes_by_country_month table.
"""

import os
from google.cloud import bigquery

# ---- CONFIG --------------------------------------------------------------
PROJECT_ID    = "project-88c1534c-6f20-45b7-a22"
DATASET_ID    = "gdelt_ru_ua"
LOOKUP_TABLE  = "domain_country_lookup"
THEMES_TABLE  = "themes_by_country_month"
OUT_PER_COUNTRY = "themes_by_country_month.csv"
OUT_GLOBAL      = "themes_global_month.csv"

# ============================================================
# TEST RUN: set to one month first to verify cost + theme quality.
# For the full run, change END_DATE.
# ------------------------------------------------------------
START_DATE    = "2022-02-01"
#END_DATE      = "2022-04-01"     # <-- TEST: one month
END_DATE    = "2026-06-01"     # <-- FULL: uncomment for production run
# ============================================================

TOP_N = 20   # store top 20 per (country, month); frontend displays 5

# GDELT theme noise blocklist. These prefixes dominate raw frequency and
# are journalistically meaningless. Trim/extend as you eyeball output.
# Keep this list in sync with the article-sampling script.
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

client = bigquery.Client(project=PROJECT_ID)


def build_themes_table():
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{THEMES_TABLE}"
    noise_clause = " AND ".join(
        f"NOT STARTS_WITH(theme, '{p}')" for p in NOISE_PREFIXES
    )
    exact_clause = "AND theme NOT IN ({})".format(
    ", ".join(f"'{t}'" for t in NOISE_EXACT))
    sql = f"""
    CREATE OR REPLACE TABLE `{table_id}` AS

    WITH
    -- Pull GKG rows in range; project only the columns we need (column
    -- pruning is the main cost lever).
    gkg AS (
      SELECT
        FORMAT_DATE('%Y-%m',
          DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING)))
        ) AS year_month,
        NET.REG_DOMAIN(DocumentIdentifier) AS domain,
        V2Themes
      FROM `gdelt-bq.gdeltv2.gkg_partitioned`
      WHERE _PARTITIONTIME BETWEEN TIMESTAMP('{START_DATE}') AND TIMESTAMP('{END_DATE}')
        AND LOWER(DocumentIdentifier) LIKE 'http%'
        AND V2Themes IS NOT NULL
        AND V2Themes != ''
    ),

    -- Attach country via domain lookup. Inner join drops articles from
    -- domains we can't attribute (acceptable for the MVP).
    joined AS (
      SELECT g.year_month, l.source_country AS country, g.V2Themes
      FROM gkg g
      JOIN `{PROJECT_ID}.{DATASET_ID}.{LOOKUP_TABLE}` l USING (domain)
    ),

    -- Each V2Themes value is "THEME_A,offset;THEME_B,offset;...".
    -- Split on ';' then take everything before ',' to get the bare theme.
    exploded AS (
      SELECT
        year_month,
        country,
        SPLIT(theme_with_offset, ',')[OFFSET(0)] AS theme
      FROM joined,
      UNNEST(SPLIT(V2Themes, ';')) AS theme_with_offset
      WHERE theme_with_offset != ''
    ),

    -- Count per (country, year_month, theme), filter noise.
    counted AS (
      SELECT
        year_month,
        country,
        theme,
        COUNT(*) AS theme_count
      FROM exploded
      WHERE theme IS NOT NULL
        AND theme != ''
        AND {noise_clause}
        {exact_clause}
      GROUP BY year_month, country, theme
    )

    -- Keep top N themes per (country, year_month).
    SELECT *
    FROM (
      SELECT
        year_month, country, theme, theme_count,
        ROW_NUMBER() OVER (
          PARTITION BY country, year_month
          ORDER BY theme_count DESC
        ) AS rank
      FROM counted
    )
    WHERE rank <= {TOP_N}
    """

    # Dry run for cost estimate
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = dry.total_bytes_processed / 1e9
    print(f"Will scan ~{gb:.1f} GB (≈ ${gb * 6.25 / 1000:.2f} on-demand)")
    print(f"Date range: {START_DATE} -> {END_DATE}")
    print(f"Top N themes per (country, year_month): {TOP_N}")
    print(f"Noise prefixes blocked: {len(NOISE_PREFIXES)}")

    if input("Proceed? [y/N]: ").strip().lower() != "y":
        print("Aborted.")
        return None

    print("Running query...")
    client.query(sql).result()
    n = client.get_table(table_id).num_rows
    print(f"Materialized {n:,} (country, year_month, theme) rows")
    return table_id


def export_csvs():
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{THEMES_TABLE}"

    # Per-country, per-month, top 20
    per_country_sql = f"""
        SELECT year_month, country, theme, theme_count, rank
        FROM `{table_id}`
        ORDER BY year_month, country, rank
    """
    df = client.query(per_country_sql).to_dataframe()
    df.to_csv(OUT_PER_COUNTRY, index=False)
    print(f"\nSaved {len(df):,} rows to {OUT_PER_COUNTRY}")

    # Global rollup: sum across countries, take top 20 globally per month
    global_sql = f"""
        WITH global_counts AS (
          SELECT year_month, theme, SUM(theme_count) AS theme_count
          FROM `{table_id}`
          GROUP BY year_month, theme
        )
        SELECT *
        FROM (
          SELECT
            year_month, theme, theme_count,
            ROW_NUMBER() OVER (
              PARTITION BY year_month ORDER BY theme_count DESC
            ) AS rank
          FROM global_counts
        )
        WHERE rank <= 20
        ORDER BY year_month, rank
    """
    df_g = client.query(global_sql).to_dataframe()
    df_g.to_csv(OUT_GLOBAL, index=False)
    print(f"Saved {len(df_g):,} rows to {OUT_GLOBAL}")

    # Quick sanity print
    print(f"\n  Date range:           {df['year_month'].min()} -> {df['year_month'].max()}")
    print(f"  Countries:            {df['country'].nunique()}")
    print(f"  Distinct themes:      {df['theme'].nunique()}")
    print("\n  Top 10 global themes for first month:")
    first_month = df_g['year_month'].min()
    print(df_g[df_g['year_month'] == first_month].head(10).to_string(index=False))


if __name__ == "__main__":
    if build_themes_table() is not None:
        export_csvs()