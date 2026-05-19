"""
Cross-country snapshot: Google Trends vs GDELT coverage
=======================================================

Builds trends_vs_coverage.csv comparing each country's news coverage of
the Russia-Ukraine war against its audience's search interest.

X axis (coverage_share): WITHIN-COUNTRY share — country's war reports as a
  fraction of its own total news output (sum(ru_ua_count) / sum(all_count)
  from country_daily_merged.csv). This matches what the choropleth uses, so
  the two visualisations now measure compatible things.

Y axis (trends_score): per-country interest in the Russia-Ukraine war,
  measured via war-specific OR-query groups in each of five languages
  (English, Russian, Chinese, Arabic, Japanese). One separate
  interest_by_region call per language; per-country MAX across the five
  normalised scores. Querying all five groups in a single call would
  return within-country share-of-bundle instead of spatial intensity —
  the same bug that flattened the previous version of this script.

  Switched away from the bare keyword "Ukraine" because that picked up
  tourism, football, Eurovision, etc. War-specific phrasings ("Ukraine
  war", "Russian invasion", "война на Украине", …) isolate the conflict
  signal at the cost of dropping low-volume markets where war-specific
  searches don't clear Trends' volume floor — which we treat as a true
  negative, not a measurement gap.

Setup:
    pip install pytrends pandas country_converter

Limitations to declare in any narrative built on this:
  - Google Trends only; Yandex (RU) / Baidu (CN) / Naver (KR) markets are
    structurally undermeasured.
  - The max-across-languages aggregator is a heuristic; per-language scales
    are independently normalised so the absolute values aren't directly
    comparable across countries that "win" in different languages.
  - The >3-year window is collapsed to a single aggregate — no temporal view.
"""

import time
import pandas as pd
import country_converter as coco
from pytrends.request import TrendReq

# ---- CONFIG --------------------------------------------------------------
GDELT_DAILY_CSV = "../app/public/data/country_daily_merged.csv"
OUTPUT_CSV      = "trends_vs_coverage.csv"
TIMEFRAME       = "2022-02-01 2026-05-08"
HL              = "en-US"
SLEEP_SECONDS   = 5      # between successive pytrends calls
MIN_TOTAL_ALL   = 100    # exclude countries with effectively no GDELT presence

# War-specific OR-groups in five languages so non-English markets aren't
# undercounted. Each value is a pytrends "a + b + c" OR-group — Trends
# returns spatial intensity for the union of those phrasings. Run as
# separate single-payload interest_by_region calls (multi-payload in one
# call returns share-of-bundle, not intensity), then max-merged per country.
KEYWORDS = {
    "en": "Ukraine war + Russia Ukraine war + war in Ukraine + Ukraine invasion",
    "ru": "война на Украине + Украина война + вторжение в Украину",
    "zh": "乌克兰战争 + 俄乌战争 + 俄乌冲突",
    "ar": "حرب أوكرانيا + الحرب في أوكرانيا + الغزو الروسي لأوكرانيا",
    "ja": "ウクライナ戦争 + ウクライナ侵攻 + ロシア ウクライナ",
}

