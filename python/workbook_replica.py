"""Re-implement the Ticker Volatility workbook's daily SD block in Python.

Source of truth: VT/modVT.bas (DrawPage), daily frequency. Input prices must be
Yahoo "adjclose" - FetchYahooSeries prefers it over "close" (found 2026-11-24,
docs/debug_log.md D-07):
  sample   = last max(520, PERIOD) simple returns          (m)
  window   = last PERIOD returns                            (w)
  sdW      = sample SD (n-1) of the window, muW = window mean
  nBeyond  = # window returns with |r - muW| > 2*sdW         (cell C8 text)
  inside_k = share of ALL m returns with |r| <= k*sdW        (cells P10:P12)
             (note: not demeaned - the workbook compares raw |r|)

Used by tests/test_workbook_replica.py to check that this project's numbers
are the same numbers a user sees in the workbook (see docs/workbook_check.md).
"""
from __future__ import annotations

import numpy as np


def vt_daily_block(close: np.ndarray, period: int) -> dict:
    close = np.asarray(close, float)
    smp = max(520, period)
    rn = close.size
    st = rn - smp - 1 if rn > smp + 1 else 0
    px = close[st:]
    rr = px[1:] / px[:-1] - 1.0
    m = rr.size
    w = min(period, m)
    win = rr[m - w:]
    sd_w = float(win.std(ddof=1))
    mu_w = float(win.mean())
    return {
        "m": int(m),
        "w": int(w),
        "sd_window": sd_w,
        "n_beyond_2sd": int(np.sum(np.abs(win - mu_w) > 2 * sd_w)),
        "inside": {k: float(np.mean(np.abs(rr) <= k * sd_w)) for k in (1, 2, 3)},
        "normal_inside": {1: 0.6827, 2: 0.9545, 3: 0.9973},
    }
