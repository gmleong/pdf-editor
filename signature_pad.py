"""
签名手写板
PyQt6 QPainter 手写捕获 → 输出透明 PNG
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QDialog, QColorDialog, QSpinBox, QLabel, QComboBox)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import (QPainter, QPen, QColor, QPixmap, QImage, QBrush,
                         QFont, QAction)
import os


class SignaturePad(QDialog):
    """签名手写板对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("签名 / 手写")
        self.setFixedSize(600, 400)

        self.pen_color = QColor(0, 0, 0)  # 黑色
        self.pen_width = 3
        self.drawing = False
        self.last_point = None

        # 画布
        self.canvas = QPixmap(580, 310)
        self.canvas.fill(Qt.GlobalColor.white)

        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 20)
        self.width_spin.setValue(3)
        toolbar.addWidget(QLabel("粗细:"))
        toolbar.addWidget(self.width_spin)

        self.color_btn = QPushButton("颜色")
        self.color_btn.clicked.connect(self._choose_color)
        toolbar.addWidget(self.color_btn)

        self.pen_type = QComboBox()
        self.pen_type.addItems(["钢笔", "马克笔", "毛笔"])
        toolbar.addWidget(QLabel("笔型:"))
        toolbar.addWidget(self.pen_type)

        toolbar.addStretch()

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self.clear_btn)

        layout.addLayout(toolbar)

        # 画布区域
        self.canvas_label = QWidget()
        self.canvas_label.setFixedSize(580, 310)
        self.canvas_label.setStyleSheet("border: 1px solid #ccc;")
        self.canvas_label.mousePressEvent = self._mouse_press
        self.canvas_label.mouseMoveEvent = self._mouse_move
        self.canvas_label.mouseReleaseEvent = self._mouse_release
        self.canvas_label.paintEvent = self._paint_event
        layout.addWidget(self.canvas_label)

        # 按钮
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        ok_btn = QPushButton("✅ 确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_bar.addWidget(ok_btn)
        btn_bar.addWidget(cancel_btn)
        layout.addLayout(btn_bar)

        self._result_pixmap = None

    def _choose_color(self):
        color = QColorDialog.getColor(self.pen_color, self, "选择笔颜色")
        if color.isValid():
            self.pen_color = color

    def _clear(self):
        self.canvas.fill(Qt.GlobalColor.white)
        self.canvas_label.update()

    def _mouse_press(self, event):
        self.drawing = True
        self.last_point = event.pos()
        # 画一个点
        p = QPainter(self.canvas)
        pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPoint(self.last_point)
        p.end()
        self.canvas_label.update()

    def _mouse_move(self, event):
        if not self.drawing:
            return
        point = event.pos()
        p = QPainter(self.canvas)
        pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawLine(self.last_point, point)
        p.end()
        self.last_point = point
        self.canvas_label.update()

    def _mouse_release(self, event):
        self.drawing = False

    def _paint_event(self, event):
        p = QPainter(self.canvas_label)
        p.drawPixmap(0, 0, self.canvas)
        p.end()

    def get_pixmap(self) -> QPixmap:
        """获取签名结果"""
        return self.canvas.copy()

    def save_to_file(self, filepath: str) -> bool:
        """保存签名到 PNG 文件（透明背景）"""
        # 创建透明背景的 pixmap
        result = QPixmap(self.canvas.size())
        result.fill(Qt.GlobalColor.transparent)

        p = QPainter(result)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.drawPixmap(0, 0, self.canvas)
        p.end()

        return result.save(filepath, "PNG")

    def get_image_bytes(self) -> bytes:
        """获取签名 PNG bytes"""
        result = QPixmap(self.canvas.size())
        result.fill(Qt.GlobalColor.transparent)
        p = QPainter(result)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.drawPixmap(0, 0, self.canvas)
        p.end()

        ba = QByteArray()
        buf = QBuffer(ba)
        result.save(buf, "PNG")
        return ba.data()
