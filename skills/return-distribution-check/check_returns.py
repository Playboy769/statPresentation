"""return-distribution-check skill runner. See SKILL.md for the contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import analyze as A  # noqa: E402

MIN_RETURNS = 250


def run(path: Path) -> tuple[int, dict]:
    df = pd.read_csv(path)
    rep: dict = {"input": path.name, "gates": {}, "flags": []}
    missing = {"date", "close"} - set(df.columns)
    if missing:
        rep["stop"] = f"missing columns {sorted(missing)}"
        return 2, rep
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    g = rep["gates"]
    g["rows"] = int(len(df))
    g["bad_dates"] = int(df["date"].isna().sum())
    g["missing_close"] = int(df["close"].isna().sum())
    g["nonpositive_close"] = int((df["close"] <= 0).sum())
    g["duplicate_dates"] = int(df["date"].duplicated().sum())
    if g["duplicate_dates"] > 0:
        rep["stop"] = (f"{g['duplicate_dates']} duplicate dates - would create spurious returns "
                       "and inflate any date join; fix the source, do not auto-drop")
        return 2, rep
    d = df.dropna().query("close > 0").sort_values("date")
    r = (d["close"].to_numpy()[1:] / d["close"].to_numpy()[:-1]) - 1
    g["returns"] = int(r.size)
    if r.size < MIN_RETURNS:
        rep["stop"] = f"only {r.size} returns (< {MIN_RETURNS}); 3 SD frequency would rest on <1 expected day"
        return 2, rep
    if np.std(r) == 0:
        rep["stop"] = "zero variance"
        return 2, rep

    m = A.moments(r)
    lb = A.ljung_box_sq(r)
    mu, sd = r.mean(), r.std(ddof=1)
    bands = []
    for k in (1, 2, 3):
        hits = int(np.sum(np.abs(r - mu) > k * sd))
        lo, hi = A.wilson(hits, r.size)
        bands.append({"k": k, "observed": hits / r.size, "ci95": [lo, hi],
                      "normal": float(2 * (1 - __import__("scipy").stats.norm.cdf(k))), "hits": hits})
    rep.update({"period": f"{d['date'].min().date()}..{d['date'].max().date()}",
                "moments": m, "ljung_box_sq": lb, "bands": bands})
    if m["excess_kurtosis"] > 1 and bands[2]["ci95"][0] > bands[2]["normal"]:
        rep["flags"].append("FAT_TAILS")
    if lb["p"] < 0.01:
        rep["flags"].append("CLUSTERING")
    if not rep["flags"] and m["jb_p"] > 0.05:
        rep["flags"].append("NORMAL_OK")
    return 0, rep


def to_md(code: int, rep: dict) -> str:
    L = [f"# return-distribution-check: {rep['input']}", "", f"exit code: **{code}**", "",
         "## Integrity gates", "", "| check | value |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in rep["gates"].items()]
    if "stop" in rep:
        L += ["", f"**STOPPED:** {rep['stop']}", "", "No statistics were computed."]
        return "\n".join(L) + "\n"
    m = rep["moments"]
    L += ["", f"## Diagnostics ({rep['period']}, n={m['n']})", "",
          f"- SD {m['sd']:.4%}, skew {m['skew']:.3f}, excess kurtosis {m['excess_kurtosis']:.3f}",
          f"- Jarque-Bera {m['jb']:.1f}, p = {m['jb_p']:.3g}",
          f"- Ljung-Box on squared returns (lag {rep['ljung_box_sq']['lags']}): Q = {rep['ljung_box_sq']['Q']:.1f}, p = {rep['ljung_box_sq']['p']:.3g}",
          "", "| band | observed share beyond | 95% CI | normal value | hits |", "|---|---|---|---|---|"]
    for b in rep["bands"]:
        L.append(f"| {b['k']} SD | {b['observed']:.4f} | [{b['ci95'][0]:.4f}, {b['ci95'][1]:.4f}] | {b['normal']:.4f} | {b['hits']} |")
    L += ["", f"**Flags:** {', '.join(rep['flags']) or 'none'}", "",
          "_Flags are prompts for review, not conclusions. Full-sample numbers; for out-of-sample use run_all.py._"]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    code, rep = run(a.csv)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.with_suffix(".json").write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    a.out.with_suffix(".md").write_text(to_md(code, rep), encoding="utf-8")
    print(to_md(code, rep))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
