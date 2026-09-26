#!/usr/bin/env python3
"""
新聞年輪 - 每日自動化流程主程式
整合：爬蟲 → AI分類 → 驗證 → 保存 JSON
"""

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
SCRIPTS_DIR = ROOT_DIR / "scripts"
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TAIWAN_TZ = timezone(timedelta(hours=8))


def run_script(script_name: str, args: list, env: dict = None) -> bool:
    """執行子腳本"""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"❌ 找不到腳本: {script_path}")
        return False
    
    cmd = [sys.executable, str(script_path)] + args
    print(f"\n🚀 執行: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, env={**os.environ, **(env or {})}, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} 執行失敗 (exit code: {e.returncode})")
        return False


def get_yesterday_date() -> str:
    """取得台灣時間的昨天日期"""
    now = datetime.now(TAIWAN_TZ)
    yesterday = now - timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')


def main():
    parser = argparse.ArgumentParser(description='新聞年輪 - 每日自動化流程')
    parser.add_argument('--date', help='目標日期 (YYYY-MM-DD)，預設為昨天')
    parser.add_argument('--skip-crawl', action='store_true', help='跳過爬蟲')
    parser.add_argument('--skip-classify', action='store_true', help='跳過分類')
    args = parser.parse_args()

    target_date = args.date or get_yesterday_date()
    json_file = DATA_DIR / f"{target_date}.json"

    print(f"📅 目標日期: {target_date}")
    print(f"📂 輸出檔案: {json_file}")

    # 1. 爬蟲
    if not args.skip_crawl:
        print("\n" + "="*50)
        print("📥 步驟 1/4: 爬蟲抓取新聞")
        print("="*50)
        if not run_script("crawl.py", ["--date", target_date, "--output", str(json_file)]):
            sys.exit(1)
    else:
        print("\n⏭️ 跳過爬蟲")

    # 2. AI 分類
    if not args.skip_classify:
        print("\n" + "="*50)
        print("🤖 步驟 2/4: AI 分類")
        print("="*50)
        if not run_script("classify.py", ["--input", str(json_file), "--output", str(json_file)]):
            sys.exit(1)
    else:
        print("\n⏭️ 跳過分類")

    # 3. 驗證
    print("\n" + "="*50)
    print("🔍 步驟 3/4: 格式驗證")
    print("="*50)
    if not run_script("validate.py", ["--file", str(json_file)]):
        sys.exit(1)

    # 4. 保存 JSON，之後由 GitHub Actions 提交到 Repository。
    # Serv00 不直接接收 JSON；Workflow 在 push 完成後只發送「更新通知」，
    # Serv00 再依日期從 GitHub raw URL 下載 JSON 並寫入 SQLite。
    print("\n" + "="*50)
    print("📦 步驟 4/4: JSON 已準備完成，等待 GitHub 提交")
    print("="*50)
    print(f"✅ 資料檔: {json_file}")
    print("📡 Serv00 將在 GitHub push 完成後收到更新通知")

    print("\n" + "="*50)
    print("✅ 所有流程完成！")
    print("="*50)


if __name__ == '__main__':
    main()