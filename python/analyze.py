"""Statistical core.

Research question: are daily returns normal? If not, how much does the
workbook's +/-k SD rule (normal assumption) underestimate the probability of
an extreme move, and do a Student-t fit or historical quantiles do better?

Design: estimate on the first 70% of days (train), evaluate on the last 30%
(test), never the other way round.

Moment definitions (kept explicit so the R check can match them exactly):
  m_j = mean((r - mean(r))**j)          (1/n, population moments)
  skew g1 = m3 / m2**1.5
  excess kurtosis g2 = m4 / m2**2 - 3
  JB = n/6 * (g1**2 + g2**2/4) ~ chi2(2) under normality (large n)
  SD for the k-sigma bands = sample SD with n-1 (same as workbook SdS)
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats


def moments(r: np.ndarray) -> dict:
    r = np.asarray(r, dtype=float)
    n = r.size
    if n < 8:
        raise ValueError("need at least 8 returns for moment statistics")
    d = r - r.mean()
    m2, m3, m4 = (d**2).mean(), (d**3).mean(), (d**4).mean()
    if m2 == 0:
        raise ValueError("zero variance: all returns identical")
    g1 = m3 / m2**1.5
    g2 = m4 / m2**2 - 3.0
    jb = n / 6.0 * (g1**2 + g2**2 / 4.0)
    return {
        "n": int(n),
        "mean": float(r.mean()),
        "sd": float(r.std(ddof=1)),
        "skew": float(g1),
        "excess_kurtosis": float(g2),
        "jb": float(jb),
        "jb_p": float(stats.chi2.sf(jb, 2)),
        "min": float(r.min()),
        "max": float(r.max()),
    }


def shapiro(r: np.ndarray) -> dict:
    r = np.asarray(r, dtype=float)
    if r.size > 5000:  # same limit as R's shapiro.test
        r = r[-5000:]
    w, p = stats.shapiro(r)
    return {"W": float(w), "p": float(p), "n_used": int(r.size)}


def ljung_box_sq(r: np.ndarray, lags: int = 10) -> dict:
    """Ljung-Box on squared demeaned returns: tests volatility clustering,
    i.e. whether the 'independent days' assumption behind the bands holds."""
    x = (np.asarray(r, float) - np.mean(r)) ** 2
    x = x - x.mean()
    n = x.size
    denom = (x**2).sum()
    q = 0.0
    for k in range(1, lags + 1):
        rho = (x[k:] * x[:-k]).sum() / denom
        q += rho**2 / (n - k)
    q *= n * (n + 2)
    return {"lags": lags, "Q": float(q), "p": float(stats.chi2.sf(q, lags))}


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def fit_t(train: np.ndarray) -> dict:
    df, loc, scale = stats.t.fit(train)
    return {"df": float(df), "loc": float(loc), "scale": float(scale)}


def exceedance_table(train: np.ndarray, test: np.ndarray, ks, tfit: dict) -> list[dict]:
    """For each k: probability that |r - mu_train| > k * sd_train.

    predicted by  - normal (the workbook's assumption): 2*(1 - Phi(k))
                  - Student-t fitted on train
                  - historical frequency in train
    observed      - frequency in test, with Wilson 95% CI and binomial tests.
    """
    mu, sd = float(np.mean(train)), float(np.std(train, ddof=1))
    rows = []
    for k in ks:
        lo, hi = mu - k * sd, mu + k * sd
        p_norm = 2 * stats.norm.sf(k)
        p_t = (stats.t.sf((hi - tfit["loc"]) / tfit["scale"], tfit["df"])
               + stats.t.cdf((lo - tfit["loc"]) / tfit["scale"], tfit["df"]))
        p_hist = float(np.mean((train < lo) | (train > hi)))
        hits = int(np.sum((test < lo) | (test > hi)))
        n = int(test.size)
        obs = hits / n
        ci = wilson(hits, n)
        rows.append({
            "k": k,
            "band_low": lo, "band_high": hi,
            "p_normal": float(p_norm), "p_t": float(p_t), "p_hist_train": p_hist,
            "test_hits": hits, "test_n": n, "p_observed": obs,
            "ci95_low": ci[0], "ci95_high": ci[1],
            "ratio_obs_to_normal": obs / p_norm if p_norm > 0 else float("nan"),
            "binom_p_vs_normal": float(stats.binomtest(hits, n, p_norm).pvalue),
            "binom_p_vs_t": float(stats.binomtest(hits, n, min(max(p_t, 1e-12), 1 - 1e-12)).pvalue),
            "binom_p_vs_hist": float(stats.binomtest(hits, n, min(max(p_hist, 1e-12), 1 - 1e-12)).pvalue),
        })
    return rows


def rolling_exceedance(r_all: np.ndarray, n_train: int, window: int, ks, t_df: float) -> list[dict]:
    """Scale-adaptive version: standardise each TEST day by the mean/SD of the
    `window` days strictly before it (like the workbook's PERIOD lookback).

    This separates the tail SHAPE question (normal vs t) from the volatility
    REGIME question (fixed train SD vs recent SD). The t model uses the df
    fitted on train, rescaled to unit variance: P(|Z|>k) = 2*t.sf(k*sqrt(df/(df-2)), df).
    """
    r_all = np.asarray(r_all, float)
    if n_train < window:
        raise ValueError("train period shorter than rolling window")
    z = []
    for i in range(n_train, r_all.size):
        past = r_all[i - window:i]
        z.append((r_all[i] - past.mean()) / past.std(ddof=1))
    z = np.asarray(z)
    rows = []
    for k in ks:
        p_norm = 2 * stats.norm.sf(k)
        p_t = 2 * stats.t.sf(k * math.sqrt(t_df / (t_df - 2)), t_df) if t_df > 2 else float("nan")
        hits = int(np.sum(np.abs(z) > k)); n = int(z.size)
        ci = wilson(hits, n)
        rows.append({"k": k, "window": window, "p_normal": float(p_norm), "p_t_unitvar": float(p_t),
                     "test_hits": hits, "test_n": n, "p_observed": hits / n,
                     "ci95_low": ci[0], "ci95_high": ci[1],
                     "ratio_obs_to_normal": (hits / n) / p_norm,
                     "binom_p_vs_normal": float(stats.binomtest(hits, n, p_norm).pvalue),
                     "binom_p_vs_t": float(stats.binomtest(hits, n, p_t).pvalue)})
    return rows


def oos_loglik(train: np.ndarray, test: np.ndarray, tfit: dict) -> dict:
    """Average out-of-sample log-likelihood per day (higher = better)."""
    mu, sd = float(np.mean(train)), float(np.std(train, ddof=1))
    ll_n = stats.norm.logpdf(test, mu, sd).mean()
    ll_t = stats.t.logpdf(test, tfit["df"], tfit["loc"], tfit["scale"]).mean()
    return {"normal": float(ll_n), "t": float(ll_t), "t_minus_normal": float(ll_t - ll_n)}


def vix_regime(df, mu: float, sd: float, k: float, high_cut: float, col: str = "vixcls") -> dict:
    """2x2: extreme day (|r-mu|>k*sd) vs previous-day VIX above `high_cut`."""
    d = df.dropna(subset=[col])
    ext = (np.abs(d["ret"].to_numpy() - mu) > k * sd)
    high = d[col].to_numpy() >= high_cut
    a = int(np.sum(ext & high)); b = int(np.sum(~ext & high))
    c = int(np.sum(ext & ~high)); e = int(np.sum(~ext & ~high))
    p_high = a / (a + b) if a + b else float("nan")
    p_low = c / (c + e) if c + e else float("nan")
    odds, p = stats.fisher_exact([[a, b], [c, e]])
    return {"k": k, "vix_high_cut": float(high_cut),
            "table": {"extreme_high": a, "normal_high": b, "extreme_low": c, "normal_low": e},
            "p_extreme_given_high": p_high, "p_extreme_given_low": p_low,
            "risk_ratio": p_high / p_low if p_low else float("nan"),
            "odds_ratio": float(odds), "fisher_p": float(p)}
