#!/usr/bin/env python3
"""
舊版 GitHub → Serv00 JSON POST 同步程式。
目前架構不再使用：JSON 會先提交到 GitHub data/，再由 Serv00 主動抓取。
保留此檔案是為了避免舊的本地指令失效；Daily Workflow 已不再呼叫它。
"""

import sys

if __name__ == '__main__':
    print('ℹ️ sync.py 已停用。現在由 GitHub 保存 data/*.json，再通知 Serv00 從 GitHub 讀取。')
    sys.exit(0)
