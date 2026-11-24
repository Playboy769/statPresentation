"""End-to-end pipeline:  fetch -> clean -> cross-check -> integrate -> analyze -> figures.

Usage (from the repo root):
    python python/run_all.py              # download fresh data
    python python/run_all.py --offline    # reuse data/raw/ (no network)
    python python/run_all.py --tickers 2330.TW QQQ
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
# Chinese labels: Times New Roman for Latin text, DFKai-SB (標楷體, Windows) for CJK glyphs
plt.rcParams["font.family"] = ["Times New Roman", "DFKai-SB"]
plt.rcParams["axes.unicode_minus"] = False
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze as A  # noqa: E402
import fetch as F  # noqa: E402
import integrate as I  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TAB = ROOT / "results" / "tables"
FIG = ROOT / "results" / "figures"


def load(ticker: str, cfg: dict, offline: bool):
    name = F.safe_name(ticker)
    if offline:
        y = F.parse_yahoo((F.RAW / f"yahoo_{name}.json").read_bytes())
    else:
        y = F.fetch_yahoo(ticker, cfg["yahoo_range"])
    raw_y = (F.RAW / f"yahoo_{name}.json").read_bytes()
    divs = F.parse_yahoo_dividends(raw_y)
    idx = None
    series = cfg.get("index_crosscheck", {}).get(ticker)
    if series:
        idx = (F.parse_fred((F.RAW / f"fred_{series}.csv").read_bytes(), series) if offline
               else F.fetch_fred(series))
    tw = None
    if ticker.endswith(".TW") and ticker[:-3].isdigit():
        no = ticker[:-3]
        p = F.RAW / f"twse_{no}.json"
        tw = (F.parse_twse(json.loads(p.read_text(encoding="utf-8"))) if offline
              else F.fetch_twse(no, cfg["twse_crosscheck_months"], cfg["twse_sleep_seconds"]))
    return y, tw, idx, divs


def load_vix(cfg: dict, offline: bool) -> pd.DataFrame:
    s = cfg["fred_series"][0]
    if offline:
        return F.parse_fred((F.RAW / f"fred_{s}.csv").read_bytes(), s)
    return F.fetch_fred(s)


def figures(name: str, ticker: str, train, test, tfit, exc, cross) -> list[str]:
    out = []
    mu, sd = train.mean(), train.std(ddof=1)

    # 1 histogram vs normal and t (train)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(train, bins=80, density=True, color="#9ca3af", label=f"訓練期日報酬（n = {train.size}）")
    xs = np.linspace(train.min(), train.max(), 600)
    ax.plot(xs, stats.norm.pdf(xs, mu, sd), color="#1d4ed8", lw=1.6, label="常態分布")
    ax.plot(xs, stats.t.pdf(xs, tfit["df"], tfit["loc"], tfit["scale"]), color="#c2410c", lw=1.6,
            label=f"Student-t 分布（自由度 {tfit['df']:.1f}）")
    ax.set_yscale("log"); ax.set_ylim(bottom=0.05)
    ax.set_xlabel("日報酬"); ax.set_ylabel("密度（對數刻度）")
    ax.legend(frameon=False, fontsize=8)
    p = FIG / f"fig1_hist_{name}.png"; fig.tight_layout(); fig.savefig(p, dpi=140); plt.close(fig); out.append(p)

    # 2 QQ plot vs normal
    fig, ax = plt.subplots(figsize=(5, 5))
    z = (np.sort(train) - mu) / sd
    q = stats.norm.ppf((np.arange(1, z.size + 1) - 0.5) / z.size)
    ax.scatter(q, z, s=4, color="#374151")
    lim = max(abs(z).max(), abs(q).max())
    ax.plot([-lim, lim], [-lim, lim], color="#1d4ed8", lw=1)
    ax.set_xlabel("常態分位數"); ax.set_ylabel("標準化報酬（z）")
    p = FIG / f"fig2_qq_{name}.png"; fig.tight_layout(); fig.savefig(p, dpi=140); plt.close(fig); out.append(p)

    # 3 out-of-sample exceedance: predicted vs observed with 95% CI
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ks = [r["k"] for r in exc]; x = np.arange(len(ks)); w = 0.2
    for j, (key, lab, col) in enumerate([("p_normal", "常態預測（活頁簿解讀）", "#9ca3af"),
                                         ("p_t", "Student-t 預測", "#ea8a2e"),
                                         ("p_hist_train", "歷史頻率預測", "#86c98a")]):
        ax.bar(x + (j - 1.5) * w, [r[key] for r in exc], w, label=lab, color=col)
    obs = np.array([r["p_observed"] for r in exc])
    err = np.array([[r["p_observed"] - r["ci95_low"] for r in exc], [r["ci95_high"] - r["p_observed"] for r in exc]])
    ax.bar(x + 1.5 * w, obs, w, color="#2563eb", label="測試期實際（95% 信賴區間）", yerr=err, capsize=3)
    ax.set_yscale("log"); ax.set_xticks(x, [f"超出 {k} SD" for k in ks])
    ax.set_ylabel("每日發生機率（對數刻度）")
    ax.legend(frameon=False, fontsize=8)
    p = FIG / f"fig3_exceed_{name}.png"; fig.tight_layout(); fig.savefig(p, dpi=140); plt.close(fig); out.append(p)

    # 4 cross-check figure
    if cross is not None and len(cross) and "r_idx" in cross:
        fig, ax = plt.subplots(figsize=(8, 3.4))
        ax.plot(cross["date"], cross["diff"] * 100, color="#9ca3af", lw=0.7, label="SPY 報酬 − S&P 500 指數報酬")
        ex = cross[cross["ex_div"]]
        ax.scatter(ex["date"], ex["diff"] * 100, s=14, color="#c2410c", zorder=3, label="除息日")
        ax.axhline(0, color="#111827", lw=0.6)
        ax.set_ylabel("差距（百分點）")
        ax.legend(frameon=False, fontsize=8)
        p = FIG / f"fig4_crosscheck_{name}.png"; fig.tight_layout(); fig.savefig(p, dpi=140); plt.close(fig); out.append(p)
    elif cross is not None and len(cross):
        fig, ax = plt.subplots(figsize=(8, 3.2))
        ax.plot(cross["date"], cross["rel_diff"] * 100, color="#374151", lw=0.8)
        ax.set_ylabel("Yahoo / TWSE - 1 (%)")
        ax.set_title(f"Fig.4 {ticker}: Yahoo close vs official TWSE close ({len(cross)} matched days)")
        p = FIG / f"fig4_crosscheck_{name}.png"; fig.tight_layout(); fig.savefig(p, dpi=140); plt.close(fig); out.append(p)
    return [Path(x).relative_to(ROOT).as_posix() for x in out]


def fig_rolling(name, ticker, exc, roll) -> str:
    """Fig.5: same observed-vs-normal question, fixed train SD vs rolling SD."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ks = [r["k"] for r in roll]; x = np.arange(len(ks)); w = 0.2
    ax.bar(x - 1.5 * w, [r["p_normal"] for r in roll], w, color="#9ca3af", label="常態預測")
    ax.bar(x - 0.5 * w, [r["p_t_unitvar"] for r in roll], w, color="#ea8a2e", label="Student-t 預測")
    for j, (rows, lab, col) in enumerate([(exc, "實際（固定訓練期 SD）", "#93c5fd"),
                                          (roll, f"實際（滾動 {roll[0]['window']} 日 SD）", "#2563eb")]):
        o = np.array([r["p_observed"] for r in rows])
        e = np.array([[r["p_observed"] - r["ci95_low"] for r in rows], [r["ci95_high"] - r["p_observed"] for r in rows]])
        ax.bar(x + (0.5 + j) * w, o, w, color=col, yerr=e, capsize=3, label=lab)
    ax.set_yscale("log"); ax.set_xticks(x, [f"超出 {k} SD" for k in ks])
    ax.set_ylabel("每日發生機率（對數刻度）")
    ax.legend(frameon=False, fontsize=8)
    p = FIG / f"fig5_rolling_{name}.png"; fig.tight_layout(); fig.savefig(p, dpi=140); plt.close(fig)
    return p.relative_to(ROOT).as_posix()


