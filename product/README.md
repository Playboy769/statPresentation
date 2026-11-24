# Ticker Volatility 活頁簿（產品原始碼）

本專題的主軸之一。輸入任一 Yahoo 代號，即可看到該檔股票的波動輪廓。

| 檔案 | 內容 |
|---|---|
| `modVT.bas` | 主程式（VBA 模組）：抓 Yahoo 價格、計算報酬與統計量、畫表與圖 |
| `SheetTickerVolatility_Code.txt` | 工作表事件碼：改 TICKER／PERIOD／FREQ 後自動重算 |
| `build.ps1` | 從空白活頁簿建出 `Ticker Volatility.xlsm` |

## 建置

需 Windows＋Excel，且在信任中心勾選「信任存取 VBA 專案物件模型」：

```
powershell -STA -File product\build.ps1 -OutPath "C:\path\Ticker Volatility.xlsm"
```

## 使用

開啟活頁簿，B2 輸入代號（如 SPY、AAPL、2330），B3 輸入 PERIOD（顯示的 K 棒數），E3 選頻率 D／W／M。需連網。

## 輸出區塊

| 區塊 | 內容 |
|---|---|
| RETURN HISTORY | 期間、SD、超過 2 SD 的天數 |
| 報酬分布圖 | 直方圖疊常態曲線，標出最新一根的位置 |
| 逐日報酬圖 | ±1、±2 SD 虛線，超過 2 SD 標橘色 |
| STANDARD DEVIATION / SD | ±1／2／3 SD 的價格區間與實際落在區間內的比例（DAYS INSIDE） |
| PROXY CHECK | 與大盤的相關、Beta |
| UP DAYS VS DOWN DAYS／STRETCH | 漲跌天數、近期累積漲跌 |
| RETURN BANDS／BIGGEST DAYS | 報酬分組次數、最大漲跌日 |
| STREAK LENGTH | 連漲／連跌的次數與延續機率 |

本專題的分析與活頁簿使用同一份 Yahoo 含息調整價格，並以 Excel 實際執行本活頁簿對帳（見 `docs/workbook_check.md`）。
