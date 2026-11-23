# Vibe Coding 紀錄

以自然語言迭代原型。每一版記錄：需求 → AI 生成版本 → 人工／後續修改 → 測試前後差異。

## V1　自然語言需求 → 第一版管線

- **需求（自然語言）**：「用 Ticker Volatility 的算法分析股票報酬是否常態、±kσ 會低估多少，
  Python 主分析、R 檢核，資料要多來源。」
- **生成**：`fetch.py`（三來源）、`integrate.py`（清理／交叉驗證／貼 VIX／切分）、
  `analyze.py`（動差、JB、Shapiro、Ljung-Box、t 擬合、超越率表、Wilson CI）、`run_all.py`（4 張圖）。
- **刻意對齊活頁簿的設計決定**：簡單報酬（非對數）、SD 用 n−1、用 `close` 而非 `adjclose`
  ——皆由讀 `VT/modVT.bas` 原始碼確認（`DailyRets`、`SdS`、`FetchYahooSeries`）。
- **測試**：線上跑 2330.TW，1 分 42 秒完成（TWSE 24 次請求 × 3 秒占大部分）。

## V2　重構：抓取與解析拆開

- **原因**：要能離線重跑（`--offline`），不必每次重抓。
- **修改**：`fetch.py` 拆成 `parse_*`（純解析）與 `fetch_*`（下載＋寫 raw＋記 manifest）。
- **前後差異**：離線模式結果與線上完全相同；重跑時間由 ~100 秒降到數秒。

## V3　看到結果後擴充：滾動 SD

- **觸發**：V1 結果顯示測試期 SD 2.10% vs 訓練期 1.60%，三種模型全部低估。
- **自然語言需求**：「把尾巴形狀和波動水準分開看。」
- **生成**：`rolling_exceedance()`、`config.json` 加 `rolling_window: 250`、圖 5。
- **前後差異**：3σ 低估倍數 11.7 →（滾動）約 7.1；t 在 1σ 落入實際 CI。
- **標示**：事後新增（D-07），results.md 明確寫出。

## V4　R 獨立檢核

- **生成**：`r/verify.R`，只共用 returns CSV，其餘全部用 R 自己的函式重算。
- **結果**：26/26 通過（t 擬合 df 差 0.7%，因兩邊最佳化器不同，容差 5%）。

## V5　單元測試：3 個失敗 → 修正

- 第一次執行：1 ERROR＋2 FAIL（全是測試本身的錯，見 debug_log D-01..D-03）。
- 修正後 14/14 通過。

## V6　交叉驗證抓到資料錯誤 → 修正清理規則

- 新增 `drop_non_trading()`（debug_log D-04）。
- **前後差異**：訓練期 n 1699 → 1698、SD 1.6024% → 1.6028%；結論不變；R 26/26、測試 14/14 維持通過。

## V7　活頁簿對帳

- **生成**：`workbook_replica.py`（Python 版活頁簿 SD 區塊）＋`run_workbook_check.ps1`（Excel COM 執行活頁簿副本）。
- **人工修改**：COM 寫入數字失敗（D-05），改寫字串。
- **結果**：與活頁簿完全一致（docs/workbook_check.md）。

## V8　skill

- `return-distribution-check`：正常資料 1 次、邊界資料 2 種（重複日期、太短），皆依規格停止（exit 2）。
