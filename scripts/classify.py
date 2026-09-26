#!/usr/bin/env python3
"""
新聞年輪 - AI 分類器
讀取 ai_providers.json 設定，依優先序嘗試分類
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
AI_CONFIG = CONFIG_DIR / "ai_providers.json"


def load_config() -> dict:
    with open(AI_CONFIG, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_providers(config: dict) -> list:
    providers = [p for p in config.get('providers', []) if p.get('enabled', True)]
    return sorted(providers, key=lambda x: x.get('priority', 999))


def build_prompts(config: dict) -> tuple:
    cats = "、".join(config.get('categories', []))
    sys_prompt = config.get('system_prompt', '').format(categories=cats)
    usr_template = config.get('user_prompt_template', '新聞標題：{title}\n\n請分類：')
    return sys_prompt, usr_template


def call_openai_compat(provider: dict, sys_prompt: str, usr_prompt: str) -> Optional[str]:
    try:
        import openai
        key = os.getenv(provider['api_key_env'])
        if not key:
            return None
        client = openai.OpenAI(
            api_key=key,
            base_url=provider.get('base_url'),
            timeout=provider.get('timeout', 30)
        )
        resp = client.chat.completions.create(
            model=provider['model'],
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": usr_prompt}],
            temperature=provider.get('temperature', 0.1),
            max_tokens=provider.get('max_tokens', 10),
            timeout=provider.get('timeout', 30)
        )
        cat = resp.choices[0].message.content.strip()
        return cat
    except Exception as e:
        print(f"    ⚠️ {provider['name']}: {type(e).__name__}: {e}")
        return None


def call_google(provider: dict, sys_prompt: str, usr_prompt: str) -> Optional[str]:
    try:
        import google.generativeai as genai
        key = os.getenv(provider['api_key_env'])
        if not key:
            return None
        genai.configure(api_key=key)
        model = genai.GenerativeModel(provider['model'])
        resp = model.generate_content(
            f"{sys_prompt}\n\n{usr_prompt}",
            generation_config=genai.types.GenerationConfig(
                temperature=provider.get('temperature', 0.1),
                max_output_tokens=provider.get('max_tokens', 10)
            )
        )
        return resp.text.strip()
    except Exception as e:
        print(f"    ⚠️ {provider['name']}: {type(e).__name__}: {e}")
        return None


def classify(provider: dict, sys_prompt: str, usr_prompt: str, valid_cats: list) -> Optional[str]:
    if provider['id'] == 'google':
        cat = call_google(provider, sys_prompt, usr_prompt)
    else:
        cat = call_openai_compat(provider, sys_prompt, usr_prompt)
    return cat if cat in valid_cats else None



def fallback_category(item: dict, valid_cats: list) -> str:
    """AI 無法使用時的保底分類：優先使用 RSS 原始分類，再用標題關鍵字。"""
    original = str(item.get('original_category', '')).strip()
    if original in valid_cats:
        return original

    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    rules = [
        ("政治", ["總統", "立法院", "行政院", "政黨", "選舉", "市長", "縣長", "議員", "國會", "政府", "內閣", "法案"]),
        ("體育", ["棒球", "籃球", "足球", "網球", "亞運", "奧運", "球隊", "球員", "冠軍"]),
        ("財經", ["股市", "股票", "台股", "金價", "央行", "利率", "銀行", "通膨", "經濟", "營收", "股價"]),
        ("科技", ["ai", "人工智慧", "科技", "晶片", "半導體", "手機", "iphone", "google", "openai", "tesla"]),
        ("健康", ["醫院", "醫師", "疾病", "健康", "癌症", "流感", "手術", "疫苗"]),
        ("社會", ["警方", "警察", "火災", "車禍", "死亡", "傷者", "法院", "犯罪", "遭逮"]),
        ("娛樂", ["演員", "歌手", "電影", "電視劇", "金鐘", "明星", "藝人", "演唱會"]),
        ("教育", ["學校", "學生", "老師", "教育", "大學", "高中", "國中"]),
        ("環境", ["環境", "氣候", "碳排", "污染", "生態", "能源", "地震", "海嘯"]),
        ("生活", ["天氣", "颱風", "美食", "旅遊", "交通", "房價", "消費"]),
    ]
    for category, keywords in rules:
        if any(k in text for k in keywords):
            return category
    return "國際" if item.get('region') != 'taiwan' else "生活"

def main():
    parser = argparse.ArgumentParser(description='AI 分類')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--delay', type=float, default=0.5)
    parser.add_argument('--reclassify-existing', action='store_true', help='即使 RSS 已有有效分類，也重新交給 AI 分類')
    parser.add_argument('--config', default=str(AI_CONFIG))
    args = parser.parse_args()

    config = load_config()
    providers = get_providers(config)
    valid_cats = config.get('categories', [])
    sys_prompt, usr_template = build_prompts(config)

    print("🤖 AI 分類鏈:")
    for p in providers:
        status = "✅" if os.getenv(p['api_key_env']) else "❌ 無Key"
        print(f"  {p['priority']}. {p['name']} ({p['model']}) - {status}")

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get('items', [])
    if not items:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return

    stats = {"總計": 0, "未分類": 0}
    for p in providers:
        stats[p['name']] = 0

    for item in items:
        title = item.get('title', '')
        if not title:
            item['category'] = fallback_category(item, valid_cats)
            stats.setdefault(item['category'], 0)
            stats[item['category']] += 1
            stats["總計"] += 1
            continue

        usr_prompt = config['user_prompt_template'].format(title=title)
        classified = False

        # RSS 已提供可信分類時，預設不浪費 AI 額度重新分類；只有未分類或明確指定 --reclassify-existing 才呼叫 AI。
        existing_category = str(item.get('original_category', '')).strip()
        if not args.reclassify_existing and existing_category in valid_cats:
            item['category'] = existing_category
            stats.setdefault('RSS保留', 0)
            stats['RSS保留'] += 1
            classified = True

        for provider in providers:
            if classified:
                break

            if not os.getenv(provider['api_key_env']):
                continue
            cat = classify(provider, config['system_prompt'].format(categories="、".join(config['categories'])), usr_prompt, valid_cats)
            if cat:
                item['category'] = cat
                stats[provider['name']] += 1
                classified = True
                break
            print(f"    ↳ {provider['name']} 失敗，嘗試下一個...")

        if not classified:
            item['category'] = fallback_category(item, valid_cats)
            stats.setdefault(item['category'], 0)
            stats[item['category']] += 1

        stats["總計"] += 1
        if args.delay > 0:
            time.sleep(args.delay)

    data['classified_at'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    data['classification_stats'] = stats
    data['classification_providers'] = [p['id'] for p in providers]

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分類完成！")
    for k, v in stats.items():
        if k != "總計":
            print(f"   {k}: {v}")


if __name__ == '__main__':
    main()