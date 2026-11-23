# 使用案例 1：正常資料（2330.TW，10 年日收盤）

- **日期**：2026-11-23
- **情境**：新標的進入專案前的檢查（指引 06：以不同輸入執行同一技能，第 1 次）。
- **指令**：
  ```
  python skills/return-distribution-check/check_returns.py data/processed/prices_2330_TW.csv --out results/skill/run1_2330
  ```
- **輸入**：`prices_2330_TW.csv`（由 Yahoo raw 經 `clean_prices` 產生，2429 列；此時尚未套用 D-04 的非交易日刪除）。
- **預期**：通過三道關卡；股票日報酬一般為厚尾且有波動群聚 → 預期出現 FAT_TAILS、CLUSTERING。
- **實際**：exit 0，旗標 `FAT_TAILS, CLUSTERING`，與預期相符。
- **人工判讀**：旗標只是提醒；正式結論仍以 `run_all.py` 的樣本外結果與 R 檢核為準（SKILL.md 禁止事項）。

## 技能輸出（原樣）

# return-distribution-check: prices_2330_TW.csv

exit code: **0**

## Integrity gates

| check | value |
|---|---|
| rows | 2429 |
| bad_dates | 0 |
| missing_close | 0 |
| nonpositive_close | 0 |
| duplicate_dates | 0 |
| returns | 2428 |

## Diagnostics (2016-11-23..2026-11-23, n=2428)

- SD 1.7668%, skew 0.264, excess kurtosis 3.665
- Jarque-Bera 1387.5, p = 5.19e-302
- Ljung-Box on squared returns (lag 10): Q = 265.9, p = 2.4e-51

| band | observed share beyond | 95% CI | normal value | hits |
|---|---|---|---|---|
| 1 SD | 0.2512 | [0.2344, 0.2689] | 0.3173 | 610 |
| 2 SD | 0.0482 | [0.0404, 0.0574] | 0.0455 | 117 |
| 3 SD | 0.0115 | [0.0080, 0.0166] | 0.0027 | 28 |

**Flags:** FAT_TAILS, CLUSTERING

_Flags are prompts for review, not conclusions. Full-sample numbers; for out-of-sample use run_all.py._
