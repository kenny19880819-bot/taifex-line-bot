# 台指期籌碼快訊 LINE Bot

這個專案會在台灣時間週一至週五 16:00、16:30 檢查永豐期貨網站。若找到當日標題完全為「台指期籌碼快訊」的 PDF，會將每一頁轉成圖片並傳送至指定 LINE 群組；同一日期只傳一次。

## 第一次設定

1. 在 GitHub 建立一個 **Public** Repository。
2. 將本 ZIP 解壓縮後，把裡面的所有內容上傳到 Repository 根目錄。請確認 `.github/workflows/daily-report.yml` 也有上傳。
3. 進入 Repository 的 `Settings` → `Secrets and variables` → `Actions`。
4. 建立以下兩個 Repository secrets：
   - `LINE_CHANNEL_ACCESS_TOKEN`：LINE Developers Console 的 Channel Access Token。
   - `LINE_GROUP_ID`：Webhook 取得的群組 groupId。
5. 進入 Repository 的 `Actions` 頁面，選擇「台指期籌碼快訊」。
6. 點 `Run workflow` 手動測試。

## 必要條件

- LINE Official Account 已啟用 Messaging API。
- LINE Bot 已加入目標群組。
- 已取得該群組的 groupId。
- Repository 必須是 Public，LINE 才能讀取產生的圖片網址。

## 測試結果

- 今天已有報告：LINE 群組會收到文字、原始 PDF 連結及每頁圖片。
- 尚未公布、休市或今天已傳送：流程會正常結束，但不發 LINE。
- 執行失敗：在 GitHub `Actions` → 該次執行 → `send-report` 查看紅色步驟的錯誤訊息。

## 安全提醒

不要把 Channel Access Token 或 groupId 直接寫入任何 `.py`、`.yml` 或 README；只能放在 GitHub Repository secrets。
