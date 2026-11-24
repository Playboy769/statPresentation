# statPresentation：股票日報酬是常態嗎？±kσ 會低估多少極端波動？

115-1 程式設計與統計軟體 分組期末專題（資料分析路線）。

## 專題問題

[Ticker Volatility](docs/workbook_check.md) 活頁簿會畫出 ±1/2/3 SD 區間。若把它讀成常態機率
（68% / 95% / 99.7%），等於假設日報酬服從常態且彼此獨立。本專題回答：

> 股票日報酬是否服從常態分布？若否，用 ±kσ 判斷「極端波動」會低估多少機率？
> 改用 Student-t 分布或歷史分位數能不能改善？（前 70% 期間估參數、後 30% 驗證）

**標的：SPY**（[decisions.md](docs/decisions.md) D-08），價格用 Yahoo 含息調整價 adjclose（與活頁簿相同）。
主要發現：最近 200、500、2,000 個交易日三視窗皆拒絕常態；超出 3σ 的天數是常態預期的 5–6 倍，
樣本外（2,000 日切 70/30）常態低估 3σ 極端日約 3.7 倍，t 分布與歷史頻率未被拒絕；
前一日 VIX 偏高時 2σ 極端日比例 17.8% vs 1.3%。詳見 [docs/results.md](docs/results.md)，
書面報告 [report/Report.docx](report/Report.docx)（PDF 同版）。

本專題為**雙主軸**：（一）產品——Ticker Volatility 活頁簿本身，原始碼在 [product/](product/README.md)，可用 `product/build.ps1` 從原始碼建出；
（二）研究——檢驗活頁簿的 SD 區間能否當常態機率讀。超出 3σ 的極端日只佔約 1.5% 的交易日，卻貢獻 28–40% 的總波動（常態下約 2.9%）。2330.TW 為早期流程驗證，保留作測試紀錄。

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
| SPY 日收盤價（close、adjclose、配息） | Yahoo Finance chart API | 不重新散布；repo 只附取得程式 |
| S&P 500 指數（SP500） | FRED（St. Louis Fed） | 公開，引用標示來源 |
| 台股官方收盤價（僅 2330 測試用） | 臺灣證券交易所 STOCK_DAY | 政府開放資料，標示來源 |
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
| 1 抓資料＋分析 | `python python/run_all.py` | `data/raw/`、`data/processed/`、`results/tables/`、`results/figures/` | 數十秒（台股代號另加 TWSE，每次請求間隔 3 秒） |
| 1' 離線重跑 | `python python/run_all.py --offline` | 同上，用既有 raw | 數秒 |
| 2 R 獨立檢核 | `Rscript r/verify.R SPY` | `results/tables/r_check_SPY.csv` | 數秒 |
| 3 單元測試 | `python -m unittest discover -s python/tests -v` | 19 項 | 數秒 |
| 4 skill | `python skills/return-distribution-check/make_test_inputs.py` 後依 [SKILL.md](skills/return-distribution-check/SKILL.md) 執行 | `results/skill/` | 數秒 |
| 5 活頁簿對帳（選用） | `powershell -STA -File python/run_workbook_check.ps1 -Book <活頁簿副本.xlsm> -Ticker SPY -Period 2000 -Out out.json` | JSON | ~30 秒 |

換標的：改 `config.json` 的 `tickers` 或加 `--tickers <代號>`（台股上市 `.TW` 會自動做 TWSE 交叉驗證；`index_crosscheck` 指定對照指數）。

## 最小示例與預期輸出

`python python/run_all.py` 對 SPY 印出（2026-11-24 下載；資料每天變，數字會小幅移動）：

```
SPY: n=1400 sd=1.2836% skew=-0.52 exkurt=11.89 JB p=0
  k=3: normal 0.0027  t 0.0162  hist 0.0157  observed 0.0100 [0.0046,0.0216]  x3.70
  window 2000: sd=1.2240% exkurt=13.29 JB p=0 SW p=4.5e-37 beyond k: 1:394/634.6 2:90/91.0 3:30/5.4
```

驗收：`r/verify.R` 必須印出 `44 / 44 checks passed`（結束碼 0）；單元測試 `OK`。
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
| [docs/debug_log.md](docs/debug_log.md) | 實際發生的錯誤與修正 D-01..D-07 |
| [docs/decisions.md](docs/decisions.md) | 決策紀錄與待追蹤 |
| [skills/return-distribution-check/](skills/return-distribution-check/SKILL.md) | 可重用 AI skill 與兩次使用案例 |

## 已知問題

- 只有 SPY 一檔；結論不可外推到個股或其他市場。
- SPY 與 S&P 500 指數 2026-06-26 一筆 −0.68 pp 差距尚未解釋（debug_log D-06）。
- R 尚未建立 `renv.lock`（本機未安裝 renv）；目前以 `r/sessionInfo.txt` 記錄版本。
- （2330 測試）TWSE 交叉驗證只涵蓋最近 24 個月，更早期間的 Yahoo 非交易日陳舊列無法檢出（debug_log D-04）。
- 尚未由非作者依本 README 獨立重跑（排在 12/17 前）。

## 授權

程式碼：待組員決定（建議 MIT）。文件與圖表：待定。第三方資料依各提供者條款，不隨 repo 散布。
