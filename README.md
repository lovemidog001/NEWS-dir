# 新聞年輪｜GitHub 新聞資料端

這一端負責：

1. 每日抓取 RSS 新聞
2. 依來源分類，必要時再交給 AI 分類
3. 驗證 JSON
4. 將每日資料存到 `data/YYYY-MM-DD.json`
5. 通知 Serv00 匯入 SQLite
6. 手動放入歷史 JSON 時，自動偵測 `data/*.json` 並同步到 Serv00


