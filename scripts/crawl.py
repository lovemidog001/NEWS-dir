#!/usr/bin/env python3
"""
新聞年輪 - RSS 爬蟲
從 sources.json 讀取來源設定，抓取指定日期新聞
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"

TAIWAN_TZ = timezone(timedelta(hours=8))


def load_sources(config_path: Path) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_date(entry) -> str | None:
    for field in ['published_parsed', 'updated_parsed', 'created_parsed']:
        if hasattr(entry, field) and getattr(entry, field):
            dt = datetime(*getattr(entry, field)[:6], tzinfo=timezone.utc)
            return dt.astimezone(TAIWAN_TZ).strftime('%Y-%m-%d')
    return None


def clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text(separator=' ', strip=True)


def fetch_source(source: dict, target_date: str, max_items: int, timeout: int) -> list:
    items = []
    try:
        headers = {'User-Agent': 'NewsRing/1.1 (+https://github.com/lovemidog001/NEWS-dir)', 'Accept': 'application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8'}
        headers.update(source.get('headers', {}))
        
        resp = requests.get(source['url'], headers=headers, timeout=timeout)
        resp.raise_for_status()
        
        feed = feedparser.parse(resp.content)
        if feed.bozo:
            print(f"  ⚠️ {source['name']}: 解析警告 - {feed.bozo_exception}")
        
        cat_map = source.get('category_map', {})
        default_cat = cat_map.get('default', source.get('default_category', '未分類'))
        
        # RSS 常把最新文章放在前面；不要先切 max_items 再過濾日期，否則歷史日期容易被漏掉。
        entries = feed.entries
        for entry in entries:
            pub_date = parse_date(entry)
            if not pub_date or pub_date != target_date:
                continue
            
            title = clean_html(entry.get('title', '')).strip()
            if not title:
                continue
            
            category = default_cat
            if 'tags' in entry:
                for tag in entry.tags:
                    if tag.term.lower() in cat_map:
                        category = cat_map[tag.term.lower()]
                        break
            
            items.append({
                'title': title,
                'date': pub_date,
                'category': category,
                'original_category': category,
                'source': source['name'],
                'region': source.get('region', 'international'),
                'url': entry.get('link', ''),
                'summary': clean_html(entry.get('summary', '') or entry.get('description', ''))[:500]
            })

        # 過濾日期後才限制數量，避免 RSS 最新文章太多導致指定歷史日期被漏掉。
        items = items[:max_items]

    except Exception as e:
        print(f"  ❌ {source['name']}: {e}")
    
    return items


def main():
    parser = argparse.ArgumentParser(description='RSS 爬蟲')
    parser.add_argument('--date', required=True, help='目標日期 YYYY-MM-DD')
    parser.add_argument('--output', required=True, help='輸出 JSON 路徑')
    parser.add_argument('--config', default=str(CONFIG_DIR / 'sources.json'))
    args = parser.parse_args()

    config = load_sources(Path(args.config))
    sources = [s for s in config.get('sources', []) if s.get('enabled', True)]
    settings = config.get('global_settings', {})
    
    max_items = settings.get('max_items_per_source', 50)
    timeout = settings.get('request_timeout', 15)

    all_items = []
    for source in tqdm(sources, desc="抓取來源"):
        if source.get('type') != 'rss':
            continue
        source_limit = source.get('max_items', max_items)
        items = fetch_source(source, args.date, source_limit, timeout)
        print(f"  ✅ {source['name']}: {len(items)} 筆")
        all_items.extend(items)

    # 去重，並以台灣新聞為主。
    seen = set()
    unique = []
    for item in all_items:
        key = (item['date'], item['title'])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    taiwan_items = [i for i in unique if i.get('region') == 'taiwan']
    international_items = [i for i in unique if i.get('region') != 'taiwan']
    taiwan_ratio = float(settings.get('taiwan_ratio', 0.8))
    if taiwan_items:
        # 台灣新聞盡量佔至少 80%；國際新聞只作補充。
        max_total = len(taiwan_items) + min(len(international_items), max(3, int(len(taiwan_items) * (1 - taiwan_ratio) / taiwan_ratio)))
        taiwan_items.sort(key=lambda x: x.get('title', ''))
        international_items.sort(key=lambda x: x.get('title', ''))
        unique = taiwan_items + international_items[:max(0, max_total - len(taiwan_items))]
    else:
        international_items.sort(key=lambda x: x.get('title', ''))
        unique = international_items

    output_data = {
        'date': args.date,
        'timezone': 'Asia/Taipei',
        'collected_at': datetime.now(TAIWAN_TZ).isoformat(),
        'sources_count': len(sources),
        'items': unique
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完成！共 {len(unique)} 筆新聞")
    from collections import Counter
    for cat, cnt in Counter(i['category'] for i in unique).most_common():
        print(f"  {cat}: {cnt}")


if __name__ == '__main__':
    main()