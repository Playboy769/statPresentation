param([string]$Book, [string]$Ticker, [int]$Period, [string]$Out)
$ErrorActionPreference = 'Stop'
$xl = New-Object -ComObject Excel.Application
try {
  $xl.Visible = $false
  $xl.DisplayAlerts = $false
  $xl.AutomationSecurity = 1
  $wb = $xl.Workbooks.Open($Book)
  $ws = $wb.Sheets.Item("Ticker Volatility")
  $xl.EnableEvents = $false
  $ws.Range("B2").Value2 = $Ticker
  $ws.Range("B3").Value2 = [string]$Period
  $ws.Range("E3").Value2 = "D"
  $xl.EnableEvents = $true
  $xl.Run("RunVT")
  $o = [ordered]@{
    status = [string]$ws.Range("A4").Text
    c8 = [string]$ws.Range("C8").Text
    m10 = [string]$ws.Range("M10").Text; m11 = [string]$ws.Range("M11").Text; m12 = [string]$ws.Range("M12").Text
    p10 = $ws.Range("P10").Value2; p11 = $ws.Range("P11").Value2; p12 = $ws.Range("P12").Value2
    last_price = $ws.Range("I5").Value2
  }
  $o | ConvertTo-Json | Set-Content -Path $Out -Encoding UTF8
  $wb.Close($false)
} finally {
  $xl.Quit()
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
}
