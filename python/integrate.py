"""Cleaning, cross-validation and integration.

Every step logs row counts so the quality record in results/ can be re-created
by re-running the script (raw files stay read-only).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class DataQualityError(RuntimeError):
    """Raised when a check fails hard enough that analysis must stop."""


def clean_prices(df: pd.DataFrame, col: str = "close") -> tuple[pd.DataFrame, dict]:
    q = {"rows_raw": int(len(df))}
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out[col] = pd.to_numeric(out[col], errors="coerce")
    q["missing_close"] = int(out[col].isna().sum())
    out = out.dropna(subset=[col])
    q["nonpositive_close"] = int((out[col] <= 0).sum())
    out = out[out[col] > 0]
    dup = out["date"].duplicated(keep="last")
    q["duplicate_dates"] = int(dup.sum())
    # Yahoo sometimes appends today's live bar with the same date as the last
    # daily bar; the later row is the more recent quote, so keep last.
    out = out[~dup].sort_values("date").reset_index(drop=True)
    q["rows_clean"] = int(len(out))
    if len(out) < 60:
        raise DataQualityError(f"only {len(out)} usable prices (<60); stop")
    return out, q


def simple_returns(prices: pd.DataFrame, col: str = "close") -> pd.DataFrame:
    """Same definition as the workbook's DailyRets: p_t / p_{t-1} - 1."""
    r = prices[col].to_numpy()
    out = pd.DataFrame({"date": prices["date"].iloc[1:].to_numpy(),
                        "ret": r[1:] / r[:-1] - 1.0})
    return out


def crosscheck_twse(yahoo: pd.DataFrame, twse: pd.DataFrame, tol: float) -> tuple[pd.DataFrame, dict]:
    """Compare Yahoo close with official TWSE close on overlapping dates.

    Join key: trading date (both are Asia/Taipei dates). One-to-one expected;
    duplicates on either side are an error, not something to silently average.
    """
    t = twse.dropna(subset=["close_twse"]).copy()
    t["date"] = pd.to_datetime(t["date"])
    if t["date"].duplicated().any():
        raise DataQualityError("duplicate dates in TWSE data -> join would inflate rows")
    lo, hi = t["date"].min(), t["date"].max()
    y = yahoo[(yahoo["date"] >= lo) & (yahoo["date"] <= hi)]
    m = y.merge(t, on="date", how="outer", indicator=True)
    both = m[m["_merge"] == "both"].copy()
    if len(both) > len(y) or len(both) > len(t):
        raise DataQualityError("join produced more rows than either input")
    both["rel_diff"] = both["close"] / both["close_twse"] - 1.0
    both["match"] = both["rel_diff"].abs() <= tol
    q = {
        "window": f"{lo.date()}..{hi.date()}",
        "yahoo_rows_in_window": int(len(y)),
        "twse_rows": int(len(t)),
        "matched_dates": int(len(both)),
        "only_yahoo": int((m["_merge"] == "left_only").sum()),
        "only_twse": int((m["_merge"] == "right_only").sum()),
        "price_match_rate": float(both["match"].mean()) if len(both) else float("nan"),
        "max_abs_rel_diff": float(both["rel_diff"].abs().max()) if len(both) else float("nan"),
        "tolerance": tol,
        "only_yahoo_dates": [str(d.date()) for d in m.loc[m["_merge"] == "left_only", "date"]],
        "only_twse_dates": [str(d.date()) for d in m.loc[m["_merge"] == "right_only", "date"]],
    }
    return both, q


def drop_non_trading(prices: pd.DataFrame, dates: list[str]) -> tuple[pd.DataFrame, int]:
    """Remove Yahoo bars on dates the official exchange did not trade.

    Found during the 2330.TW cross-check: Yahoo carried a bar on 2026-10-23
    whose close equals the previous TWSE close, i.e. a stale non-trading day
    that would add a fake 0% return (docs/debug_log.md D-04).
    """
    bad = pd.to_datetime(pd.Series(dates, dtype="object"))
    keep = ~prices["date"].isin(bad)
    return prices[keep].reset_index(drop=True), int((~keep).sum())


def attach_vix(rets: pd.DataFrame, vix: pd.DataFrame, col: str = "vixcls") -> tuple[pd.DataFrame, dict]:
    """Label each return day with the most recent VIX close STRICTLY BEFORE it.

    Strictly-before avoids look-ahead for Taiwan dates (TW closes before the US
    session of the same calendar day) and is applied uniformly to all tickers.
    """
    v = vix.dropna(subset=[col]).copy()
    v["date"] = pd.to_datetime(v["date"])
    v = v.sort_values("date")
    r = rets.sort_values("date").copy()
    out = pd.merge_asof(r, v.rename(columns={"date": "vix_date"}), left_on="date",
                        right_on="vix_date", direction="backward", allow_exact_matches=False)
    q = {
        "rows_in": int(len(r)),
        "rows_out": int(len(out)),
        "unlabelled": int(out[col].isna().sum()),
        "max_gap_days": int((out["date"] - out["vix_date"]).dt.days.max()),
    }
    if q["rows_out"] != q["rows_in"]:
        raise DataQualityError("VIX attach changed row count")
    return out, q


def time_split(rets: pd.DataFrame, frac: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0.1 <= frac <= 0.9:
        raise ValueError("train_fraction must be in [0.1, 0.9]")
    n = len(rets)
    cut = int(np.floor(n * frac))
    return rets.iloc[:cut].reset_index(drop=True), rets.iloc[cut:].reset_index(drop=True)
