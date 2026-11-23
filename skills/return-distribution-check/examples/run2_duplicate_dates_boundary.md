# 使用案例 2：邊界／異常資料

- **日期**：2026-11-23
- **情境**：同一技能第 2 次使用，刻意餵壞資料，確認技能會**停止**而不是印出漂亮但錯誤的表。
- **輸入 2a**：`skilltest_duplicates.csv` ＝ 2330 價格再插入 3 列重複日期（第 100、500、900 列複製）。
- **輸入 2b**：`skilltest_short.csv` ＝ 只取最後 100 列（99 筆報酬）。
- **指令**：
  ```
  python skills/return-distribution-check/check_returns.py data/processed/skilltest_duplicates.csv --out results/skill/run2a_duplicates
  python skills/return-distribution-check/check_returns.py data/processed/skilltest_short.csv --out results/skill/run2b_short
  ```
- **預期**：兩者都 exit 2、不計算任何統計量，並說明原因。
- **實際**：2a exit 2（3 duplicate dates）；2b exit 2（only 99 returns < 250）。符合規格。
- **注意**：第一次在終端機用 `| tail` 看輸出時顯示 exit 0，那是管線最後一個指令 `tail` 的結束碼；
  不經管線重跑才確認真實結束碼為 2。

## 技能輸出 2a（原樣）

# return-distribution-check: skilltest_duplicates.csv

exit code: **2**

## Integrity gates

| check | value |
|---|---|
| rows | 2432 |
| bad_dates | 0 |
| missing_close | 0 |
| nonpositive_close | 0 |
| duplicate_dates | 3 |

**STOPPED:** 3 duplicate dates - would create spurious returns and inflate any date join; fix the source, do not auto-drop

No statistics were computed.

## 技能輸出 2b（原樣）

# return-distribution-check: skilltest_short.csv

exit code: **2**

## Integrity gates

| check | value |
|---|---|
| rows | 100 |
| bad_dates | 0 |
| missing_close | 0 |
| nonpositive_close | 0 |
| duplicate_dates | 0 |
| returns | 99 |

**STOPPED:** only 99 returns (< 250); 3 SD frequency would rest on <1 expected day

No statistics were computed.
