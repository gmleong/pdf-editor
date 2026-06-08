#!/usr/bin/env python3
"""
📝 PDF 编辑器 — 入口
启动方式：python3 main.py
"""

import sys
import os

# 确保当前目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from editor_ui import launch

if __name__ == "__main__":
    launch()
