import * as d3 from 'd3';

// ISO 3166-1 alpha-2 → numeric. Used to join GDELT FIPS (→ alpha-2 via crosswalk) to
// world-atlas TopoJSON feature IDs (numeric ISO).
const ALPHA2_TO_NUMERIC = {
  AF: 4,   AX: 248, AL: 8,   DZ: 12,  AS: 16,  AD: 20,  AO: 24,  AI: 660,
  AQ: 10,  AG: 28,  AR: 32,  AM: 51,  AW: 533, AU: 36,  AT: 40,  AZ: 31,
  BS: 44,  BH: 48,  BD: 50,  BB: 52,  BY: 112, BE: 56,  BZ: 84,  BJ: 204,
  BM: 60,  BT: 64,  BO: 68,  BQ: 535, BA: 70,  BW: 72,  BV: 74,  BR: 76,
  IO: 86,  BN: 96,  BG: 100, BF: 854, BI: 108, CV: 132, KH: 116, CM: 120,
  CA: 124, KY: 136, CF: 140, TD: 148, CL: 152, CN: 156, CX: 162, CC: 166,
  CO: 170, KM: 174, CG: 178, CD: 180, CK: 184, CR: 188, CI: 384, HR: 191,
  CU: 192, CW: 531, CY: 196, CZ: 203, DK: 208, DJ: 262, DM: 212, DO: 214,
  EC: 218, EG: 818, SV: 222, GQ: 226, ER: 232, EE: 233, SZ: 748, ET: 231,
  FK: 238, FO: 234, FJ: 242, FI: 246, FR: 250, GF: 254, PF: 258, TF: 260,
  GA: 266, GM: 270, GE: 268, DE: 276, GH: 288, GI: 292, GR: 300, GL: 304,
  GD: 308, GP: 312, GU: 316, GT: 320, GG: 831, GN: 324, GW: 624, GY: 328,
  HT: 332, HM: 334, VA: 336, HN: 340, HK: 344, HU: 348, IS: 352, IN: 356,
  ID: 360, IR: 364, IQ: 368, IE: 372, IM: 833, IL: 376, IT: 380, JM: 388,
  JP: 392, JE: 832, JO: 400, KZ: 398, KE: 404, KI: 296, KP: 408, KR: 410,
  KW: 414, KG: 417, LA: 418, LV: 428, LB: 422, LS: 426, LR: 430, LY: 434,
  LI: 438, LT: 440, LU: 442, MO: 446, MG: 450, MW: 454, MY: 458, MV: 462,
  ML: 466, MT: 470, MH: 584, MQ: 474, MR: 478, MU: 480, YT: 175, MX: 484,
  FM: 583, MD: 498, MC: 492, MN: 496, ME: 499, MS: 500, MA: 504, MZ: 508,
  MM: 104, NA: 516, NR: 520, NP: 524, NL: 528, NC: 540, NZ: 554, NI: 558,
  NE: 562, NG: 566, NU: 570, NF: 574, MK: 807, MP: 580, NO: 578, OM: 512,
  PK: 586, PW: 585, PS: 275, PA: 591, PG: 598, PY: 600, PE: 604, PH: 608,
  PN: 612, PL: 616, PT: 620, PR: 630, QA: 634, RE: 638, RO: 642, RU: 643,
  RW: 646, BL: 652, SH: 654, KN: 659, LC: 662, MF: 663, PM: 666, VC: 670,
  WS: 882, SM: 674, ST: 678, SA: 682, SN: 686, RS: 688, SC: 690, SL: 694,
  SG: 702, SX: 534, SK: 703, SI: 705, SB: 90,  SO: 706, ZA: 710, GS: 239,
  SS: 728, ES: 724, LK: 144, SD: 729, SR: 740, SJ: 744, SE: 752, CH: 756,
  SY: 760, TW: 158, TJ: 762, TZ: 834, TH: 764, TL: 626, TG: 768, TK: 772,
  TO: 776, TT: 780, TN: 788, TR: 792, TM: 795, TC: 796, TV: 798, UG: 800,
  UA: 804, AE: 784, GB: 826, US: 840, UM: 581, UY: 858, UZ: 860, VU: 548,
  VE: 862, VN: 704, VG: 92,  VI: 850, WF: 876, EH: 732, YE: 887, ZM: 894,
  ZW: 716, XK: 383,
};

const parseDate = d3.timeParse('%Y-%m-%d');

