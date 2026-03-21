"""
Trophic State Index calculations.
Implements both the adapted Carlson TSI and the TRIX index used in Black Sea research.
"""

import math
import numpy as np
import pandas as pd


def carlson_tsi(chl_mg_m3: float) -> dict:
    """
    Carlson TSI adapted for marine/coastal environments.
    Input: surface chlorophyll-a in mg/m³ (= µg/L)
    """
    chl = max(chl_mg_m3, 0.001)
    tsi = 9.81 * math.log(chl) + 30.6

    if chl < 1.5:
        status = "Oligotrophic"
        color  = "#2166ac"
    elif chl < 3.0:
        status = "Mesotrophic"
        color  = "#4dac26"
    elif chl < 6.0:
        status = "Eutrophic"
        color  = "#f1a340"
    else:
        status = "Hypereutrophic"
        color  = "#d73027"

    return {"tsi": round(tsi, 2), "status": status, "color": color, "chl": chl}


def trix_index(
    chl_mg_m3: float,
    do_pct_saturation: float,
    din_umol_l: float,
    drp_umol_l: float,
) -> dict:
    """
    TRIX (Trophic Index) — widely used in Black Sea eutrophication studies.
    Reference: Vollenweider et al. (1998)

    Args:
        chl_mg_m3:         Chlorophyll-a (mg/m³)
        do_pct_saturation: Dissolved oxygen saturation (%)
        din_umol_l:        Dissolved Inorganic Nitrogen (µmol/L)
        drp_umol_l:        Dissolved Reactive Phosphorus (µmol/L)

    Returns dict with trix value and trophic class.
    """
    # Absolute deviation of DO from 100% saturation
    ado = abs(do_pct_saturation - 100.0)

    chl = max(chl_mg_m3, 0.001)
    ado = max(ado, 0.001)
    din = max(din_umol_l * 0.014,  0.001)  # convert µmol/L N to mg/L
    drp = max(drp_umol_l * 0.031,  0.001)  # convert µmol/L P to mg/L

    trix = (math.log10(chl * ado * din * drp) + 1.5) / 1.2

    if trix < 2:
        tclass, color = "High quality",   "#2166ac"
    elif trix < 4:
        tclass, color = "Good quality",   "#4dac26"
    elif trix < 5:
        tclass, color = "Mediocre",       "#f1a340"
    elif trix < 6:
        tclass, color = "Eutrophic",      "#d7191c"
    else:
        tclass, color = "Hypereutrophic", "#7f0000"

    return {"trix": round(trix, 3), "class": tclass, "color": color}


def compute_tsi_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply Carlson TSI to a time series DataFrame.
    Expects column 'y' (mean chlorophyll in mg/m³).
    Returns original DataFrame with added columns: tsi, trophic_status.
    """
    results = df["y"].apply(lambda c: carlson_tsi(c))
    df = df.copy()
    df["tsi"]            = results.apply(lambda r: r["tsi"])
    df["trophic_status"] = results.apply(lambda r: r["status"])
    df["status_color"]   = results.apply(lambda r: r["color"])
    return df
