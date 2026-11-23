# 測試計畫與結果

預期值一律由定義、理論、教科書或獨立實作決定，不採用被測程式自己的輸出。
執行日期 2026-11-23，Windows 11、Python 3.14.4、R 4.6.1。

| 編號 | 層次 | 輸入與預期 | 實際結果與證據 | 判定 |
|---|---|---|---|---|
| T01 | 計算 | 8 點手算資料：偏態 0、峰態＝m4/m2²−3、SD 用 n−1 | `test_hand_example` | 通過 |
| T02 | 統計 | 20 萬筆模擬常態：偏態、峰態近 0，JB 不拒絕 | `test_large_normal_sample_is_close_to_theory` | 通過 |
| T03 | 邊界 | 少於 8 筆、零變異 → 拋 ValueError | `test_boundary_too_few_and_constant` | 通過 |
| T04 | 計算 | Wilson 10/100 → (0.0552, 0.1744)（教科書值） | `test_wilson_known_value` | 通過 |
| T05 | 邊界 | Wilson 0/n、n/n、0/0 | `test_wilson_edges` | 第一次失敗（D-02），修正後通過 |
| T06 | 統計 | 真的是常態時，常態模型不可被拒絕（固定種子） | `test_exceedance_on_simulated_normal_matches_normal` | 第一次失敗（D-03），修正判準後通過 |
| T07 | 統計 | i.i.d. 不拒絕、分段波動必拒絕（Ljung-Box） | `test_iid_not_rejected_and_garch_like_rejected` | 通過 |
| T08 | 資料 | 重複日期保留後者、空值計數 | `test_duplicates_keep_last_and_drop_missing` | 第一次 ERROR（D-01），修正後通過 |
| T09 | 邊界 | 少於 60 筆價格 → 停止 | `test_too_short_series_stops` | 通過 |
| T10 | 資料 | TWSE 重複日期 → 停止，不可讓合併列數膨脹 | `test_twse_duplicate_key_stops_instead_of_inflating` | 通過 |
| T11 | 資料洩漏 | VIX 只能貼前一日，不可貼當日 | `test_vix_is_strictly_previous_day` | 通過 |
| T12 | 資料洩漏 | 切分依時間，訓練期全在測試期之前 | `test_split_is_chronological` | 通過 |
| T13 | 計算 | 活頁簿複製版：手算 3 筆報酬的 SD | `test_hand_series` | 通過 |
| T14 | 計算 | 活頁簿樣本長度規則 max(520, PERIOD) | `test_sample_is_520_when_period_smaller` | 通過 |
| T15 | 獨立實作 | R 重算動差、JB、Shapiro、Ljung-Box、t 擬合、超越次數、Wilson、二項檢定、滾動次數 | `results/tables/r_check_2330_TW.csv` 26/26 | 通過 |
| T16 | 系統 | 活頁簿副本實際執行 VBA vs Python 複製版 | `docs/evidence/workbook_vs_python_2330_20261123.json` | 通過（完全一致） |
| T17 | 資料 | Yahoo vs TWSE 收盤價（容差 0.5%） | 478 天 100% 相同；發現 1 筆非交易日（D-04） | 通過，並修正清理規則 |
| T18 | 邊界 | skill：重複日期、少於 250 筆 → exit 2、不輸出統計 | `results/skill/run2a_*`、`run2b_*` | 通過 |
| T19 | 系統 | `--offline` 重跑結果與線上相同 | 同一份 raw 資料，線上與離線的超越率表逐位相同（V1 線上 vs V2 離線） | 通過 |

## 執行方式

```
python -m unittest discover -s python/tests -v      # T01–T14
Rscript r/verify.R 2330_TW                          # T15（需先跑 run_all.py）
powershell -STA -File python/run_workbook_check.ps1 -Book <活頁簿副本> -Ticker 2330 -Period 250 -Out out.json   # T16
```

## 尚未做

- 使用者測試（由非作者依 README 操作）——排在 12/17 前。
- 多個切點的穩健性檢查（只做了 70/30 一次）。