export async function loadData() {
  const [mainData, crosswalk] = await Promise.all([
    d3.csv('/data/country_daily_merged.csv'),
    d3.csv('/data/fips-10-4-to-iso-country-codes.csv'),
  ]);

  // Build crosswalk lookups: FIPS ↔ ISO alpha-2, name
  const fipsToAlpha2 = new Map();
  const fipsToName = new Map();
  const alpha2ToFips = new Map();

  for (const row of crosswalk) {
    const fips = row['FIPS 10-4'];
    const alpha2 = row['ISO 3166'];
    const name = row['Name'];
    fipsToAlpha2.set(fips, alpha2);
    fipsToName.set(fips, name);
    if (alpha2 && alpha2 !== '-') alpha2ToFips.set(alpha2, fips);
  }

  // Build numeric ↔ FIPS lookups via ALPHA2_TO_NUMERIC
  const numericToFips = new Map();
  const numericToName = new Map();
  const fipsToNumeric = new Map();

  for (const [alpha2, numeric] of Object.entries(ALPHA2_TO_NUMERIC)) {
    const fips = alpha2ToFips.get(alpha2);
    if (fips) {
      numericToFips.set(numeric, fips);
      numericToName.set(numeric, fipsToName.get(fips) || alpha2);
      fipsToNumeric.set(fips, numeric);
    }
  }

  // Pre-group data by date into a Map for fast slicing.
  // dateMap: Map<'YYYY-MM-DD', { ruUaTotal, allTotal, byCountry: Map<fips, {ruUa, all, ratio, lowVolume}> }>
  const dateMap = new Map();
  let minDate = null;
  let maxDate = null;

  for (const row of mainData) {
    const dateStr = row.date;
    const fips = row.country;
    const allCount = +row.all_count;
    const ruUaCount = +row.ru_ua_count;
    const ratio = +row.ratio;
    const lowVolume = row.low_volume === 'True';

    if (!dateMap.has(dateStr)) {
      dateMap.set(dateStr, { ruUaTotal: 0, allTotal: 0, byCountry: new Map() });
    }
    const day = dateMap.get(dateStr);
    day.ruUaTotal += ruUaCount;
    day.allTotal += allCount;
    day.byCountry.set(fips, { ruUa: ruUaCount, all: allCount, ratio, lowVolume });

    const d = parseDate(dateStr);
    if (!minDate || d < minDate) minDate = d;
    if (!maxDate || d > maxDate) maxDate = d;
  }

  return {
    dateMap,
    fipsToName,
    fipsToNumeric,
    numericToFips,
    numericToName,
    minDate,
    maxDate,
  };
}

// Compute per-country averages within the selected date range.
// Returns Map<numericId, { fips, name, avgRatio, totalWar, totalAll }>
export function computeCountryAverages(dateMap, dateRange, fipsToNumeric, numericToName) {
  const [start, end] = dateRange;
  const fipsStats = new Map();

  for (const [dateStr, dayData] of dateMap) {
    const d = parseDate(dateStr);
    if (d < start || d > end) continue;

    for (const [fips, { ruUa, all, ratio, lowVolume }] of dayData.byCountry) {
      if (!fipsStats.has(fips)) {
        fipsStats.set(fips, {
          ratioSum: 0, count: 0,
          ratioSumAll: 0, countAll: 0,
          totalWar: 0, totalAll: 0,
        });
      }
      const s = fipsStats.get(fips);
      s.totalWar += ruUa;
      s.totalAll += all;
      s.ratioSumAll += ratio;
      s.countAll++;
      if (!lowVolume) {
        s.ratioSum += ratio;
        s.count++;
      }
    }
  }

  const result = new Map();
  for (const [fips, s] of fipsStats) {
    const numeric = fipsToNumeric.get(fips);
    if (!numeric) continue;
    // Mean of daily ratios on non-low-volume days; fall back to all days if all are low-volume.
    const avgRatio =
      s.count > 0
        ? s.ratioSum / s.count
        : s.countAll > 0
          ? s.ratioSumAll / s.countAll
          : 0;
    result.set(numeric, {
      fips,
      avgRatio,
      totalWar: s.totalWar,
      totalAll: s.totalAll,
      name: numericToName.get(numeric) || fips,
    });
  }
  return result;
}

// Compute time series aggregated line for selected countries (or global if none).
// Returns [{date, value}] with 7-day rolling mean applied.
export function computeTimeSeries(dateMap, selectedFips, dateRange) {
  const [start, end] = dateRange;
  const points = [];

  const sortedDates = [...dateMap.keys()].sort();

  for (const dateStr of sortedDates) {
    const d = parseDate(dateStr);
    if (d < start || d > end) continue;

    const dayData = dateMap.get(dateStr);
    let ruUaSum = 0;
    let allSum = 0;

    if (!selectedFips || selectedFips.size === 0) {
      ruUaSum = dayData.ruUaTotal;
      allSum = dayData.allTotal;
    } else {
      for (const fips of selectedFips) {
        const c = dayData.byCountry.get(fips);
        if (c) {
          ruUaSum += c.ruUa;
          allSum += c.all;
        }
      }
    }

    if (allSum > 0) {
      points.push({ date: d, value: (ruUaSum / allSum) * 100 });
    }
  }

  return rollingMean(points, 7);
}

// Calendar-based 7-day rolling mean. Gaps in data don't break the window —
// missing dates simply contribute nothing to the average.
function rollingMean(series, windowDays = 7) {
  const byTime = new Map(series.map(p => [p.date.getTime(), p.value]));
  return series.map(point => {
    let sum = 0;
    let count = 0;
    for (let i = 0; i < windowDays; i++) {
      const t = point.date.getTime() - i * 86400000;
      const v = byTime.get(t);
      if (v != null) { sum += v; count++; }
    }
    return { date: point.date, value: count > 0 ? sum / count : null };
  });
}

// 95th-percentile of non-zero country average ratios; used to clamp color scale domain.
export function computeP95(countryAverages) {
  const values = [...countryAverages.values()]
    .map(d => d.avgRatio)
    .filter(v => v > 0)
    .sort((a, b) => a - b);
  if (values.length === 0) return 0.05;
  const idx = Math.min(Math.floor(values.length * 0.95), values.length - 1);
  return values[idx];
}