# FIPS 10-4 -> ISO 3166-1 alpha-2. Covers the countries that actually appear
# in GDELT GKG. A handful of FIPS codes have no ISO equivalent (e.g. obsolete
# territories) and are intentionally omitted; those rows fall out of the join.
FIPS_TO_ISO2 = {
    "AC": "AG", "AE": "AE", "AF": "AF", "AG": "DZ", "AJ": "AZ", "AL": "AL",
    "AM": "AM", "AN": "AD", "AO": "AO", "AR": "AR", "AS": "AU", "AU": "AT",
    "BA": "BH", "BB": "BB", "BC": "BW", "BE": "BE", "BF": "BS", "BG": "BD",
    "BH": "BZ", "BK": "BA", "BL": "BO", "BM": "MM", "BN": "BJ", "BO": "BY",
    "BP": "SB", "BR": "BR", "BT": "BT", "BU": "BG", "BX": "BN", "BY": "BI",
    "CA": "CA", "CB": "KH", "CD": "TD", "CE": "LK", "CF": "CG", "CG": "CD",
    "CH": "CN", "CI": "CL", "CM": "CM", "CN": "KM", "CO": "CO", "CS": "CR",
    "CT": "CF", "CU": "CU", "CV": "CV", "CY": "CY", "DA": "DK", "DJ": "DJ",
    "DO": "DM", "DR": "DO", "EC": "EC", "EG": "EG", "EI": "IE", "EK": "GQ",
    "EN": "EE", "ER": "ER", "ES": "SV", "ET": "ET", "EZ": "CZ", "FI": "FI",
    "FJ": "FJ", "FM": "FM", "FR": "FR", "GA": "GM", "GB": "GA", "GG": "GE",
    "GH": "GH", "GJ": "GD", "GM": "DE", "GR": "GR", "GT": "GT", "GV": "GN",
    "GY": "GY", "HA": "HT", "HO": "HN", "HR": "HR", "HU": "HU", "IC": "IS",
    "ID": "ID", "IN": "IN", "IR": "IR", "IS": "IL", "IT": "IT", "IV": "CI",
    "IZ": "IQ", "JA": "JP", "JM": "JM", "JO": "JO", "KE": "KE", "KG": "KG",
    "KN": "KP", "KS": "KR", "KU": "KW", "KZ": "KZ", "LA": "LA", "LE": "LB",
    "LG": "LV", "LH": "LT", "LI": "LR", "LO": "SK", "LS": "LI", "LT": "LS",
    "LU": "LU", "LY": "LY", "MA": "MG", "MD": "MD", "MG": "MN", "MI": "MW",
    "MJ": "ME", "MK": "MK", "ML": "ML", "MN": "MC", "MO": "MA", "MP": "MU",
    "MR": "MR", "MT": "MT", "MU": "OM", "MV": "MV", "MX": "MX", "MY": "MY",
    "MZ": "MZ", "NG": "NE", "NH": "VU", "NI": "NG", "NL": "NL", "NO": "NO",
    "NP": "NP", "NR": "NR", "NS": "SR", "NU": "NI", "NZ": "NZ", "PA": "PY",
    "PE": "PE", "PK": "PK", "PL": "PL", "PM": "PA", "PO": "PT", "PP": "PG",
    "PS": "PW", "PU": "GW", "QA": "QA", "RM": "MH", "RO": "RO", "RP": "PH",
    "RS": "RU", "RW": "RW", "SA": "SA", "SE": "SC", "SF": "ZA", "SG": "SN",
    "SI": "SI", "SL": "SL", "SM": "SM", "SN": "SG", "SO": "SO", "SP": "ES",
    "ST": "LC", "SU": "SD", "SW": "SE", "SY": "SY", "SZ": "CH", "TD": "TT",
    "TH": "TH", "TI": "TJ", "TN": "TO", "TO": "TG", "TP": "ST", "TS": "TN",
    "TU": "TR", "TV": "TV", "TW": "TW", "TX": "TM", "TZ": "TZ", "UG": "UG",
    "UK": "GB", "UP": "UA", "US": "US", "UV": "BF", "UY": "UY", "UZ": "UZ",
    "VE": "VE", "VM": "VN", "WA": "NA", "WZ": "SZ", "YM": "YE", "ZA": "ZM",
    "ZI": "ZW",
}


def load_gdelt_within_country_share():
    """Per-country within-country share of war coverage.

    Sums ru_ua_count and all_count over the full period and computes
    sum(ru_ua) / sum(all). Dropping countries below MIN_TOTAL_ALL guards
    against tiny denominators producing meaningless ratios."""
    df = pd.read_csv(GDELT_DAILY_CSV)
    g = df.groupby("country", as_index=False).agg(
        total_reports=("ru_ua_count", "sum"),
        total_all    =("all_count",   "sum"),
    )
    n_before = len(g)
    g = g[g["total_all"] >= MIN_TOTAL_ALL]
    print(f"      filtered {n_before - len(g)} countries below "
          f"{MIN_TOTAL_ALL} total all_count")
    g["coverage_share"] = g["total_reports"] / g["total_all"]
    g["iso2"] = g["country"].map(FIPS_TO_ISO2)
    unmapped = g[g["iso2"].isna()]["country"].tolist()
    if unmapped:
        print(f"      warning: {len(unmapped)} FIPS without ISO2 "
              f"(dropped): {unmapped}")
    g = g.dropna(subset=["iso2"])
    g = g.rename(columns={"country": "fips"})
    return g[["fips", "iso2", "total_reports", "total_all", "coverage_share"]]


