"""
Russia-Ukraine Coverage Dataset Builder
========================================

One script. Uploads your domain-country lookup to BigQuery (once),
then runs an aggregated query that returns:

    date | country | report_count | total_report_count

Total runtime: ~1-2 minutes. Total cost: a few dollars (scans GKG once).

Setup:
    pip install google-cloud-bigquery pandas db-dtypes
    gcloud auth application-default login
"""

import os
from google.cloud import bigquery

# ---- CONFIG --------------------------------------------------------------
PROJECT_ID    = "--insert-project-id--"     # <-- your project
DATASET_ID    = "gdelt_ru_ua"
LOOKUP_TABLE  = "domain_country_lookup"
LOOKUP_CSV    = "domain_country_lookup.csv"           # path to your local CSV
START_DATE    = "2022-02-01"
END_DATE      = "2026-05-08"

# ---- FILTER MODE ---------------------------------------------------------
# "legacy"   : original filter — V2Themes ~ /RUSSIA|UKRAINE/ OR V2Locations ~ /#(UP|RS)#/
# "anchored" : require V2Locations ~ /#(UP|RS)#/ AND one war-keyword hit
#              (see WAR_PERSONS / WAR_PLACES / WAR_THEMES / WAR_ORGS below)
# Output file is auto-suffixed with the mode so the two runs don't overwrite.
MODE          = "anchored"

OUTPUT_CSV    = f"ru_ua_country_daily_{MODE}.csv"

# ---- WAR-KEYWORD LISTS ---------------------------------------------------
# An article is kept iff it is geotagged in Ukraine OR Russia (the anchor)
# AND mentions at least one war indicator from these lists. Edit freely;
# the SQL is built from these constants so adding a name is a one-liner.

# V2Persons format: "Name1,offset;Name2,offset;..."  (case-insensitive match)
WAR_PERSONS = [
    "putin", "zelensky", "zelenskyy", "lavrov", "shoigu", "prigozhin",
    "stoltenberg",
]

# V2Locations.LocationFullName contains city/region names (case-insensitive)
WAR_PLACES = [
    "kyiv", "kharkiv", "mariupol", "bakhmut", "donetsk", "luhansk",
    "kherson", "crimea", "donbas",
]

# V2Themes format: "THEME,offset;THEME,offset;..."  (themes are uppercase)
# Anchored to word boundaries so e.g. KILL doesn't match KILLED_BY_DISEASE.
WAR_THEMES = [
    "ARMEDCONFLICT", "KILL", "WOUND",
    "WB_2433_CONFLICT_AND_FRAGILITY",
]

# V2Organizations free-text (case-insensitive)
WAR_ORGS = ["wagner group", "kremlin"]

client = bigquery.Client(project=PROJECT_ID)


# ---- STEP 1: ENSURE DATASET EXISTS --------------------------------------
def ensure_dataset():
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset_ref.location = "US"   # must match gdelt-bq location
    client.create_dataset(dataset_ref, exists_ok=True)
    print(f"[1/3] Dataset {DATASET_ID} ready")


# ---- STEP 2: UPLOAD LOOKUP CSV (idempotent) -----------------------------
def upload_lookup():
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{LOOKUP_TABLE}"

    # Skip upload if table already exists with rows
    try:
        existing = client.get_table(table_id)
        if existing.num_rows > 0:
            print(f"[2/3] Lookup table already loaded ({existing.num_rows:,} rows) - skipping upload")
            return table_id
    except Exception:
        pass

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition="WRITE_TRUNCATE",
    )

    if not os.path.exists(LOOKUP_CSV):
        raise FileNotFoundError(
            f"Cannot find {LOOKUP_CSV}. Place the CSV next to this script "
            f"or update LOOKUP_CSV to its full path."
        )

    with open(LOOKUP_CSV, "rb") as f:
        client.load_table_from_file(f, table_id, job_config=job_config).result()

    n = client.get_table(table_id).num_rows
    print(f"[2/3] Uploaded {n:,} domain->country mappings")
    return table_id


# ---- STEP 3: BUILD THE DATASET ------------------------------------------
def build_filter_clause():
    """Return the topic-filter SQL for the configured MODE."""
    if MODE == "legacy":
        return """
        AND (
          REGEXP_CONTAINS(V2Themes, r'(?i)RUSSIA|UKRAINE')
          OR REGEXP_CONTAINS(V2Locations, r'#(UP|RS)#')
        )"""

    if MODE == "anchored":
        persons_re = "|".join(WAR_PERSONS)
        places_re  = "|".join(WAR_PLACES)
        themes_re  = "|".join(WAR_THEMES)
        orgs_re    = "|".join(WAR_ORGS)
        return f"""
        -- Anchor: article must be geotagged in Ukraine or Russia (FIPS UP/RS)
        AND REGEXP_CONTAINS(V2Locations, r'#(UP|RS)#')
        -- War indicator: at least one person, place, theme, or organization
        AND (
          REGEXP_CONTAINS(V2Persons,       r'(?i)({persons_re})')
          OR REGEXP_CONTAINS(V2Locations,  r'(?i)({places_re})')
          OR REGEXP_CONTAINS(V2Themes,     r'\\b({themes_re})\\b')
          OR REGEXP_CONTAINS(V2Organizations, r'(?i)({orgs_re})')
        )"""

    raise ValueError(f"Unknown MODE: {MODE!r} (expected 'legacy' or 'anchored')")


def build_dataset():
    filter_clause = build_filter_clause()
    print(f"      Filter mode: {MODE} -> writing to {OUTPUT_CSV}")

    sql = f"""
    WITH coverage AS (
      SELECT
        DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING))) AS date,
        NET.REG_DOMAIN(DocumentIdentifier) AS domain
      FROM `gdelt-bq.gdeltv2.gkg_partitioned`
      WHERE _PARTITIONTIME BETWEEN TIMESTAMP('{START_DATE}') AND TIMESTAMP('{END_DATE}')
        {filter_clause}
        AND LOWER(DocumentIdentifier) LIKE '%http%'
    ),
    joined AS (
      SELECT c.date, l.source_country AS country
      FROM coverage c
      JOIN `{PROJECT_ID}.{DATASET_ID}.{LOOKUP_TABLE}` l USING (domain)
    )
    SELECT
      date,
      country,
      COUNT(*) AS report_count,
      SUM(COUNT(*)) OVER (PARTITION BY date) AS total_report_count
    FROM joined
    GROUP BY date, country
    ORDER BY date, country
    """

    # Dry run first to estimate cost
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = dry.total_bytes_processed / 1e9
    print(f"[3/3] Will scan ~{gb:.1f} GB (≈ ${gb * 6.25 / 1000:.2f} on-demand)")

    print("      Running query...")
    df = client.query(sql).to_dataframe()
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n✓ Saved {len(df):,} rows to {OUTPUT_CSV}")
    print(f"  Date range: {df['date'].min()} → {df['date'].max()}")
    print(f"  Countries:  {df['country'].nunique()}")
    print("\n  Top 10 reporting countries (total volume):")
    print(df.groupby("country")["report_count"].sum()
            .sort_values(ascending=False).head(10).to_string())
    return df


# ---- RUN ----------------------------------------------------------------
if __name__ == "__main__":
    ensure_dataset()
    upload_lookup()
    build_dataset()