# 新聞年輪｜GitHub 新聞資料端

這一端負責：

1. 每日抓取 RSS 新聞
2. 依來源分類，必要時再交給 AI 分類
3. 驗證 JSON
4. 將每日資料存到 `data/YYYY-MM-DD.json`
5. 通知 Serv00 匯入 SQLite
6. 手動放入歷史 JSON 時，自動偵測 `data/*.json` 並同步到 Serv00

## 兩條 GitHub Actions

### Daily News Sync
- 每天台灣時間約 02:00 執行。
- `workflow_dispatch` 可以指定日期補抓。
- 會執行：爬蟲 → 分類 → 驗證 → commit → 通知 Serv00。

### Sync JSON to Serv00
- 只監看 `data/*.json`。
- 你手動新增或修改 `data/2026-09-10.json` 並 push 後，它只會通知 Serv00。
- **不會重新執行爬蟲與 AI。**
- 一次 push 多個日期也會逐一同步。

> Daily News Sync 自己產生的 JSON 仍保留直接通知 Serv00 的機制，避免 GitHub Actions 使用 `GITHUB_TOKEN` push 時不觸發另一條 workflow 造成漏同步。

## 歷史新聞標準流程

1. 產生 `2026-09-10.json`
2. 放到 `data/2026-09-10.json`
3. `git add data/2026-09-10.json`
4. `git commit -m "data: 新聞資料 2026-09-10"`
5. `git push`
6. GitHub Actions 自動通知 Serv00
7. Serv00 從 GitHub Raw 讀取 JSON
8. 已存在的新聞跳過，不覆蓋 Admin 修改

## JSON 去重規則

Serv00 依序使用：

- 有網址：先比對 URL
- 沒找到：比對 `news_date + title`

因此重複上傳同一份 JSON 不會產生重複新聞。

## AI 分類成本優化

RSS 已經提供有效分類時，預設直接保留，不再浪費 AI 呼叫。
只有「未分類」或沒有可靠來源分類的新聞才需要 AI。

如果真的需要全部重新分類，可以把 `classify.py` 改為使用：

```text
--reclassify-existing
```

## GitHub Secrets

請確認：

- `NVIDIA_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `AGNES_API_KEY`
- `SERV00_UPDATE_URL`
- `SERV00_UPDATE_TOKEN`
- `CACHE_TOKEN`

其中 `SERV00_UPDATE_TOKEN` 必須和 Serv00 `config.php` 的 `UPDATE_TOKEN` 完全相同。


### GitHub → Serv00 同步
`daily-news.yml` 同時處理每日新聞流程、手動指定日期，以及 `data/*.json` 的直接變更同步。直接新增歷史 JSON 時只通知 Serv00，不會重新執行爬蟲或 AI 分類。
