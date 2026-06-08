"""
py2app 打包配置 — PDF 编辑器.app
"""
import sys
import os
from setuptools import setup

APP_NAME = "PDF 编辑器"

# 所有需要包含的 Python 模块
INCLUDES = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "fitz",          # PyMuPDF
    "reportlab",
    "reportlab.pdfbase",
    "reportlab.pdfbase.ttfonts",
    "reportlab.pdfgen",
    "reportlab.lib.pagesizes",
    "PIL",           # Pillow
    "PIL.Image",
    "PIL.ImageOps",
    "pypdf",         # 如果用了
    "os", "sys", "json", "pathlib", "datetime",
]

# 需要排除的
EXCLUDES = [
    "tkinter",
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
    "PyQt6.QtBluetooth",
    "PyQt6.QtNetwork",
    "PyQt6.QtMultimedia",
    "PyQt6.QtSvg",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebChannel",
    "PyQt6.QtSql",
    "PyQt6.QtTest",
    "PyQt6.QtXml",
    "PyQt6.QtDBus",
]

# 生成一个简单的 App 图标（使用 PIL 生成 .icns）
ICON_FILE = os.path.join(os.path.dirname(__file__), "icon.icns")
if not os.path.exists(ICON_FILE):
    ICON_FILE = None  # 不加图标也能打包

APP = ["main.py"]
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "includes": INCLUDES,
    "excludes": EXCLUDES,
    "packages": ["PyQt6", "fitz", "reportlab", "PIL"],
    "iconfile": ICON_FILE,
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.pdfeditor.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "CFBundleExecutable": APP_NAME,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        # 支持拖拽 PDF 文件到图标上打开
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "PDF Document",
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Owner",
                "LSItemContentTypes": ["com.adobe.pdf"],
                "NSExportableTypes": ["com.adobe.pdf"],
            }
        ],
    },
}

setup(
    name=APP_NAME,
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
