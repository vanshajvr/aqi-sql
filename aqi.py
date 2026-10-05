"""
aqi.py

CPCB National Air Quality Index from pollutant concentrations, used to put
OpenAQ data (which has concentrations, not AQI) on the same scale as the
official AQI in the Kaggle data.

Method (CPCB, National AQI, 2014):
  * each pollutant gets a sub-index by linear interpolation inside its
    concentration band:  I = (I_hi - I_lo) / (C_hi - C_lo) * (C - C_lo) + I_lo
  * AQI = the highest sub-index
  * at least 3 pollutants are needed, one of which must be PM2.5 or PM10

Units: PM2.5, PM10, NO2, SO2, O3 in ug/m3; CO in mg/m3.
CPCB uses 24-hour means for PM, NO2 and SO2, and 8-hour maxima for CO and
O3. Callers here pass daily means for all six; that approximation is
measured by Test A in analysis_plans/backfill_preregistration.md.

The top ("Severe", 401-500) bands are open-ended in the CPCB table; the
upper concentrations used here are the ones in common use for this dataset
(e.g. PM2.5 250-380), and anything above them is capped at 500.
"""
import math

AQI_BANDS = [(0, 50), (51, 100), (101, 200), (201, 300), (301, 400), (401, 500)]

# Concentration band edges per pollutant, aligned with AQI_BANDS
CONC_BANDS = {
    "pm25": [(0, 30), (31, 60), (61, 90), (91, 120), (121, 250), (251, 380)],
    "pm10": [(0, 50), (51, 100), (101, 250), (251, 350), (351, 430), (431, 510)],
    "no2": [(0, 40), (41, 80), (81, 180), (181, 280), (281, 400), (401, 520)],
    "so2": [(0, 40), (41, 80), (81, 380), (381, 800), (801, 1600), (1601, 2000)],
    "co": [(0, 1.0), (1.1, 2.0), (2.1, 10), (10.1, 17), (17.1, 34), (34.1, 50)],
    "o3": [(0, 50), (51, 100), (101, 168), (169, 208), (209, 748), (749, 1000)],
}

CATEGORIES = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]


def _is_missing(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def sub_index(pollutant, conc):
    """CPCB sub-index for one pollutant, or None if the value is missing/invalid."""
    if _is_missing(conc) or conc < 0:
        return None
    bands = CONC_BANDS[pollutant]
    for (c_lo, c_hi), (i_lo, i_hi) in zip(bands, AQI_BANDS):
        # Concentrations between published edges (e.g. 30.5 for PM2.5) belong
        # to the upper band; interpolate from the previous band's top.
        if conc <= c_hi:
            lo = c_lo if conc >= c_lo else bands[bands.index((c_lo, c_hi)) - 1][1]
            ilo = i_lo if conc >= c_lo else i_lo - 1
            return (i_hi - ilo) / (c_hi - lo) * (conc - lo) + ilo
    return 500.0


def aqi(concentrations):
    """concentrations: dict pollutant -> value. Returns (aqi, dominant) or (None, None)."""
    subs = {p: sub_index(p, v) for p, v in concentrations.items() if p in CONC_BANDS}
    subs = {p: s for p, s in subs.items() if s is not None}
    if len(subs) < 3 or not ({"pm25", "pm10"} & subs.keys()):
        return None, None
    dominant = max(subs, key=subs.get)
    return subs[dominant], dominant


def category(aqi_value):
    """CPCB category, using the same cut-offs as 05_severity_breakdown.sql."""
    if _is_missing(aqi_value):
        return None
    for cat, upper in zip(CATEGORIES, (50, 100, 200, 300, 400)):
        if aqi_value <= upper:
            return cat
    return "Severe"
