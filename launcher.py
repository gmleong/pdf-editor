#!/usr/bin/env python3
"""
PDF 编辑器启动器
用于 start.command 调用，确保使用正确的 Python
"""
import os
import sys
import subprocess

# 强制使用系统 Python
python = "/usr/bin/python3"
script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")

# 设置环境变量，让 Python 能找到正确的 site-packages
env = os.environ.copy()
env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + env.get("PATH", "")

# 启动
subprocess.run([python, script], env=env)
