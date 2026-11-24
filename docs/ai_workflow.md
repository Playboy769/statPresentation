# AI agent workflow 紀錄

工具：Claude Code（桌面版 Code 分頁），模型 Claude Opus 5.5（`claude-opus-5-5`），2026-11-23。
付費：使用者個人訂閱方案；未呼叫額外付費 API。資料 API（Yahoo／TWSE／FRED）皆免費公開端點。

一條完整的 **規劃 → 審查 → 實作 → 測試 → 修正** 流程，每一步標出人工決策點（🧑）與產出證據。

```
Define ──► Plan ──► Review ──► Code ──► Test ──► Fix ──► Reflect
  🧑         🤖       🧑         🤖       🤖+🧑     🤖       🧑
```

## 1. Define：釐清問題（人工決策主導）

| 時間 | 事件 | 證據 |
|---|---|---|
| 開始 | 使用者提供：Ticker Volatility.xlsm、課程指引截圖，要求「資料分析」與「工具使用過程紀錄」 | 對話 |
| — | Agent 依專案規則先問 10 題澄清題（分三輪 4＋4＋2） | decisions.md D-01..D-06 |
| 🧑 | 研究問題：使用者先提「判斷波動是否極端、是否遵循常態」，並授權 agent 給更好界定 | D-01 |
| 🧑 | 使用者補上完整課程指引 PDF（27 頁），agent 讀完後發現「至少 3 份資料、2 個獨立來源」門檻 | D-03 |
| 🧑 | 採用 agent 提的收斂版問題（加入基準＝常態、對照＝t／歷史、70/30 樣本外驗證） | D-01 |

## 2. Plan：拆解任務

Agent 提出分工（使用者核定）：

| 任務 | 語言 | 輸入 → 輸出 |
|---|---|---|
| 抓資料（3 來源） | Python `fetch.py` | API → `data/raw/*`、`manifest.json` |
| 清理、交叉驗證、整合 | Python `integrate.py` | raw → `data/processed/returns_*.csv` |
| 統計分析與圖 | Python `analyze.py`、`run_all.py` | returns → `results/tables/*.json`、`results/figures/*.png` |
| 獨立重算檢核 | R `verify.R` | 同一份 returns CSV → `results/tables/r_check_*.csv` |
| 與活頁簿對帳 | Python `workbook_replica.py` + PowerShell COM | 活頁簿副本 → `docs/evidence/*.json` |
| 可重用檢查 | skill `return-distribution-check` | 任一 CSV → 報告 / 停止 |

## 3. Review：人工審核點

| 🧑 決策 | 內容 |
|---|---|
| 標的 | 使用者回「先不要分析」→ 澄清後決定**先建架構、用 1 檔跑通**，標的另定（D-05） |
| 第二來源 | 使用者選 TWSE 官方＋FRED（D-03） |
| 交付範圍 | 只做分析＋過程紀錄；網站、PPT、影片之後再做（D-04） |
| 位置 | 新獨立資料夾＋新 repo，名稱 statPresentation（D-06） |

## 4. Code：小步實作

依序：fetch → integrate → analyze → run_all → 跑通 → R 檢核 → 單元測試 → skill → 文件。
每一步跑過才進下一步；詳細版本變化見 `vibe_coding_log.md`。

## 5. Test：用已知答案、邊界與反例測試

- Python 單元測試 19 項（手算例、教科書 Wilson 區間、模擬常態不應被拒絕、重複鍵必須停止、VIX 不可偷看當日）。
- R 獨立重算 26 項，全部通過。
- 活頁簿對帳：SD、超過 2SD 天數、±1/2/3 SD 內比例完全一致。
- 測試結果紀錄：`test_plan.md`。

## 6. Fix：實際發生的錯誤與修正

見 `debug_log.md`（D-01..D-05，全部是真實發生、有輸出可查的錯誤，沒有杜撰）。
其中 D-04 是**整合資料後才發現的資料錯誤**：Yahoo 在非交易日 2026-10-23 多了一根陳舊 K 棒。

## 7. Reflect：分析過程中改變的計畫

- 第一次跑完發現測試期 SD 比訓練期大三成 → 所有固定參數模型都低估。
  Agent 提議加「滾動 250 日 SD」版本，把「尾巴形狀」與「波動水準」分開評估。
  這是**看到結果後新增的分析**，在 results.md 中明確標示，不當成事前假設。
- 剩餘限制與下一步：見 results.md「限制」。

## 人類必須能回答的問題（指引 07）

- 我負責哪一步？→ 由組員分工後填入 `decisions.md`。
- AI 提供了什麼、人改了什麼？→ `ai_disclosure.md` 每筆的「人類判斷」欄。
- 哪個測試證明結果合理？→ R 44/44、活頁簿對帳、模擬常態測試。
