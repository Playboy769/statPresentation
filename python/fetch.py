"""Data acquisition from three independent public sources.

1. Yahoo Finance chart API  -> daily close for any ticker (same source and
   field the Ticker Volatility workbook uses: `close`, not `adjclose`).
2. TWSE STOCK_DAY (official exchange data) -> raw daily close for Taiwan
   listed stocks, used to cross-validate the Yahoo series.
3. FRED fredgraph.csv -> VIXCLS (CBOE volatility index), used as an external
   "market stress" label to see where extreme days fall.

Each fetch writes an untouched raw file to data/raw/ and returns a tidy
DataFrame. Raw files are never edited afterwards; cleaning is in integrate.py.
"""
from __future__ import annotations

import hashlib
import io
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifest.json"

YAHOO_UA = "Mozilla/5.0 (statPresentation course project)"


def _record(name: str, path: Path, url: str, rows: int) -> None:
    """Append source metadata (download time, sha256, row count) to the manifest."""
    meta = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    meta[name] = {
        "file": path.relative_to(ROOT).as_posix(),
        "url": url,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": rows,
    }
    MANIFEST.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def safe_name(ticker: str) -> str:
    return ticker.replace("^", "IDX_").replace(".", "_").replace("=", "_")


# ---------------------------------------------------------------- Yahoo
def parse_yahoo(raw: bytes) -> pd.DataFrame:
    res = json.loads(raw)["chart"]["result"][0]
    tz = res["meta"].get("exchangeTimezoneName", "UTC")
    ts = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz)
    df = pd.DataFrame({"date": ts.date, "close": res["indicators"]["quote"][0]["close"]})
    # Ticker Volatility reads "adjclose" (dividend/split adjusted) when present -
    # see VT/modVT.bas FetchYahooSeries - so keep both columns.
    adj = res["indicators"].get("adjclose")
    df["adjclose"] = adj[0]["adjclose"] if adj else df["close"]
    return df


def parse_yahoo_dividends(raw: bytes) -> pd.DataFrame:
    """Cash dividends from the same Yahoo response (events=div). Used only to
    explain ex-dividend gaps between SPY (price return) and the S&P 500 index."""
    res = json.loads(raw)["chart"]["result"][0]
    tz = res["meta"].get("exchangeTimezoneName", "UTC")
    ev = res.get("events", {}).get("dividends", {}) or {}
    rows = [(pd.Timestamp(v["date"], unit="s", tz="UTC").tz_convert(tz).date(), float(v["amount"])) for v in ev.values()]
    df = pd.DataFrame(rows, columns=["date", "dividend"])
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def fetch_yahoo(ticker: str, rng: str = "10y") -> pd.DataFrame:
    sym = requests.utils.quote(ticker, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval=1d&events=div%7Csplit"
    r = requests.get(url, headers={"User-Agent": YAHOO_UA}, timeout=20)
    r.raise_for_status()
    path = RAW / f"yahoo_{safe_name(ticker)}.json"
    path.write_bytes(r.content)
    df = parse_yahoo(r.content)
    _record(f"yahoo_{ticker}", path, url, len(df))
    return df


# ---------------------------------------------------------------- TWSE
def _roc_to_date(s: str) -> date:
    y, m, d = (int(x) for x in s.strip().split("/"))
    return date(y + 1911, m, d)


def parse_twse(raws: list) -> pd.DataFrame:
    frames = []
    for js in raws:
        if js.get("stat") == "OK" and js.get("data"):
            f = js["fields"]
            i_date, i_close = f.index("日期"), f.index("收盤價")
            rows = [(_roc_to_date(row[i_date]), row[i_close].replace(",", "")) for row in js["data"]]
            frames.append(pd.DataFrame(rows, columns=["date", "close_twse"]))
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "close_twse"])
    # "--" marks a halted / no-trade price; keep as NaN, handled in integrate.py
    df["close_twse"] = pd.to_numeric(df["close_twse"], errors="coerce")
    return df


def fetch_twse(stock_no: str, months: int, sleep_s: float = 3.0) -> pd.DataFrame:
    """Monthly STOCK_DAY requests, newest month backwards. TWSE throttles bursts,
    so we sleep between calls (see docs/data_dictionary.md, rate limit note)."""
    raws = []
    today = date.today()
    y, m = today.year, today.month
    for i in range(months):
        url = (f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json"
               f"&date={y}{m:02d}01&stockNo={stock_no}")
        r = requests.get(url, headers={"User-Agent": YAHOO_UA}, timeout=20)
        r.raise_for_status()
        raws.append(r.json())
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        if i < months - 1:
            time.sleep(sleep_s)
    path = RAW / f"twse_{stock_no}.json"
    path.write_text(json.dumps(raws, ensure_ascii=False), encoding="utf-8")
    df = parse_twse(raws)
    _record(f"twse_{stock_no}", path, "https://www.twse.com.tw/exchangeReport/STOCK_DAY", len(df))
    return df


# ---------------------------------------------------------------- FRED
def parse_fred(raw: bytes, series: str) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = ["date", series.lower()]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df[series.lower()] = pd.to_numeric(df[series.lower()], errors="coerce")  # "." = missing
    return df


def fetch_fred(series: str) -> pd.DataFrame:
    # No custom User-Agent: FRED stalls on browser-like UAs (observed before).
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    path = RAW / f"fred_{series}.csv"
    path.write_bytes(r.content)
    df = parse_fred(r.content, series)
    _record(f"fred_{series}", path, url, len(df))
    return df