def fig_windows(name, ticker, wins) -> str:
    """Fig.6: share of days beyond k SD in the latest 200/500/2000 days vs normal."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ks = [e["k"] for e in wins[0]["exceedance"]]; x = np.arange(len(ks)); w = 0.8 / (len(wins) + 1)
    ax.bar(x - 0.4 + w / 2, [e["p_normal"] for e in wins[0]["exceedance"]], w, color="#9ca3af", label="常態預期")
    shades = ["#bfdbfe", "#60a5fa", "#2563eb"]
    for j, wv in enumerate(wins):
        ex = wv["exceedance"]
        o = np.array([e["p_observed"] for e in ex])
        err = np.array([[e["p_observed"] - e["ci95_low"] for e in ex], [e["ci95_high"] - e["p_observed"] for e in ex]])
        ax.bar(x - 0.4 + w * (j + 1.5), np.maximum(o, 1e-4), w, color=shades[j % 3], yerr=err, capsize=3,
               label=f"最近 {wv['n']} 日")
    ax.set_yscale("log"); ax.set_xticks(x, [f"超出 {k} SD" for k in ks])
    ax.set_ylabel("天數比例（對數刻度）")
    ax.legend(frameon=False, fontsize=8)
    p = FIG / f"fig6_windows_{name}.png"; fig.tight_layout(); fig.savefig(p, dpi=140); plt.close(fig)
    return p.relative_to(ROOT).as_posix()


def run_one(ticker: str, cfg: dict, vix: pd.DataFrame, offline: bool) -> dict:
    name = F.safe_name(ticker)
    y_raw, tw, idx, divs = load(ticker, cfg, offline)
    # cross-checks compare the unadjusted close with other price-only sources;
    # the analysis uses cfg["price_field"] (adjclose = what the workbook uses)
    prices, q_clean = I.clean_prices(y_raw[["date", "close"]])
    field = cfg.get("price_field", "close")
    main, q_main = I.clean_prices(y_raw[["date", field]].rename(columns={field: "close"}))
    q_clean = {"close": q_clean, field: q_main}
    cross, q_cross, q_idx = (None, None, None)
    if idx is not None:
        series = cfg["index_crosscheck"][ticker]
        cross, q_idx = I.crosscheck_index(prices, idx, series.lower(), divs, cfg["index_return_tolerance"])
    if tw is not None:
        cross, q_cross = I.crosscheck_twse(prices, tw, cfg["price_match_tolerance"])
        prices, q_cross["dropped_non_trading_yahoo_bars"] = I.drop_non_trading(prices, q_cross["only_yahoo_dates"])
        main, _ = I.drop_non_trading(main, q_cross["only_yahoo_dates"])
    rets_all = I.simple_returns(main)
    windows = [dict(window=n, **A.window_stats(I.last_n(rets_all, n)["ret"].to_numpy(), cfg["k_sigma"]))
               for n in cfg.get("windows", [])]
    rets = I.last_n(rets_all, cfg.get("analysis_window"))
    rets, q_vix = I.attach_vix(rets, vix)
    train, test = I.time_split(rets, cfg["train_fraction"])
    rets["sample"] = ["train"] * len(train) + ["test"] * len(test)
    rets.to_csv(PROC / f"returns_{name}.csv", index=False)

    tr, te = train["ret"].to_numpy(), test["ret"].to_numpy()
    tfit = A.fit_t(tr)
    exc = A.exceedance_table(tr, te, cfg["k_sigma"], tfit)
    mu, sd = tr.mean(), tr.std(ddof=1)
    vix_cut = float(train["vixcls"].quantile(cfg["vix_high_quantile"]))
    res = {
        "ticker": ticker,
        "period": f"{rets['date'].min().date()}..{rets['date'].max().date()}",
        "split": {"train": f"{train['date'].min().date()}..{train['date'].max().date()}",
                  "test": f"{test['date'].min().date()}..{test['date'].max().date()}",
                  "n_train": int(len(train)), "n_test": int(len(test))},
        "analysis_window": cfg.get("analysis_window"),
        "price_field": field,
        "quality": {"clean": q_clean, "twse_crosscheck": q_cross, "index_crosscheck": q_idx,
                    "dividends_in_data": int(len(divs)), "vix_attach": q_vix},
        "windows": windows,
        "moments": {"full": A.moments(rets["ret"]), "train": A.moments(tr), "test": A.moments(te)},
        "shapiro_train": A.shapiro(tr),
        "ljung_box_sq_train": A.ljung_box_sq(tr),
        "t_fit_train": tfit,
        "exceedance": exc,
        "exceedance_rolling": A.rolling_exceedance(rets["ret"].to_numpy(), len(train),
                                                   cfg["rolling_window"], cfg["k_sigma"], tfit["df"]),
        "oos_loglik": A.oos_loglik(tr, te, tfit),
        "vix_regime_full_k2": A.vix_regime(rets, mu, sd, 2, vix_cut),
    }
    res["figures"] = figures(name, ticker, tr, te, tfit, exc, cross) + [fig_rolling(name, ticker, exc, res["exceedance_rolling"])]         + ([fig_windows(name, ticker, windows)] if windows else [])
    (TAB / f"summary_{name}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    pd.DataFrame(exc).to_csv(TAB / f"exceedance_{name}.csv", index=False)
    pd.DataFrame(res["exceedance_rolling"]).to_csv(TAB / f"exceedance_rolling_{name}.csv", index=False)
    if windows:
        pd.DataFrame([{"window": w["window"], **e} for w in windows for e in w["exceedance"]]).to_csv(
            TAB / f"windows_{name}.csv", index=False)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--tickers", nargs="*")
    a = ap.parse_args(argv)
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    for d in (F.RAW, PROC, TAB, FIG):
        d.mkdir(parents=True, exist_ok=True)
    vix = load_vix(cfg, a.offline)
    for t in a.tickers or cfg["tickers"]:
        r = run_one(t, cfg, vix, a.offline)
        m = r["moments"]["train"]
        print(f"{t}: n={m['n']} sd={m['sd']:.4%} skew={m['skew']:.2f} exkurt={m['excess_kurtosis']:.2f} "
              f"JB p={m['jb_p']:.2g}")
        for e in r["exceedance"]:
            print(f"  k={e['k']}: normal {e['p_normal']:.4f}  t {e['p_t']:.4f}  hist {e['p_hist_train']:.4f}"
                  f"  observed {e['p_observed']:.4f} [{e['ci95_low']:.4f},{e['ci95_high']:.4f}]"
                  f"  x{e['ratio_obs_to_normal']:.2f}")
        for w in r["windows"]:
            mm = w["moments"]
            print(f"  window {w['n']}: sd={mm['sd']:.4%} exkurt={mm['excess_kurtosis']:.2f} JB p={mm['jb_p']:.2g} "
                  f"SW p={w['shapiro']['p']:.2g} beyond k: " + " ".join(
                      f"{e['k']}:{e['hits']}/{e['expected_normal']:.1f}" for e in w["exceedance"]))
        if r["quality"]["index_crosscheck"]:
            print("  index check:", r["quality"]["index_crosscheck"])
        for e in r["exceedance_rolling"]:
            print(f"  rolling{e['window']} k={e['k']}: normal {e['p_normal']:.4f}  t {e['p_t_unitvar']:.4f}"
                  f"  observed {e['p_observed']:.4f} [{e['ci95_low']:.4f},{e['ci95_high']:.4f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
