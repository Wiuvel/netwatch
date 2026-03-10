# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QBrush, QColor, QScreen
from PyQt6 import sip
from .styles import TOAST_DURATION_MS, TOAST_ANIM_MS, COLOR_BG_CARD, COLOR_TEXT_PRIMARY, COLOR_WARNING, COLOR_SUCCESS

class Toast(QWidget):
    def __init__(self, text="", level="info", duration=TOAST_DURATION_MS):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.text = text
        self.duration = duration
        self._closing = False

        self.bg_color = {
            "error": COLOR_BG_CARD,
            "warn": COLOR_WARNING,
            "success": COLOR_SUCCESS,
            "info": COLOR_BG_CARD
        }.get(level, COLOR_BG_CARD)

        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.pos_anim = QPropertyAnimation(self, b"pos")
        self._init_ui()

    def _init_ui(self):
        self.setFixedSize(300, 60)
        layout = QVBoxLayout(self)
        self.label = QLabel(self.text)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-family: 'Exo 2', 'Inter', 'Segoe UI'; font-size: 12px; font-weight: 500; border: none; background: transparent;")
        layout.addWidget(self.label)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QBrush(QColor(self.bg_color)))
        painter.setPen(QColor(255, 255, 255, 30))
        painter.drawRoundedRect(rect, 12, 12)

    def is_alive(self):
        try:
            return not sip.isdeleted(self)
        except (RuntimeError, TypeError):
            return False

    def show_toast(self):
        screen = QScreen.availableGeometry(self.screen())
        margin = 20
        target_x = screen.left() + margin
        target_y = screen.bottom() - self.height() - margin

        self.setWindowOpacity(0.0)
        start_pos = QPoint(target_x, target_y + 20)
        target_pos = QPoint(target_x, target_y)
        self.move(start_pos)

        self.opacity_anim.setDuration(TOAST_ANIM_MS)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.pos_anim.setDuration(TOAST_ANIM_MS)
        self.pos_anim.setStartValue(start_pos)
        self.pos_anim.setEndValue(target_pos)
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.show()
        self.opacity_anim.start()
        self.pos_anim.start()

        QTimer.singleShot(self.duration, self.hide_toast)

    def hide_toast(self):
        if self._closing or not self.is_alive():
            return
        self._closing = True

        self.opacity_anim.setStartValue(self.windowOpacity())
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.setDuration(TOAST_ANIM_MS)
        self.opacity_anim.start()

        cur_pos = self.pos()
        self.pos_anim.setStartValue(cur_pos)
        self.pos_anim.setEndValue(QPoint(cur_pos.x(), cur_pos.y() + 20))
        self.pos_anim.start()

        QTimer.singleShot(TOAST_ANIM_MS, self.close)

    def reposition(self, index):
        if not self.is_alive() or self._closing:
            return
        try:
            screen = QScreen.availableGeometry(self.screen())
            margin = 20
            target_x = screen.left() + margin
            target_y = screen.bottom() - self.height() - margin - (index * (self.height() + 10))

            new_pos = QPoint(target_x, target_y)
            self.pos_anim.stop()
            self.pos_anim.setStartValue(self.pos())
            self.pos_anim.setEndValue(new_pos)
            self.pos_anim.start()
        except RuntimeError:
            pass
