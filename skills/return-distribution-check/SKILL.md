---
name: return-distribution-check
description: Check a price/return CSV before anyone reads +/-k SD bands as "probabilities" - data integrity first, then normality and tail-frequency diagnostics. Use when a team member brings a new ticker or data file into the project, or before quoting any "x% of days fall inside 2 SD" statement.
version: 1.0 (2026-11-23)
---

# return-distribution-check

## Purpose
The Ticker Volatility workbook draws +/-1/2/3 SD bands. Reading those bands as
"68% / 95% / 99.7% of days" silently assumes normal, independent returns. This
skill makes that assumption explicit and checkable for any new data file, and
**refuses to produce statistics when the data are broken** (duplicate dates,
too short, constant prices) instead of printing a plausible-looking table.

## When to use
- A new ticker or CSV enters the project (before it goes into `run_all.py`).
- Someone wants to quote an exceedance probability from SD bands.

Do **not** use it to decide whether a model is "correct" - it only flags.
Conclusions still come from `python/run_all.py` + `r/verify.R` and human review.

## Input
CSV with columns `date` and `close` (daily, any order). Optional extra columns are ignored.

## Steps (what the script does, in order)
1. **Integrity gate** - parse dates, count missing / non-positive closes,
   duplicate dates. Duplicate dates => STOP (exit 2): a duplicate would create a
   zero or double-counted return and inflate the join in `integrate.py`.
2. **Size gate** - fewer than 250 returns => STOP (exit 2): JB and 3 SD
   frequencies are meaningless on a few months (expected 3 SD count < 1).
3. **Variance gate** - zero variance => STOP (exit 2).
4. **Diagnostics** - n, SD, skew, excess kurtosis, Jarque-Bera p, Ljung-Box on
   squared returns (lag 10), and for k = 1, 2, 3: observed share of days with
   |r - mean| > k SD vs the normal value, with Wilson 95% CI.
5. **Flags (not verdicts)** - `FAT_TAILS` if excess kurtosis > 1 and the 3 SD
   frequency CI lies above the normal value; `CLUSTERING` if Ljung-Box p < 0.01;
   `NORMAL_OK` only if neither fires and JB p > 0.05.

## Output
`<out>.md` human-readable report + `<out>.json` machine-readable, same numbers.
Exit code: 0 = ran, 2 = stopped by a gate (report explains why).

## How to run
```
python skills/return-distribution-check/check_returns.py <input.csv> --out results/skill/<name>
```

## Prohibitions
- Never fill missing prices or drop duplicates automatically - report and stop.
- Never state "returns are normal"; the strongest wording is "no evidence against normality at this sample size".
- Never present full-sample numbers as out-of-sample performance.

## Verification of the skill itself
`examples/` holds two documented runs:
1. `run1_2330_normal_case.md` - real data, expected: runs, FAT_TAILS + CLUSTERING.
2. `run2_duplicate_dates_boundary.md` - same data with injected duplicate dates
   and a 100-row file, expected: both STOP with exit 2 and no statistics.

## Known limitations
- Daily simple returns only; no frequency conversion.
- 250-return floor is a judgement call (one trading year), not a derived constant.
