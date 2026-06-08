"""
PDF 编辑引擎
基于 PyMuPDF (fitz) + reportlab + pypdf
中文排版：使用系统 PingFang 字体
"""

import fitz  # PyMuPDF
import os
from pathlib import Path
from typing import Optional, Tuple, List

# 中文字体路径（macOS 系统的 PingFang）
FONT_PATHS = {
    "pingfang-sc": "/System/Library/Fonts/PingFang.ttc",
    "stheitisc": "/System/Library/Fonts/STHeiti Light.ttc",
    "stheitimed": "/System/Library/Fonts/STHeiti Medium.ttc",
    "songti": "/System/Library/Fonts/Supplemental/Songti.ttc",
}


def get_cjk_font() -> str:
    """获取可用的中文字体路径"""
    for name, path in FONT_PATHS.items():
        if os.path.exists(path):
            return path
    # fallback
    return "/System/Library/Fonts/PingFang.ttc"


class PDFDocument:
    """PDF 文档对象"""

    def __init__(self):
        self.doc: Optional[fitz.Document] = None
        self.filepath: Optional[str] = None
        self.modified = False
        self.cjk_font = get_cjk_font()

    def open(self, filepath: str) -> bool:
        """打开 PDF 文件"""
        try:
            self.doc = fitz.open(filepath)
            self.filepath = filepath
            self.modified = False
            return True
        except Exception as e:
            print(f"打开失败: {e}")
            return False

    def save(self, filepath: Optional[str] = None) -> bool:
        """保存 PDF"""
        if not self.doc:
            return False
        try:
            path = filepath or self.filepath
            if not path:
                return False
            self.doc.save(path, garbage=4, deflate=True)
            self.modified = False
            if filepath:
                self.filepath = filepath
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False

    def close(self):
        """关闭文档"""
        if self.doc:
            self.doc.close()
            self.doc = None
            self.filepath = None

    @property
    def page_count(self) -> int:
        return len(self.doc) if self.doc else 0

    def render_page(self, page_num: int, zoom: float = 1.5) -> Optional[bytes]:
        """渲染页面为 PNG bytes"""
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return None
        page = self.doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")

    def get_page_size(self, page_num: int, zoom: float = 1.5) -> Tuple[int, int]:
        """获取页面渲染尺寸"""
        if not self.doc:
            return (0, 0)
        page = self.doc[page_num]
        rect = page.rect
        return (int(rect.width * zoom), int(rect.height * zoom))

    def search_text(self, page_num: int, keyword: str) -> List[dict]:
        """搜索页面中的文字，返回位置信息"""
        if not self.doc:
            return []
        page = self.doc[page_num]
        instances = page.search_for(keyword)
        results = []
        for inst in instances:
            results.append({
                "x0": inst.x0, "y0": inst.y0,
                "x1": inst.x1, "y1": inst.y1,
                "width": inst.x1 - inst.x0,
                "height": inst.y1 - inst.y0,
                "text": keyword,
            })
        return results

    def get_text_at_point(self, page_num: int, x: float, y: float):
        """获取指定坐标附近的文字内容及包围盒（点击编辑用）"""
        if not self.doc:
            return None
        page = self.doc[page_num]

        # 搜索范围内所有 text span
        blocks = page.get_text("dict")["blocks"]
        best = None
        best_dist = float("inf")

        for b in blocks:
            if b["type"] != 0:  # skip non-text
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    bx0, by0, bx1, by1 = span["bbox"]
                    # 宽容匹配：周围 150px 范围
                    if bx0 - 150 <= x <= bx1 + 150 and \
                       by0 - 150 <= y <= by1 + 150:
                        cx = (bx0 + bx1) / 2
                        cy = (by0 + by1) / 2
                        dist = (x - cx) ** 2 + (y - cy) ** 2
                        text = span["text"].strip()
                        if dist < best_dist and text:
                            best_dist = dist
                            best = {
                                "text": text,
                                "x0": bx0,
                                "y0": by0,
                                "x1": bx1,
                                "y1": by1,
                                "font": span["font"],
                                "size": span["size"],
                            }

        return best  # {"text": ..., "x0": ..., "y0": ..., "x1": ..., "y1": ..., ...}

    def get_text_blocks(self, page_num: int) -> List[dict]:
        """获取页面上所有文本块"""
        if not self.doc:
            return []
        page = self.doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        results = []
        for b in blocks:
            if b["type"] == 0:  # text block
                for line in b["lines"]:
                    for span in line["spans"]:
                        results.append({
                            "x0": span["bbox"][0],
                            "y0": span["bbox"][1],
                            "x1": span["bbox"][2],
                            "y1": span["bbox"][3],
                            "text": span["text"],
                            "font": span["font"],
                            "size": span["size"],
                            "color": span.get("color", 0),
                        })
        return results

    def replace_text(self, page_num: int, old_text: str, new_text: str) -> bool:
        """替换文字（保持原字体和位置）"""
        if not self.doc:
            return False
        page = self.doc[page_num]

        # 1. 找到文本位置
        instances = page.search_for(old_text)
        if not instances:
            return False

        # 2. 获取原文本属性
        blocks = page.get_text("dict")["blocks"]
        orig_font = "helv"
        orig_size = 12
        orig_color = (0, 0, 0)

        for b in blocks:
            if b["type"] == 0:
                for line in b["lines"]:
                    for span in line["spans"]:
                        if old_text in span["text"]:
                            orig_font = span["font"]
                            orig_size = span["size"]
                            c = span.get("color", 0)
                            # convert int color to rgb
                            if isinstance(c, int):
                                orig_color = (
                                    (c >> 16 & 0xFF) / 255,
                                    (c >> 8 & 0xFF) / 255,
                                    (c & 0xFF) / 255,
                                )
                            else:
                                orig_color = c or (0, 0, 0)

        # 3. 用白色矩形遮盖 + 写新文字
        annot_opts = {
            "fill_opacity": 1,
        }
        for inst in instances:
            # 白色遮盖矩形
            rect = fitz.Rect(inst.x0, inst.y0, inst.x1, inst.y1)
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)

            # 写新文字（与原位置对齐）
            text_point = fitz.Point(inst.x0, inst.y0 + orig_size * 0.8)
            page.insert_text(
                text_point,
                new_text,
                fontname=orig_font if orig_font else "helv",
                fontsize=orig_size,
                color=orig_color,
            )

        self.modified = True
        return True

    def add_text(self, page_num: int, text: str, x: float, y: float,
                 fontsize: float = 14, color: Tuple = (0, 0, 0)) -> bool:
        """在指定位置添加文字"""
        if not self.doc:
            return False
        page = self.doc[page_num]

        # 使用系统中文字体
        try:
            # 尝试嵌入中文字体
            font_path = self.cjk_font
            page.insert_text(
                fitz.Point(x, y),
                text,
                fontname="china-s",
                fontfile=font_path,
                fontsize=fontsize,
                color=color,
            )
        except:
            # fallback
            page.insert_text(
                fitz.Point(x, y),
                text,
                fontsize=fontsize,
                color=color,
            )

        self.modified = True
        return True

    def insert_image(self, page_num: int, image_path: str,
                     x: float, y: float, width: float, height: float) -> bool:
        """插入图片到指定位置"""
        if not self.doc:
            return False
        page = self.doc[page_num]

        rect = fitz.Rect(x, y, x + width, y + height)
        page.insert_image(rect, filename=image_path)

        self.modified = True
        return True

    def delete_page(self, page_num: int) -> bool:
        """删除页面"""
        if not self.doc or page_num < 0 or page_num >= len(self.doc):
            return False
        self.doc.delete_page(page_num)
        self.modified = True
        return True

    def rotate_page(self, page_num: int, rotation: int = 90) -> bool:
        """旋转页面（90/180/270）"""
        if not self.doc:
            return False
        page = self.doc[page_num]
        current = page.rotation or 0
        page.set_rotation((current + rotation) % 360)
        self.modified = True
        return True

    def move_page(self, from_idx: int, to_idx: int) -> bool:
        """移动页面顺序"""
        if not self.doc:
            return False
        self.doc.move_page(from_idx, to_idx)
        self.modified = True
        return True

    def insert_blank_page(self, after_idx: int, width: float = 595,
                          height: float = 842) -> bool:
        """插入空白页（A4 默认）"""
        if not self.doc:
            return False
        page = self.doc.new_page(width=width, height=height)
        # move to after_idx
        if after_idx < len(self.doc) - 1:
            self.doc.move_page(len(self.doc) - 1, after_idx + 1)
        self.modified = True
        return True


# 测试
if __name__ == "__main__":
    doc = PDFDocument()
    r = doc.open("/Users/gm/order-system/db/schema.sql" if False else None)
    print(f"OK: {doc.cjk_font}")
    print(f"Font exists: {os.path.exists(doc.cjk_font)}")
