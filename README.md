# PDF 编辑器

一个跨平台的 PDF 编辑桌面应用，基于 PyQt6 + PyMuPDF + reportlab。

## 功能

- 打开/查看 PDF 文件
- 原地文字编辑（点击文字直接编辑）
- 添加新文字
- 手写签名
- 插入图片/印章
- 页面管理（删除、旋转、插入空白页）
- 文字搜索替换
- 支持中文排版（PingFang 字体嵌入）

## 下载

从 [Releases](https://github.com/) 下载对应平台的安装包：

| 平台 | 格式 |
|------|------|
| macOS | `PDF编辑器-x.x.x.dmg` |
| Windows | `PDF编辑器-x.x.x.exe` |

## 开发

### 环境要求

- Python 3.9+
- PyQt6, PyMuPDF, reportlab, Pillow

### 运行

```bash
pip install -r requirements.txt
python main.py
```

### 打包

macOS:
```bash
python setup.py py2app
```

Windows:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```
