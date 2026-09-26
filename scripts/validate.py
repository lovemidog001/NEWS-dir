#!/usr/bin/env python3
"""
新聞年輪 - JSON 格式驗證
"""

import argparse
import json
import sys
from pathlib import Path
from jsonschema import validate, ValidationError

SCHEMA = {
    "type": "object",
    "required": ["date", "timezone", "items"],
    "properties": {
        "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
        "timezone": {"type": "string", "const": "Asia/Taipei"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "date", "category", "original_category", "source"],
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                    "category": {"type": "string"},
                    "original_category": {"type": "string"},
                    "source": {"type": "string"}
                }
            }
        }
    }
}

VALID_CATEGORIES = [
    "政治", "國際", "財經", "科技", "社會",
    "生活", "健康", "體育", "娛樂", "教育", "環境", "未分類"
]


def validate_file(file_path: Path, strict: bool) -> bool:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 讀取失敗: {e}")
        return False

    errors, warnings = [], []

    # Schema 驗證
    try:
        validate(instance=data, schema=SCHEMA)
        print("✅ Schema 驗證通過")
    except ValidationError as e:
        errors.append(f"Schema 錯誤: {e.message}")

    # 業務邏輯
    if 'items' in data:
        cats, sources, dates, dupes = {}, {}, set(), set()
        seen = set()
        for i, item in enumerate(data['items']):
            cat = item.get('category', '')
            if cat not in VALID_CATEGORIES:
                warnings.append(f"第{i+1}筆: 未知分類 '{cat}'")
            cats[cat] = cats.get(cat, 0) + 1
            sources[item.get('source','')] = sources.get(item.get('source',''),0) + 1
            dates.add(item.get('date',''))
            title = item.get('title','')
            if title in seen:
                dupes.add(title)
            seen.add(title)

        if dupes:
            warnings.append(f"重複標題: {len(dupes)} 筆")
        if len(dates) > 1:
            warnings.append(f"多日期: {dates}")
        elif dates and data.get('date') not in dates:
            warnings.append("項目日期與根層日期不符")

        print(f"📊 統計: {len(data['items'])} 筆")
        for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {cnt}")

    if errors:
        for e in errors: print(f"❌ {e}")
    if warnings:
        for w in warnings: print(f"⚠️ {w}")

    if errors or (strict and warnings):
        return False
    print("✅ 驗證通過")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True)
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    ok = validate_file(Path(args.file), args.strict)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()