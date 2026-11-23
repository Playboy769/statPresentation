# statPresentation：股票日報酬是常態嗎？±kσ 會低估多少極端波動？

115-1 程式設計與統計軟體 分組期末專題（資料分析路線）。

## 專題問題

[Ticker Volatility](docs/workbook_check.md) 活頁簿會畫出 ±1/2/3 SD 區間。若把它讀成常態機率
（68% / 95% / 99.7%），等於假設日報酬服從常態且彼此獨立。本專題回答：

> 股票日報酬是否服從常態分布？若否，用 ±kσ 判斷「極端波動」會低估多少機率？
> 改用 Student-t 分布或歷史分位數能不能改善？（前 70% 期間估參數、後 30% 驗證）

**目前狀態：流程驗證版**，只用 2330.TW 跑通；正式標的待組員決定（[decisions.md](docs/decisions.md) D-05）。
主要發現（僅限 2330.TW）：日報酬尖峰厚尾且波動群聚；樣本外 3σ 極端日是常態預測的約 12 倍
（滾動 SD 約 7 倍）。詳見 [docs/results.md](docs/results.md)。

## 成員與分工

| 成員 | 負責 | 審查 |
|---|---|---|
| ＿＿ | 問題與統計設計 | ＿＿ |
| ＿＿ | 資料與程式實作 | ＿＿ |
| ＿＿ | 測試與 AI 協作 | ＿＿ |
| ＿＿ | 整合與溝通 | ＿＿ |

## 資料來源與授權

| 資料 | 提供者 | 授權 |
|---|---|---|
| 日收盤價 | Yahoo Finance chart API | 不重新散布；repo 只附取得程式 |
| 台股官方收盤價 | 臺灣證券交易所 STOCK_DAY | 政府開放資料，標示來源 |
| VIXCLS | FRED（St. Louis Fed）／CBOE | 公開，引用標示來源 |

欄位、整合方式與品質紀錄：[docs/data_dictionary.md](docs/data_dictionary.md)。
`data/raw/` 不進 git；每次下載的時間、SHA-256 與列數寫在 `data/manifest.json`。

## 環境

- 開發環境：Windows 11、Python 3.14.4、R 4.6.1（另需 R 內建的 MASS 與 jsonlite）。
- Python：
  ```
  python -m venv .venv
  .venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
  pip install -r requirements.txt
  ```
- R：只用 base R＋MASS＋jsonlite，版本資訊在 `r/sessionInfo.txt`。尚未建立 `renv.lock`（見「已知問題」）。
- 活頁簿對帳（選用）：需 Windows＋Excel。腳本以 `AutomationSecurity = 1`（允許巨集）開啟活頁簿執行 `RunVT`，請只對自己信任的活頁簿**副本**使用。

## 執行順序（從 repo 根目錄）

| 步驟 | 指令 | 產出 | 約略時間 |
|---|---|---|---|
| 1 抓資料＋分析 | `python python/run_all.py` | `data/raw/`、`data/processed/`、`results/tables/`、`results/figures/` | ~2 分鐘（TWSE 每次請求間隔 3 秒） |
| 1' 離線重跑 | `python python/run_all.py --offline` | 同上，用既有 raw | 數秒 |
| 2 R 獨立檢核 | `Rscript r/verify.R 2330_TW` | `results/tables/r_check_2330_TW.csv` | 數秒 |
| 3 單元測試 | `python -m unittest discover -s python/tests -v` | 14 項 | 數秒 |
| 4 skill | `python skills/return-distribution-check/make_test_inputs.py` 後依 [SKILL.md](skills/return-distribution-check/SKILL.md) 執行 | `results/skill/` | 數秒 |
| 5 活頁簿對帳（選用） | `powershell -STA -File python/run_workbook_check.ps1 -Book <活頁簿副本.xlsm> -Ticker 2330 -Period 250 -Out out.json` | JSON | ~30 秒 |

換標的：改 `config.json` 的 `tickers`（任何 Yahoo 代號；台股上市 `.TW` 會自動做 TWSE 交叉驗證）。

## 最小示例與預期輸出

`python python/run_all.py` 對 2330.TW 印出（2026-11-23 下載；資料每天變，數字會小幅移動）：

```
2330.TW: n=1698 sd=1.6028% skew=0.35 exkurt=3.33 JB p=7e-179
  k=3: normal 0.0027  t 0.0113  hist 0.0106  observed 0.0316 [0.0211,0.0469]  x11.69
```

驗收：`r/verify.R` 必須印出 `26 / 26 checks passed`（結束碼 0）；單元測試 `OK`。
容差：動差相對誤差 1e-9、t 擬合 df 5%（兩語言最佳化器不同）、次數必須完全相同。

## 隨機性

只有單元測試用到亂數，種子固定（`20261123`、`1`、`7`）。主分析沒有模擬，結果是確定性的。

## 文件

| 文件 | 內容 |
|---|---|
| [docs/results.md](docs/results.md) | 分析結果、結論與限制 |
| [docs/data_dictionary.md](docs/data_dictionary.md) | 資料來源、欄位、整合、品質紀錄 |
| [docs/workbook_check.md](docs/workbook_check.md) | 與 Ticker Volatility 活頁簿逐格對帳 |
| [docs/test_plan.md](docs/test_plan.md) | 測試 T01–T19 與結果 |
| [docs/ai_workflow.md](docs/ai_workflow.md) | AI agent workflow（規劃→審查→實作→測試→修正）與人工決策點 |
| [docs/ai_disclosure.md](docs/ai_disclosure.md) | AI 使用揭露、主要提示、查核 |
| [docs/vibe_coding_log.md](docs/vibe_coding_log.md) | 自然語言迭代的版本紀錄 |
| [docs/debug_log.md](docs/debug_log.md) | 實際發生的錯誤與修正 D-01..D-05 |
| [docs/decisions.md](docs/decisions.md) | 決策紀錄與待追蹤 |
| [skills/return-distribution-check/](skills/return-distribution-check/SKILL.md) | 可重用 AI skill 與兩次使用案例 |

## 已知問題

- 只有一檔標的；結論不可外推。
- R 尚未建立 `renv.lock`（本機未安裝 renv）；目前以 `r/sessionInfo.txt` 記錄版本。
- TWSE 交叉驗證只涵蓋最近 24 個月，更早期間的 Yahoo 非交易日陳舊列無法檢出（debug_log D-04）。
- 尚未由非作者依本 README 獨立重跑（排在 12/17 前）。

## 授權

程式碼：待組員決定（建議 MIT）。文件與圖表：待定。第三方資料依各提供者條款，不隨 repo 散布。