def fetch_trends_multilingual():
    """One interest_by_region call per language OR-group. Each returns
    per-country spatial intensity (0-100) for the union of war-specific
    phrasings in that language. Merged by country name; final
    trends_score = max across languages, so a country's score reflects
    the language it searched war-related terms in most strongly."""
    pytrends = TrendReq(hl=HL, tz=0, retries=3, backoff_factor=1)
    frames = []
    for lang, kw in KEYWORDS.items():
        print(f"      fetching {lang}: {kw!r}")
        pytrends.build_payload([kw], timeframe=TIMEFRAME, geo="")
        df = pytrends.interest_by_region(resolution="COUNTRY", inc_low_vol=True)
        df = (df.reset_index()
                .rename(columns={"geoName": "country_name",
                                 kw: f"score_{lang}"}))
        frames.append(df)
        time.sleep(SLEEP_SECONDS)

    out = frames[0]
    for df in frames[1:]:
        out = out.merge(df, on="country_name", how="outer")
    score_cols = [f"score_{lang}" for lang in KEYWORDS]
    out[score_cols] = out[score_cols].fillna(0)
    out["trends_score"] = out[score_cols].max(axis=1)
    return out


def attach_iso2_to_trends(trends_df):
    """pytrends country name -> ISO2 via country_converter."""
    cc = coco.CountryConverter()
    out = trends_df.copy()
    out["iso2"] = cc.convert(
        names=out["country_name"].tolist(),
        src="regex",
        to="ISO2",
        not_found=None,
    )
    return out[out["iso2"].notna()]


def build_snapshot():
    print("[1/3] Loading GDELT within-country shares...")
    gdelt = load_gdelt_within_country_share()
    print(f"      {len(gdelt)} countries kept after volume + ISO2 filters")

    print(f"[2/3] Fetching Google Trends interest_by_region in "
          f"{len(KEYWORDS)} languages over {TIMEFRAME}...")
    trends = fetch_trends_multilingual()
    print(f"      {len(trends)} countries returned by Trends (merged)")

    print("[3/3] Mapping country names -> ISO2 and joining...")
    trends = attach_iso2_to_trends(trends)
    merged = gdelt.merge(trends, on="iso2", how="inner")
    print(f"      {len(merged)} countries successfully joined")

    # Percentile ranks on each axis, then gap. Both axes now measure
    # "this country's share of itself" (within-country), so they're on
    # compatible conceptual ground.
    merged["coverage_pct_rank"] = merged["coverage_share"].rank(pct=True)
    merged["trends_pct_rank"]   = merged["trends_score"].rank(pct=True)
    merged["gap"] = merged["coverage_pct_rank"] - merged["trends_pct_rank"]

    score_cols = [f"score_{lang}" for lang in KEYWORDS]
    out = merged[[
        "fips", "iso2", "country_name",
        "total_reports", "total_all",
        "coverage_share", "coverage_pct_rank",
        *score_cols, "trends_score", "trends_pct_rank",
        "gap",
    ]].sort_values("gap")

    out.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(out)} rows to {OUTPUT_CSV}")

    print("\nTop 10 'audience searches more than press covers' (gap < 0):")
    print(out.head(10)[["fips", "country_name", "coverage_share",
                        "trends_score", "gap"]].to_string(index=False))

    print("\nTop 10 'press covers more than audience searches' (gap > 0):")
    print(out.tail(10)[["fips", "country_name", "coverage_share",
                        "trends_score", "gap"]].to_string(index=False))

    return out


if __name__ == "__main__":
    build_snapshot()
