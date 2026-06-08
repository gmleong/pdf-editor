"""
PDF 编辑器主窗口
PyQt6
"""

import os
import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QTextEdit,
                             QSplitter, QFileDialog, QMessageBox, QScrollArea,
                             QListWidget, QListWidgetItem, QSpinBox,
                             QColorDialog, QInputDialog, QToolBar, QStatusBar,
                             QApplication, QFrame, QDialog, QMenuBar, QMenu)
from PyQt6.QtCore import Qt, QByteArray, QBuffer
from PyQt6.QtGui import (QAction, QPixmap, QPainter, QColor, QPen, QFont,
                         QImage, QIcon, QKeySequence)
from pathlib import Path

from pdf_engine import PDFDocument
from signature_pad import SignaturePad


class PDFEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pdf = PDFDocument()
        self.current_page = 0
        self.zoom = 1.2
        self.last_save_path = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PDF 编辑器")
        self.setMinimumSize(1200, 800)

        # ====== 菜单栏 ======
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")

        open_action = QAction("打开(&O)...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("保存(&S)", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("另存为(&A)...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ====== 中央部件 ======
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ====== 右侧：预览区 ======
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        # 顶部工具栏（使用 QAction 而不是 QPushButton，避开 ClickableLabel 事件拦截）
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        toolbar.setStyleSheet("""
            QToolBar {
                background: #f0f0f0;
                border-bottom: 1px solid #ddd;
                padding: 4px;
            }
            QToolBar QToolButton {
                padding: 6px 12px;
                border: 1px solid transparent;
                border-radius: 4px;
                font-size: 13px;
            }
            QToolBar QToolButton:hover {
                background: #e0e0e0;
                border-color: #ccc;
            }
            QToolBar QToolButton:pressed {
                background: #d0d0d0;
            }
        """)

        # 使用 QPushButton 替代 QAction（避免 QAction.triggered 在某些 Qt 版本中不生效的问题）
        open_btn = QPushButton("📂 打开")
        open_btn.clicked.connect(lambda: self.open_file())
        toolbar.addWidget(open_btn)

        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self.save_file)
        toolbar.addWidget(save_btn)

        save_as_btn = QPushButton("另存为")
        save_as_btn.clicked.connect(self.save_as_file)
        toolbar.addWidget(save_as_btn)

        toolbar.addSeparator()

        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(lambda: self.set_zoom(self.zoom * 1.2))
        toolbar.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(lambda: self.set_zoom(self.zoom / 1.2))
        toolbar.addWidget(zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("padding: 4px 8px;")
        toolbar.addWidget(self.zoom_label)

        toolbar.addSeparator()

        prev_btn = QPushButton("◀ 上一页")
        prev_btn.clicked.connect(self.prev_page)
        toolbar.addWidget(prev_btn)

        self.page_label = QLabel("第 0/0 页")
        self.page_label.setStyleSheet("padding: 4px 8px;")
        toolbar.addWidget(self.page_label)

        next_btn = QPushButton("下一页 ▶")
        next_btn.clicked.connect(self.next_page)
        toolbar.addWidget(next_btn)

        main_layout.addWidget(self._build_left_panel())
        main_layout.addWidget(right_panel)

        # 工具栏
        right_layout.addWidget(toolbar)

        # 页面预览 + 编辑区（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #e0e0e0; }")
        self.preview_label = ClickableLabel()
        self.preview_label.set_editor(self)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background: white;")
        self.preview_label.setMinimumSize(600, 400)
        scroll.setWidget(self.preview_label)
        right_layout.addWidget(scroll, 1)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        # 刷新
        self.update_preview()
        self.update_toolbar()

    def _build_left_panel(self):
        """左侧面板：工具 + 编辑"""
        left = QWidget()
        left.setFixedWidth(320)
        left.setStyleSheet("background: #f5f5f5; border-right: 1px solid #ddd;")
        layout = QVBoxLayout(left)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ====== 页面列表 ======
        section_title = QLabel("📄 页面管理")
        section_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #333; margin-top: 4px;")
        layout.addWidget(section_title)

        self.page_list = QListWidget()
        self.page_list.setMaximumHeight(120)
        self.page_list.currentRowChanged.connect(self._page_selected)
        layout.addWidget(self.page_list)

        page_btn_row = QHBoxLayout()
        delete_page_btn = QPushButton("删除页面")
        delete_page_btn.clicked.connect(self._delete_current_page)
        page_btn_row.addWidget(delete_page_btn)

        rotate_btn = QPushButton("旋转 90°")
        rotate_btn.clicked.connect(self._rotate_current_page)
        page_btn_row.addWidget(rotate_btn)

        blank_page_btn = QPushButton("+ 空白页")
        blank_page_btn.clicked.connect(self._insert_blank_page)
        page_btn_row.addWidget(blank_page_btn)
        layout.addLayout(page_btn_row)

        # ====== 文字编辑 ======
        layout.addSpacing(8)
        section_title2 = QLabel("✏️ 文字编辑")
        section_title2.setStyleSheet("font-weight: bold; font-size: 13px; color: #333;")
        layout.addWidget(section_title2)

        layout.addWidget(QLabel("搜索文字："))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入要搜索的文字...")
        layout.addWidget(self.search_input)

        search_replace_row = QHBoxLayout()
        search_btn = QPushButton("🔍 搜索")
        search_btn.clicked.connect(self._search_text)
        search_replace_row.addWidget(search_btn)
        replace_all_btn = QPushButton("🔁 全部替换")
        replace_all_btn.clicked.connect(self._replace_all_text)
        search_replace_row.addWidget(replace_all_btn)
        layout.addLayout(search_replace_row)

        layout.addWidget(QLabel("替换为："))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("替换后的文字...")
        layout.addWidget(self.replace_input)

        # ====== 添加文字 ======
        layout.addSpacing(8)
        section_title3 = QLabel("📝 添加文字")
        section_title3.setStyleSheet("font-weight: bold; font-size: 13px; color: #333;")
        layout.addWidget(section_title3)

        layout.addWidget(QLabel("文字内容："))
        self.add_text_input = QTextEdit()
        self.add_text_input.setMaximumHeight(60)
        self.add_text_input.setPlaceholderText("输入要添加的文字...")
        layout.addWidget(self.add_text_input)

        text_props = QHBoxLayout()
        text_props.addWidget(QLabel("字号:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 200)
        self.font_size_spin.setValue(14)
        text_props.addWidget(self.font_size_spin)

        text_color_btn = QPushButton("颜色")
        text_color_btn.clicked.connect(self._choose_text_color)
        text_props.addWidget(text_color_btn)

        layout.addLayout(text_props)

        add_text_btn = QPushButton("📝 添加到当前页")
        add_text_btn.clicked.connect(self._add_text_to_page)
        add_text_btn.setStyleSheet("background: #1a1a2e; color: white; padding: 8px; border-radius: 6px; font-weight: bold;")
        layout.addWidget(add_text_btn)

        # ====== 签名/图片/盖章 ======
        layout.addSpacing(8)
        section_title4 = QLabel("🖌️ 签名 / 图片 / 盖章")
        section_title4.setStyleSheet("font-weight: bold; font-size: 13px; color: #333;")
        layout.addWidget(section_title4)

        sign_btn = QPushButton("✍️ 手写签名")
        sign_btn.clicked.connect(self._add_signature)
        sign_btn.setStyleSheet("background: #2e7d32; color: white; padding: 8px; border-radius: 6px;")
        layout.addWidget(sign_btn)

        img_btn = QPushButton("🖼️ 插入图片")
        img_btn.clicked.connect(self._insert_image)
        img_btn.setStyleSheet("background: #1565c0; color: white; padding: 8px; border-radius: 6px;")
        layout.addWidget(img_btn)

        stamp_btn = QPushButton("🔴 插入印章")
        stamp_btn.clicked.connect(self._insert_stamp)
        stamp_btn.setStyleSheet("background: #e65100; color: white; padding: 8px; border-radius: 6px;")
        layout.addWidget(stamp_btn)

        layout.addStretch()
        return left

    # ====== 文件操作 ======

    def open_file(self, path=None):
        print(f"=== open_file called, path={path}, pdf doc={bool(self.pdf and self.pdf.doc)} ===")
        if path is None:
            print("=== about to call QFileDialog (using QTimer to yield) ===")
            # 使用 QTimer + 普通函数调用避免事件循环嵌套问题
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._do_open_dialog)
            return
        self._do_open_with_path(path)

    def _do_open_dialog(self):
        print("=== _do_open_dialog ===")
        # 创建一个临时的独立窗口作 parent，避免 ClickableLabel 的干扰
        dlg_parent = QWidget()
        dlg_parent.setWindowTitle("选择文件")
        # 让 dialog 显示在屏幕中央
        dlg_parent.setGeometry(self.geometry().center().x() - 200,
                                self.geometry().center().y() - 150, 1, 1)
        dlg_parent.setWindowFlags(Qt.WindowType.Window |
                                   Qt.WindowType.Dialog)
        path, _ = QFileDialog.getOpenFileName(
            dlg_parent, "打开 PDF", "", "PDF 文件 (*.pdf)")
        dlg_parent.deleteLater()
        print(f"=== QFileDialog returned: {path} ===")
        if path:
            self._do_open_with_path(path)

    def _do_open_with_path(self, path):
        print(f"=== _do_open_with_path: {path} ===")
        if not path:
            return
        try:
            if self.pdf.open(path):
                self.current_page = 0
                self.update_page_list()
                self.update_preview()
                self.update_toolbar()
                self.status_bar.showMessage(f"已打开: {os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "错误", "无法打开此 PDF 文件")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开文件失败: {e}")

    def save_file(self):
        if self.pdf.filepath:
            if self.pdf.save():
                self.status_bar.showMessage("✅ 已保存")
            else:
                QMessageBox.warning(self, "错误", "保存失败")
        else:
            self.save_as_file()

    def save_as_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "另存为", "edited.pdf", "PDF 文件 (*.pdf)")
        if not path:
            return
        if self.pdf.save(path):
            self.status_bar.showMessage(f"✅ 已保存到: {os.path.basename(path)}")

    # ====== 导航 ======

    def next_page(self):
        if self.current_page < self.pdf.page_count - 1:
            self.current_page += 1
            self.update_preview()
            self.update_toolbar()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_preview()
            self.update_toolbar()

    def set_zoom(self, new_zoom):
        self.zoom = max(0.3, min(4.0, new_zoom))
        self.update_preview()

    def _page_selected(self, row):
        if row >= 0 and row < self.pdf.page_count:
            self.current_page = row
            self.update_preview()
            self.update_toolbar()

    # ====== 编辑操作 ======

    def _search_text(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            return
        if not self.pdf.doc:
            return
        results = self.pdf.search_text(self.current_page, keyword)
        if results:
            self.status_bar.showMessage(f"找到 {len(results)} 个 \"{keyword}\"")
        else:
            self.status_bar.showMessage(f"未找到 \"{keyword}\"")

    def _replace_all_text(self):
        old = self.search_input.text().strip()
        new = self.replace_input.text().strip()
        if not old:
            return

        ok = self.pdf.replace_text(self.current_page, old, new)
        if ok:
            self.update_preview()
            self.status_bar.showMessage(f"✅ 已替换: \"{old}\" → \"{new}\"")
        else:
            self.status_bar.showMessage(f"⚠️ 未找到 \"{old}\" 或替换失败")

    def _choose_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self._text_color = color
            self.status_bar.showMessage(f"文字颜色已设置")

    def _add_text_to_page(self):
        text = self.add_text_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请输入文字内容")
            return
        # 放在页面左上角 50, 100 位置
        x = 50
        y = 100
        color = getattr(self, '_text_color', None)
        rgb = (color.red()/255, color.green()/255, color.blue()/255) if color else (0, 0, 0)

        ok = self.pdf.add_text(
            self.current_page, text, x, y,
            fontsize=self.font_size_spin.value(),
            color=rgb
        )
        if ok:
            self.update_preview()
            self.status_bar.showMessage(f"✅ 已添加文字")
        else:
            QMessageBox.warning(self, "错误", "添加文字失败")

    def _add_signature(self):
        dialog = SignaturePad(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 保存到临时文件
            tmp_path = "/tmp/pdf_editor_signature.png"
            dialog.save_to_file(tmp_path)

            if not self.pdf.doc:
                QMessageBox.warning(self, "提示", "请先打开一个 PDF 文件")
                return

            # 插入到页面中央偏下
            page = self.pdf.doc[self.current_page]
            page_w = page.rect.width
            page_h = page.rect.height
            x = page_w * 0.3
            y = page_h * 0.6
            w = page_w * 0.4
            h = w * 0.3

            ok = self.pdf.insert_image(self.current_page, tmp_path, x, y, w, h)
            if ok:
                self.update_preview()
                self.status_bar.showMessage("✅ 签名已添加")
            else:
                QMessageBox.warning(self, "错误", "插入签名失败")

    def _insert_image(self):
        if not self.pdf.doc:
            QMessageBox.warning(self, "提示", "请先打开一个 PDF 文件")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not path:
            return

        page = self.pdf.doc[self.current_page]
        page_w = page.rect.width
        page_h = page.rect.height

        x = page_w * 0.2
        y = page_h * 0.3
        w = page_w * 0.6
        h = page_h * 0.4

        ok = self.pdf.insert_image(self.current_page, path, x, y, w, h)
        if ok:
            self.update_preview()
            self.status_bar.showMessage("✅ 图片已插入")
        else:
            QMessageBox.warning(self, "错误", "插入图片失败")

    def _insert_stamp(self):
        """插入红色圆形印章"""
        if not self.pdf.doc:
            QMessageBox.warning(self, "提示", "请先打开一个 PDF 文件")
            return

        try:
            from PIL import Image, ImageDraw, ImageFont

            stamp_path = "/tmp/pdf_editor_stamp.png"
            text, ok = QInputDialog.getText(self, "印章文字", "输入印章文字:")
            if not ok or not text:
                text = "已审核"

            img_size = 300
            img = Image.new("RGBA", (img_size, img_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # 红色圆
            center = img_size // 2
            r = img_size // 2 - 10
            draw.ellipse(
                [center - r, center - r, center + r, center + r],
                outline=(220, 40, 40, 220), width=5
            )

            # 文字
            try:
                font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 40)
            except:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((center - tw // 2, center - th // 2),
                      text, fill=(220, 40, 40, 220), font=font)

            img.save(stamp_path, "PNG")

            page = self.pdf.doc[self.current_page]
            page_w = page.rect.width
            page_h = page.rect.height
            stamp_size = min(page_w, page_h) * 0.2
            x = page_w - stamp_size - 30
            y = 30

            ok = self.pdf.insert_image(self.current_page, stamp_path, x, y, stamp_size, stamp_size)
            if ok:
                self.update_preview()
                self.status_bar.showMessage("✅ 印章已插入")
            else:
                QMessageBox.warning(self, "错误", "插入印章失败")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"生成印章失败: {e}")

    def _delete_current_page(self):
        if self.pdf.page_count <= 1:
            QMessageBox.warning(self, "提示", "至少保留一页")
            return
        if self.pdf.delete_page(self.current_page):
            if self.current_page >= self.pdf.page_count:
                self.current_page = self.pdf.page_count - 1
            self.update_page_list()
            self.update_preview()
            self.update_toolbar()
            self.status_bar.showMessage("✅ 页面已删除")

    def _rotate_current_page(self):
        if self.pdf.rotate_page(self.current_page, 90):
            self.update_preview()
            self.status_bar.showMessage("✅ 页面已旋转 90°")

    def _insert_blank_page(self):
        self.pdf.insert_blank_page(self.current_page)
        self.update_page_list()
        self.update_preview()
        self.update_toolbar()
        self.status_bar.showMessage("✅ 空白页已添加")

    # ====== UI 更新 ======

    def update_preview(self):
        if not self.pdf.doc:
            self.preview_label.clear()
            self.preview_label.setFixedSize(600, 400)
            return

        img_data = self.pdf.render_page(self.current_page, self.zoom)
        if img_data:
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            self.preview_label.setPixmap(pixmap)
            self.preview_label.setFixedSize(pixmap.size())

    def update_page_list(self):
        self.page_list.blockSignals(True)
        self.page_list.clear()
        for i in range(self.pdf.page_count):
            item = QListWidgetItem(f"第 {i+1} 页")
            self.page_list.addItem(item)
        if self.current_page < self.pdf.page_count:
            self.page_list.setCurrentRow(self.current_page)
        self.page_list.blockSignals(False)

    def update_toolbar(self):
        total = self.pdf.page_count
        self.page_label.setText(f"第 {self.current_page + 1}/{total} 页")
        self.zoom_label.setText(f"{int(self.zoom * 100)}%")


class InlineEdit(QLineEdit):
    """内联文字编辑框，在 PDF 预览上直接编辑"""
    def __init__(self, pdf_coords, zoom, parent_label, editor, page_idx, old_text):
        super().__init__(parent_label)
        self.pdf_coords = pdf_coords  # (x, y, w, h) in PDF space
        self.zoom_factor = zoom
        self.parent_label = parent_label
        self.editor = editor
        self.page_idx = page_idx
        self.old_text = old_text
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.setText(old_text)
        self.selectAll()

        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #1a73e8;
                background: rgba(255, 255, 255, 0.92);
                padding: 1px 2px;
                font-size: 13px;
                color: #111;
            }
        """)

        font = QFont("PingFang SC", 12)
        self.setFont(font)
        self.setPlaceholderText("在此编辑...")

        self.returnPressed.connect(self._confirm)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == 10:  # FocusOut
            self._confirm()
            return True
        return super().eventFilter(obj, event)

    def _confirm(self):
        new_text = self.text().strip()
        if new_text and new_text != self.old_text:
            self.editor.pdf.replace_text(self.page_idx, self.old_text, new_text)
            self.editor.update_preview()
            self.editor.status_bar.showMessage(f"✅ 已替换: \"{self.old_text[:15]}\" → \"{new_text[:15]}\"")
        self.parent_label._clear_inline_edit()
        self.parent_label.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.parent_label._clear_inline_edit()
            self.parent_label.setFocus()
            return
        super().keyPressEvent(event)


class ClickableLabel(QLabel):
    """
    可点击/可编辑的 PDF 预览标签
    - 点击文字：原地内联编辑（像 Word）
    - 点击空白：添加新文字
    - 拖拽 PDF 文件：打开
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.editor = None
        self.pdf = None
        self.inline_edit = None
        self._current_editing = False

    def set_editor(self, editor):
        self.editor = editor
        self.pdf = editor.pdf if editor else None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile().lower()
                if path.endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        try:
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    path = url.toLocalFile()
                    if path.lower().endswith(".pdf") and os.path.exists(path):
                        self.editor.open_file(path)
                        event.acceptProposedAction()
                        return
            event.ignore()
        except Exception as e:
            print(f"dropEvent error: {e}")
            event.ignore()

    def _get_pdf_coords(self, click_x, click_y):
        """将屏幕坐标转换为 PDF 坐标"""
        label_w = self.width()
        label_h = self.height()
        if label_w == 0 or label_h == 0:
            return None

        page = self.pdf.doc[self.editor.current_page]
        page_w = page.rect.width
        page_h = page.rect.height

        zoom_x = page_w / label_w
        zoom_y = page_h / label_h
        zoom = max(zoom_x, zoom_y)

        display_w = page_w / zoom
        display_h = page_h / zoom
        offset_x = (label_w - display_w) / 2
        offset_y = (label_h - display_h) / 2

        pdf_x = (click_x - offset_x) * zoom
        pdf_y = (click_y - offset_y) * zoom

        if pdf_x < 0 or pdf_x > page_w or pdf_y < 0 or pdf_y > page_h:
            return None

        return pdf_x, pdf_y, zoom

    def _clear_inline_edit(self):
        """移除内联编辑框"""
        if self.inline_edit:
            try:
                self.inline_edit.deleteLater()
            except:
                pass
            self.inline_edit = None
            self._current_editing = False

    def _show_inline_edit(self, pdf_x, pdf_y, pdf_w, pdf_h, text):
        """
        在 PDF 文字位置显示内联编辑框
        将 PDF 坐标转换为屏幕坐标
        """
        label_w = self.width()
        label_h = self.height()
        if label_w == 0 or label_h == 0:
            return

        page = self.pdf.doc[self.editor.current_page]
        page_w = page.rect.width
        page_h = page.rect.height

        zoom_x = page_w / label_w
        zoom_y = page_h / label_h
        zoom = max(zoom_x, zoom_y)

        display_w = page_w / zoom
        display_h = page_h / zoom
        offset_x = (label_w - display_w) / 2
        offset_y = (label_h - display_h) / 2

        # PDF → 屏幕坐标
        sx = offset_x + pdf_x / zoom
        sy = offset_y + pdf_y / zoom
        sw = max(pdf_w / zoom * 1.1, 60)
        sh = max(pdf_h / zoom * 1.3, 24)

        # 清除旧的编辑框
        self._clear_inline_edit()

        # 创建内联编辑框
        self.inline_edit = QLineEdit(self)
        self.inline_edit.setText(text)
        self.inline_edit.selectAll()
        self.inline_edit.setGeometry(int(sx), int(sy), int(sw), int(sh))
        self.inline_edit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #1a73e8;
                background: rgba(255, 255, 255, 0.95);
                padding: 1px 3px;
                font-size: 13px;
                color: #111;
            }
        """)
        self.inline_edit.returnPressed.connect(lambda: self._confirm_inline_edit(text))
        self.inline_edit.setFocus()
        self.inline_edit.show()
        self._current_editing = True

    def _confirm_inline_edit(self, old_text):
        if not self.inline_edit:
            return
        new_text = self.inline_edit.text().strip()
        if new_text and new_text != old_text:
            self.editor.pdf.replace_text(self.editor.current_page, old_text, new_text)
            self.editor.update_preview()
            self.editor.status_bar.showMessage(f"✅ 已替换: \"{old_text[:15]}\" → \"{new_text[:15]}\"")
        self._clear_inline_edit()

    def mousePressEvent(self, event):
        # 先读取坐标（super() 调用可能使 event 失效）
        pos = event.position()
        pos_x, pos_y = pos.x(), pos.y()

        # 让基类先处理事件（确保 QAction 等能正常触发）
        super().mousePressEvent(event)

        # 如果正在编辑，先尝试确认
        if self._current_editing:
            self._confirm_inline_edit(self.inline_edit.text() if self.inline_edit else "")
            return

        if not self.pdf or not self.pdf.doc or not self.editor:
            return  # 没有 PDF 打开时不做任何事

        coords = self._get_pdf_coords(pos_x, pos_y)
        if coords is None:
            return

        pdf_x, pdf_y, zoom = coords
        page_idx = self.editor.current_page

        # 搜索此位置的文字
        text_info = self.pdf.get_text_at_point(page_idx, pdf_x, pdf_y)
        if text_info:
            text = text_info["text"]
            inst_x = text_info["x0"]
            inst_y = text_info["y0"]
            inst_w = text_info["x1"] - text_info["x0"]
            inst_h = text_info["y1"] - text_info["y0"]
            self._show_inline_edit(inst_x, inst_y, inst_w, inst_h, text)
        else:
            # 没点到文字 → 可添加文字
            text, ok = QInputDialog.getText(self, "添加文字", "在此位置输入新文字:")
            if ok and text:
                self.editor.pdf.add_text(page_idx, text, pdf_x, pdf_y, 12)
                self.editor.update_preview()
                self.editor.status_bar.showMessage("✅ 已添加文字")


def launch():
    app = QApplication(sys.argv)
    font = QFont("PingFang SC", 11)
    app.setFont(font)
    editor = PDFEditor()
    editor.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
