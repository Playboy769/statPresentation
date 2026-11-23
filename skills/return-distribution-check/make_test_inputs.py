"""Rebuild the three skill example inputs from the raw Yahoo file.

Run from the repo root after `python python/run_all.py` has downloaded data:
    python skills/return-distribution-check/make_test_inputs.py
Writes data/processed/prices_2330_TW.csv, skilltest_duplicates.csv, skilltest_short.csv.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
import fetch as F  # noqa: E402
import integrate as I  # noqa: E402

out = ROOT / "data" / "processed"
p, _ = I.clean_prices(F.parse_yahoo((F.RAW / "yahoo_2330_TW.json").read_bytes()))
p["date"] = p["date"].dt.strftime("%Y-%m-%d")
p.to_csv(out / "prices_2330_TW.csv", index=False)
pd.concat([p, p.iloc[[100, 500, 900]]]).sort_values("date").to_csv(out / "skilltest_duplicates.csv", index=False)
p.tail(100).to_csv(out / "skilltest_short.csv", index=False)
print("wrote 3 files to", out)
