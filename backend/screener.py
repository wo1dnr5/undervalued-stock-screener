import pandas as pd
import numpy as np


def apply_filters(df, per_max=15.0, pbr_max=1.5, roe_min=10.0, rsi_max=40.0, w52_min=-20.0):
    if df is None or df.empty:
        return pd.DataFrame()

    mask = pd.Series(True, index=df.index)

    if "PER" in df.columns:
        mask &= df["PER"].notna() & (df["PER"] > 0) & (df["PER"] <= per_max)
    if "PBR" in df.columns:
        mask &= df["PBR"].notna() & (df["PBR"] > 0) & (df["PBR"] <= pbr_max)
    if "ROE" in df.columns:
        mask &= df["ROE"].notna() & (df["ROE"] >= roe_min)
    if "RSI" in df.columns:
        mask &= df["RSI"].notna() & (df["RSI"] <= rsi_max)
    if "52W_change" in df.columns:
        mask &= df["52W_change"].notna() & (df["52W_change"] <= w52_min)

    return df[mask].copy()


def _normalize(series, higher_is_better=False):
    s_min, s_max = series.min(), series.max()
    if s_max == s_min:
        return pd.Series(50.0, index=series.index)
    norm = (series - s_min) / (s_max - s_min) * 100
    return norm if higher_is_better else (100 - norm)


def calculate_score(df):
    if df is None or df.empty:
        return df
    df = df.copy()

    weights = {
        "PER":        (0.25, False),
        "PBR":        (0.20, False),
        "ROE":        (0.20, True),
        "RSI":        (0.20, False),
        "52W_change": (0.15, False),
    }

    score = pd.Series(0.0, index=df.index)
    for col, (w, higher) in weights.items():
        if col in df.columns and df[col].notna().sum() > 1:
            score += _normalize(df[col], higher_is_better=higher) * w

    df["score"] = score.round(1)
    return df
