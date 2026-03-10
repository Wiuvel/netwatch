# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import time
import threading
import qtawesome as qta
import psutil
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, pyqtSlot, QSettings, QSize, QFileInfo,
    QObject, pyqtSignal, QThreadPool, QRunnable, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
)
from PyQt6.QtGui import QColor, QIcon, QPixmap, QFontDatabase, QPainter, QPen, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QFileDialog, QToolButton,
    QApplication, QFrame, QStackedWidget, QScrollArea, QFileIconProvider,
    QStyledItemDelegate, QStyle, QGridLayout, QSizePolicy, QGraphicsOpacityEffect, QMessageBox
)

from .styles import (
    MAIN_STYLE, WINDOW_WIDTH, WINDOW_HEIGHT, OUTPUT_FILE,
    LIST_UPDATE_INTERVAL_MS, NEW_IP_HIGHLIGHT_MS, TOAST_DURATION_MS, TOAST_ANIM_MS,
    COLOR_NEW_IP, ICON_PATH, LOGO_PATH, FONTS_DIR,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_BG_CARD, COLOR_BORDER, COLOR_ACCENT,
    COLOR_SUCCESS, COLOR_DANGER, COLOR_ACCENT_HOVER
)
from .toast import Toast
from core.monitor import ProcessMonitor
from core.utils import process_and_collapse_networks, save_subnets_to_file, validate_process_name, get_ip_info
from core.translations import TRANSLATIONS
import locale
import ctypes

class WorkerSignals(QObject):
    finished = pyqtSignal(str, str) # ip, info

class InfoWorker(QRunnable):
    def __init__(self, ip):
        super().__init__()
        self.setAutoDelete(False)
        self.ip = ip
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        info = get_ip_info(self.ip)
        if info:
            self.signals.finished.emit(self.ip, info)

class ResultDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        
        # Data
        ip = index.data(Qt.ItemDataRole.UserRole + 1)
        info = index.data(Qt.ItemDataRole.UserRole + 2)
        is_new = index.data(Qt.ItemDataRole.UserRole + 3)
        
        # Fallback if roles not set
        if not ip:
            text = index.data(Qt.ItemDataRole.DisplayRole)
            if text:
                parts = text.split(maxsplit=1)
                ip = parts[0]
                info = parts[1] if len(parts) > 1 else ""
            else:
                ip = ""
                info = ""

        rect = option.rect
        
        # Background
        bg_color = QColor("#0F1724") 
        if option.state & QStyle.StateFlag.State_Selected:
            bg_color = QColor("#1E293B")
        elif option.state & QStyle.StateFlag.State_MouseOver:
            bg_color = QColor("#162029")
            
        painter.fillRect(rect, bg_color)
        
        # Content Rect
        content_rect = rect.adjusted(20, 0, -20, 0)
        
        # Draw IP
        painter.setPen(QColor("#F3F4F6"))
        font = option.font
        font.setPointSize(13)
        
        if is_new:
             painter.setPen(QColor(COLOR_NEW_IP))
             font.setBold(True)
        else:
             font.setBold(True)
             
        painter.setFont(font)
        
        # IP Column width fixed
        ip_width = 160
        ip_spacing = 20
        ip_rect = QRect(content_rect.x(), content_rect.y(), ip_width, content_rect.height())
        fm = painter.fontMetrics()
        elided_ip = fm.elidedText(ip, Qt.TextElideMode.ElideRight, ip_width)
        painter.drawText(ip_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_ip)

        # Connection count badge — placed between IP and info
        conn_count = index.data(Qt.ItemDataRole.UserRole + 4)
        badge_total_w = 0
        if conn_count and conn_count > 0:
            badge_text = str(conn_count)
            badge_font = QFont(option.font)
            badge_font.setPointSize(9)
            badge_font.setBold(True)
            painter.setFont(badge_font)
            fm = painter.fontMetrics()
            badge_w = max(fm.horizontalAdvance(badge_text) + 12, 24)
            badge_h = 18
            badge_x = content_rect.x() + ip_width + ip_spacing
            badge_y = rect.center().y() - badge_h // 2
            badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)
            painter.setBrush(QColor("#3B82F6" if conn_count < 5 else "#F59E0B" if conn_count < 10 else "#EF4444"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect, 9, 9)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
            badge_total_w = badge_w + 8

        # Draw Info — offset by badge width if present
        if info:
            info_x = content_rect.x() + ip_width + ip_spacing + badge_total_w
            info_rect = QRect(info_x, content_rect.y(),
                            content_rect.right() - info_x, content_rect.height())

            painter.setPen(QColor("#94A3B8"))
            font.setBold(False)
            font.setPointSize(13)
            painter.setFont(font)

            fm = painter.fontMetrics()
            elided_info = fm.elidedText(info, Qt.TextElideMode.ElideRight, info_rect.width())
            painter.drawText(info_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_info)

        # Bottom Border
        painter.setPen(QPen(QColor("#1F2937"), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        painter.restore()
        
    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 48)

class AnimatedStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation_duration = 300
        self.animation_curve = QEasingCurve.Type.OutCubic

    def setCurrentIndex(self, index):
        if index == self.currentIndex():
            return

        current_widget = self.currentWidget()
        next_widget = self.widget(index)
        
        if not current_widget:
            super().setCurrentIndex(index)
            return

        # Geometry
        width = self.width()
        height = self.height()
        
        next_widget.setGeometry(0, 0, width, height)
        
        # Determine direction
        if index > self.currentIndex():
            offset_x = width
            end_x = -width
        else:
            offset_x = -width
            end_x = width

        next_widget.move(offset_x, 0)
        next_widget.show()
        next_widget.raise_()

        # Animations
        self.anim_group = QParallelAnimationGroup(self)

        anim_curr = QPropertyAnimation(current_widget, b"pos")
        anim_curr.setDuration(self.animation_duration)
        anim_curr.setStartValue(QPoint(0, 0))
        anim_curr.setEndValue(QPoint(end_x, 0))
        anim_curr.setEasingCurve(self.animation_curve)

        anim_next = QPropertyAnimation(next_widget, b"pos")
        anim_next.setDuration(self.animation_duration)
        anim_next.setStartValue(QPoint(offset_x, 0))
        anim_next.setEndValue(QPoint(0, 0))
        anim_next.setEasingCurve(self.animation_curve)

        self.anim_group.addAnimation(anim_curr)
        self.anim_group.addAnimation(anim_next)
        
        def on_finished():
            current_widget.hide()
            current_widget.move(0, 0) # Reset
            super(AnimatedStackedWidget, self).setCurrentIndex(index)

        self.anim_group.finished.connect(on_finished)
        self.anim_group.start()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("NetWatch", "Config")
        self._load_fonts()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setObjectName("main_window")
        self.setStyleSheet(MAIN_STYLE)
        
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        self.monitor = None
        self.all_ips = set()
        self.new_ips = set()
        self.conn_counts = {}
        self.ip_info_cache = {}
        self.pending_info_requests = set()
        self._active_workers = set()
        self._last_collapsed = [] # For change detection
        self._last_query = ""
        self._info_updated = False
        self._drag_pos = None
        self._toasts = []
        self._icon_provider = QFileIconProvider()
        self.threadpool = QThreadPool.globalInstance()
        self.threadpool.setMaxThreadCount(10) # Limit concurrent API requests

        # Language Init
        self.current_lang = self.settings.value("language", "", type=str)
        if not self.current_lang:
            # Auto-detect
            try:
                # Windows specific check
                windll = ctypes.windll.kernel32
                lang_id = windll.GetUserDefaultUILanguage()
                # 0x0419 is Russian
                self.current_lang = "ru" if lang_id == 0x0419 else "en"
            except:
                # Fallback to locale
                sys_lang = locale.getdefaultlocale()[0]
                self.current_lang = "ru" if sys_lang and "ru" in sys_lang.lower() else "en"
            self.settings.setValue("language", self.current_lang)
        
        if self.current_lang not in TRANSLATIONS:
            self.current_lang = "en"

        self._setup_timers()
        self._init_ui()

    def tr(self, key):
        return TRANSLATIONS.get(self.current_lang, {}).get(key, key)

    def _load_fonts(self):
        if os.path.exists(FONTS_DIR):
            for font_file in os.listdir(FONTS_DIR):
                if font_file.endswith(('.ttf', '.otf', '.woff2')):
                    QFontDatabase.addApplicationFont(os.path.join(FONTS_DIR, font_file))

    def _setup_timers(self):
        self.ui_update_timer = QTimer()
        self.ui_update_timer.setInterval(LIST_UPDATE_INTERVAL_MS)
        self.ui_update_timer.timeout.connect(self.update_list_display)

        self.highlight_timer = QTimer()
        self.highlight_timer.setInterval(NEW_IP_HIGHLIGHT_MS)
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.timeout.connect(self._clear_highlights)

        # Timer for automatic process list refresh
        self.proc_refresh_timer = QTimer()
        self.proc_refresh_timer.setInterval(5000) # 5 seconds
        self.proc_refresh_timer.timeout.connect(self.refresh_processes)

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        sidebar_layout.setSpacing(15)

        # App Logo & Title in Sidebar
        sidebar_header = QHBoxLayout()
        if os.path.exists(LOGO_PATH):
            logo_label = QLabel()
            logo_pixmap = QPixmap(LOGO_PATH).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            sidebar_header.addWidget(logo_label)
        
        sidebar_title = QLabel("Net Watch")
        sidebar_title.setObjectName("title")
        sidebar_header.addWidget(sidebar_title)
        sidebar_header.addStretch()
        sidebar_layout.addLayout(sidebar_header)
        sidebar_layout.addSpacing(20)

        # Nav Buttons
        self.nav_monitor_btn = self._create_nav_btn("fa5s.desktop", self.tr("Monitor"), self.show_monitor_page)
        self.nav_settings_btn = self._create_nav_btn("fa5s.cog", self.tr("Settings"), self.show_settings_page)
        
        sidebar_layout.addWidget(self.nav_monitor_btn)
        sidebar_layout.addWidget(self.nav_settings_btn)
        sidebar_layout.addStretch()

        # Footer in Sidebar
        version_lbl = QLabel("v1.0.0")
        version_lbl.setObjectName("footer")
        sidebar_layout.addWidget(version_lbl)

        main_layout.addWidget(self.sidebar)

        # --- Content Area ---
        content_container = QWidget()
        self.content_layout = QVBoxLayout(content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Custom Title Bar (Right side only, for buttons)
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(50)
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(0, 0, 15, 0)
        title_bar_layout.addStretch()

        def create_title_btn(icon_name, hover_color, callback):
            btn = QPushButton()
            btn.setIcon(qta.icon(icon_name, color='#94A3B8'))
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1E293B;
                    border: none;
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                }}
            """)
            btn.clicked.connect(callback)
            return btn

        self.min_btn = create_title_btn("fa5s.minus", "#334155", self.showMinimized)
        self.close_btn = create_title_btn("fa5s.times", "#EF4444", self.close)
        
        title_bar_layout.addWidget(self.min_btn)
        title_bar_layout.addWidget(self.close_btn)
        self.content_layout.addWidget(self.title_bar)

        # Stacked Widget for Pages
        self.pages = AnimatedStackedWidget()
        self._init_monitor_page()
        self._init_settings_page()
        
        self.content_layout.addWidget(self.pages)
        main_layout.addWidget(content_container)

        # Default Page
        self.show_monitor_page()

    def _create_nav_btn(self, icon_name, text, callback):
        btn = QPushButton("  " + text)
        btn.setIcon(qta.icon(icon_name, color=COLOR_TEXT_SECONDARY))
        btn.setObjectName("nav_btn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn

    def _init_monitor_page(self):
        page = QWidget()
        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(25, 0, 25, 25)
        main_layout.setSpacing(25)

        # --- Left Column: Process Control (30%) ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Title
        title = QLabel(self.tr("Monitoring"))
        title.setObjectName("section_title")
        left_layout.addWidget(title)

        # Input Stack
        self.monitor_input_stack = QStackedWidget()
        
        # 1. Process Selection View
        self.proc_selector_view = QWidget()
        proc_sel_layout = QVBoxLayout(self.proc_selector_view)
        proc_sel_layout.setContentsMargins(0, 0, 0, 0)
        proc_sel_layout.setSpacing(10)
        
        proc_header = QHBoxLayout()
        proc_lbl = QLabel(self.tr("Processes"))
        proc_lbl.setStyleSheet("font-weight: 600; font-size: 14px; color: #94A3B8;")
        proc_header.addWidget(proc_lbl)
        proc_header.addStretch()
        self.refresh_proc_btn = QToolButton()
        self.refresh_proc_btn.setIcon(qta.icon("fa5s.sync", color=COLOR_TEXT_PRIMARY))
        self.refresh_proc_btn.setToolTip(self.tr("AutoRefresh")) # Assuming same key or new
        self.refresh_proc_btn.clicked.connect(self.refresh_processes)
        proc_header.addWidget(self.refresh_proc_btn)
        proc_sel_layout.addLayout(proc_header)

        self.proc_list = QListWidget()
        self.proc_list.setObjectName("proc_list")
        self.proc_list.setIconSize(QSize(24, 24))
        self.proc_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.proc_list.itemDoubleClicked.connect(self.toggle_monitoring)
        proc_sel_layout.addWidget(self.proc_list)
        
        self.monitor_input_stack.addWidget(self.proc_selector_view)

        # 2. Legacy Manual Input View
        self.legacy_input_view = QWidget()
        legacy_layout = QVBoxLayout(self.legacy_input_view)
        legacy_layout.setContentsMargins(0, 0, 0, 0)
        legacy_layout.setSpacing(15)
        
        input_desc = QLabel(self.tr("ManualInput"))
        input_desc.setObjectName("desc")
        legacy_layout.addWidget(input_desc)

        self.proc_input = QLineEdit()
        self.proc_input.setPlaceholderText(self.tr("PlaceholderProc"))
        legacy_layout.addWidget(self.proc_input)
        legacy_layout.addStretch()
        
        self.monitor_input_stack.addWidget(self.legacy_input_view)
        
        left_layout.addWidget(self.monitor_input_stack)

        # Action Button
        self.toggle_btn = QPushButton(self.tr("Start"))
        self.toggle_btn.setIcon(qta.icon("fa5s.rocket", color="white"))
        self.toggle_btn.setObjectName("start_btn")
        self.toggle_btn.setFixedHeight(50)
        self.toggle_btn.clicked.connect(self.toggle_monitoring)
        left_layout.addWidget(self.toggle_btn)

        # --- Right Column: Results (70%) ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        # Header with Search and Actions
        results_header = QHBoxLayout()
        results_header.setSpacing(10)
        
        # Search Box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Search"))
        self.search_input.setMinimumWidth(100)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.addAction(qta.icon("fa5s.search", color="#64748B"), QLineEdit.ActionPosition.LeadingPosition)
        self.search_input.textChanged.connect(self.update_list_display)
        results_header.addWidget(self.search_input)
        
        # results_header.addStretch() # Removed stretch to allow search to expand

        self.copy_btn = QToolButton()
        self.copy_btn.setText(self.tr("Copy"))
        self.copy_btn.setIcon(qta.icon("fa5s.copy", color="#F3F4F6"))
        self.copy_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        results_header.addWidget(self.copy_btn)

        self.save_btn = QToolButton()
        self.save_btn.setText(self.tr("Save"))
        self.save_btn.setIcon(qta.icon("fa5s.save", color="#F3F4F6"))
        self.save_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.save_btn.clicked.connect(self.save_to_file_dialog)
        results_header.addWidget(self.save_btn)

        right_layout.addLayout(results_header)

        # Results List
        self.list_widget = QListWidget()
        self.list_widget.setItemDelegate(ResultDelegate(self.list_widget))
        self.list_widget.setSpacing(4)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.itemDoubleClicked.connect(self._copy_single_ip)
        right_layout.addWidget(self.list_widget)

        # Status Bar
        self.status_lbl = QLabel(self.tr("Ready"))
        self.status_lbl.setObjectName("footer")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(self.status_lbl)

        # Add columns to main layout
        main_layout.addWidget(left_container, 50)
        main_layout.addWidget(right_container, 50)

        self.pages.addWidget(page)
        self.monitor_page_idx = self.pages.indexOf(page)

    def _init_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 0, 25, 25)
        layout.setSpacing(20)

        title = QLabel(self.tr("Settings"))
        title.setObjectName("section_title")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        container_layout = QGridLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(20)

        def create_setting_row(title_text, desc_text, callback, initial_state=False):
            row = QFrame()
            row.setStyleSheet(f"background-color: {COLOR_BG_CARD}; border-radius: 16px; border: 1px solid {COLOR_BORDER};")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(20, 20, 20, 20)
            
            info = QVBoxLayout()
            t = QLabel(title_text)
            t.setStyleSheet("font-weight: 600; font-size: 15px; border: none; background: transparent;")
            d = QLabel(desc_text)
            d.setObjectName("desc")
            d.setStyleSheet("border: none; background: transparent;")
            d.setWordWrap(True)
            info.addWidget(t)
            info.addWidget(d)
            row_layout.addLayout(info)
            
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setChecked(initial_state)
            btn.setFixedWidth(120)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            def update_btn_style():
                if btn.isChecked():
                    btn.setText(self.tr("On"))
                    btn.setObjectName("toggle_on")
                else:
                    btn.setText(self.tr("Off"))
                    btn.setObjectName("toggle_off")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

            btn.clicked.connect(update_btn_style)
            btn.clicked.connect(callback)
            update_btn_style()
            
            row_layout.addWidget(btn)
            return row, btn

        # Legacy Mode
        is_legacy = self.settings.value("legacy_mode", False, type=bool)
        legacy_row, self.legacy_toggle = create_setting_row(
            self.tr("LegacyMode"), 
            self.tr("LegacyDesc"),
            self.update_settings_ui,
            is_legacy
        )
        container_layout.addWidget(legacy_row, 0, 0)

        # Hide System Processes
        hide_system = self.settings.value("hide_system", True, type=bool)
        system_row, self.system_toggle = create_setting_row(
            self.tr("HideSystem"),
            self.tr("HideSystemDesc"),
            self.update_settings_ui,
            hide_system
        )
        container_layout.addWidget(system_row, 0, 1)

        # Show Toasts
        show_toasts = self.settings.value("show_toasts", True, type=bool)
        toast_row, self.toast_toggle = create_setting_row(
            self.tr("Toasts"),
            self.tr("ToastsDesc"),
            self.update_settings_ui,
            show_toasts
        )
        container_layout.addWidget(toast_row, 1, 0)

        # Auto-refresh Process List
        auto_refresh = self.settings.value("auto_refresh", True, type=bool)
        refresh_row, self.refresh_toggle = create_setting_row(
            self.tr("AutoRefresh"),
            self.tr("AutoRefreshDesc"),
            self.update_settings_ui,
            auto_refresh
        )
        container_layout.addWidget(refresh_row, 1, 1)

        # Language Toggle
        def toggle_language():
            new_lang = "en" if self.current_lang == "ru" else "ru"
            
            # Show confirmation dialog
            msg = QMessageBox(self)
            msg.setWindowTitle("Net Watch")
            
            # Use text based on TARGET language
            if new_lang == "ru":
                title_text = "Язык интерфейса"
                info_text = "Перезапустить приложение для смены языка на Русский?"
                yes_text = "Да"
                no_text = "Нет"
            else:
                title_text = "Interface Language"
                info_text = "Restart application to switch language to English?"
                yes_text = "Yes"
                no_text = "No"
                
            msg.setText(title_text)
            msg.setInformativeText(info_text)
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            msg.button(QMessageBox.StandardButton.Yes).setText(yes_text)
            msg.button(QMessageBox.StandardButton.No).setText(no_text)
            
            # Style the message box to match theme
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {COLOR_BG_CARD};
                    color: {COLOR_TEXT_PRIMARY};
                }}
                QLabel {{
                    color: {COLOR_TEXT_PRIMARY};
                }}
                QPushButton {{
                    background-color: {COLOR_ACCENT};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                    min-width: 60px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_ACCENT_HOVER};
                }}
            """)
            
            ret = msg.exec()
            
            if ret == QMessageBox.StandardButton.Yes:
                self.settings.setValue("language", new_lang)
                
                # Restart app logic
                if getattr(sys, 'frozen', False):
                    # On Windows, os.startfile is the most reliable way to restart a frozen EXE
                    # It starts a completely fresh process as if the user clicked the file again.
                    try:
                        os.startfile(sys.executable)
                    except AttributeError:
                        # Fallback for non-Windows (or just in case)
                        subprocess.Popen([sys.executable] + sys.argv[1:])
                else:
                    # For regular python script execution
                    subprocess.Popen([sys.executable] + sys.argv)
                
                QApplication.quit()
                sys.exit(0)
            else:
                # Revert toggle visually if user said No
                self.lang_toggle.blockSignals(True)
                self.lang_toggle.setChecked(self.current_lang == "ru")
                update_lang_btn()
                self.lang_toggle.blockSignals(False)
            
        lang_row, self.lang_toggle = create_setting_row(
            self.tr("Language"),
            self.tr("LanguageDesc"),
            toggle_language,
            self.current_lang == "ru"
        )
        # Customizing language button text
        def update_lang_btn():
            # If checked -> RU, else -> EN
            # But the button logic in create_setting_row sets "On"/"Off"
            # We need to override it
            if self.lang_toggle.isChecked():
                self.lang_toggle.setText("RU")
            else:
                self.lang_toggle.setText("EN")
        
        # Disconnect default slot and connect custom
        try:
            self.lang_toggle.clicked.disconnect()
        except:
            pass
            
        self.lang_toggle.clicked.connect(toggle_language)
        self.lang_toggle.clicked.connect(update_lang_btn)
        
        # Set initial state based on current lang
        self.lang_toggle.setChecked(self.current_lang == "ru")
        update_lang_btn()

        container_layout.addWidget(lang_row, 2, 0)


        container_layout.setRowStretch(3, 1)
        container_layout.setColumnStretch(0, 1)
        container_layout.setColumnStretch(1, 1)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.pages.addWidget(page)
        self.settings_page_idx = self.pages.indexOf(page)
        self.update_settings_ui()

    def update_settings_ui(self):
        # Save settings
        self.settings.setValue("legacy_mode", self.legacy_toggle.isChecked())
        self.settings.setValue("hide_system", self.system_toggle.isChecked())
        self.settings.setValue("show_toasts", self.toast_toggle.isChecked())
        self.settings.setValue("auto_refresh", self.refresh_toggle.isChecked())
        
        # Update monitor input view
        self.monitor_input_stack.setCurrentIndex(1 if self.legacy_toggle.isChecked() else 0)
        
        # Update refresh timer
        if self.refresh_toggle.isChecked() and not self.legacy_toggle.isChecked():
            if not self.proc_refresh_timer.isActive():
                self.proc_refresh_timer.start()
        else:
            self.proc_refresh_timer.stop()
            
        if not self.legacy_toggle.isChecked():
            self.refresh_processes()

    def toggle_legacy_mode(self):
        self.update_settings_ui()

    def show_monitor_page(self):
        self.pages.setCurrentIndex(self.monitor_page_idx)
        self._update_nav_highlight(self.nav_monitor_btn)
        if not self.legacy_toggle.isChecked():
            self.refresh_processes()
            if self.refresh_toggle.isChecked():
                self.proc_refresh_timer.start()

    def show_settings_page(self):
        self.pages.setCurrentIndex(self.settings_page_idx)
        self._update_nav_highlight(self.nav_settings_btn)
        self.proc_refresh_timer.stop()

    def _update_nav_highlight(self, active_btn):
        for btn in [self.nav_monitor_btn, self.nav_settings_btn]:
            btn.setProperty("active", btn == active_btn)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def refresh_processes(self):
        # Store current selection
        current_sel = None
        if self.proc_list.currentItem():
            current_sel = self.proc_list.currentItem().data(Qt.ItemDataRole.UserRole)
            
        self.proc_list.clear()
        hide_system = self.system_toggle.isChecked()
        
        # Group by name
        grouped_processes = {}
        
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                info = proc.info
                name = info['name']
                exe = info['exe']
                if not name or not exe: continue
                
                # Simple system process filtering
                if hide_system:
                    exe_path = exe.lower()
                    if "windows\\system32" in exe_path or "windows\\syswow64" in exe_path:
                        continue
                
                if name not in grouped_processes:
                    grouped_processes[name] = exe
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by name
        sorted_names = sorted(grouped_processes.keys(), key=lambda x: x.lower())
        
        for name in sorted_names:
            item = QListWidgetItem(name)
            exe_path = grouped_processes[name]
            icon = self._icon_provider.icon(QFileInfo(exe_path))
            item.setIcon(icon)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.proc_list.addItem(item)
            
            # Restore selection
            if current_sel and name == current_sel:
                self.proc_list.setCurrentItem(item)

    # --- Window Dragging ---
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.pos().y() <= 50:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_pos and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # --- Monitoring Logic ---
    def toggle_monitoring(self):
        if self.monitor and self.monitor.running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        self.all_ips.clear()
        self.new_ips.clear()
        self.conn_counts.clear()
        self.list_widget.clear()
        
        if self.legacy_toggle.isChecked():
            raw_name = self.proc_input.text().strip()
        else:
            selected_item = self.proc_list.currentItem()
            if not selected_item:
                self.show_toast(self.tr("SelectProcess"), "warn")
                return
            raw_name = selected_item.data(Qt.ItemDataRole.UserRole)
            
        proc_name = validate_process_name(raw_name)
        
        if not proc_name:
            self.show_toast(self.tr("EnterValidName"), "warn")
            return

        self.monitor = ProcessMonitor(proc_name)
        self.monitor.new_subnets_signal.connect(self.on_new_subnets)
        self.monitor.conn_counts_signal.connect(self.on_conn_counts)
        self.monitor.error_signal.connect(self.on_monitor_error)
        self.monitor.finished_signal.connect(self.on_monitor_finished)
        
        self.monitor.start()
        
        self.toggle_btn.setText(self.tr("Stop"))
        self.toggle_btn.setIcon(qta.icon("fa5s.stop", color="white"))
        self.toggle_btn.setObjectName("stop_btn")
        self.toggle_btn.setStyleSheet("")
        
        if self.legacy_toggle.isChecked():
            self.proc_input.setEnabled(False)
        else:
            # self.proc_list.setEnabled(False) # Allow scrolling
            self.refresh_proc_btn.setEnabled(False)
            
        self.status_lbl.setText(self.tr("MonitoringStatus").format(proc_name))
        self.ui_update_timer.start()
        self.show_toast(self.tr("MonitoringStarted").format(proc_name), "success")

    def stop_monitoring(self):
        if self.monitor:
            self.monitor.stop()
        self.on_monitor_finished()
        self.show_toast(self.tr("Stopped"), "info")

    @pyqtSlot(set)
    def on_new_subnets(self, new_nets):
        self.new_ips |= new_nets
        self.all_ips |= new_nets
        save_subnets_to_file(self.all_ips, OUTPUT_FILE)
        self.highlight_timer.start()
        self.update_list_display()
        self.show_toast(self.tr("FoundSubnets").format(len(new_nets)), "info")

    @pyqtSlot(dict)
    def on_conn_counts(self, counts):
        self.conn_counts = counts
        self._info_updated = True

    @pyqtSlot(str)
    def on_monitor_error(self, err_msg):
        self.show_toast(self.tr("Error").format(err_msg), "error")
        self.stop_monitoring()

    @pyqtSlot()
    def on_monitor_finished(self):
        self.toggle_btn.setText(self.tr("Start"))
        self.toggle_btn.setIcon(qta.icon("fa5s.rocket", color="white"))
        self.toggle_btn.setObjectName("start_btn")
        self.toggle_btn.setStyleSheet("")
        
        self.proc_input.setEnabled(True)
        # self.proc_list.setEnabled(True)
        self.refresh_proc_btn.setEnabled(True)
        
        self.status_lbl.setText(self.tr("Ready"))
        self.ui_update_timer.stop()

    # --- UI Helpers ---
    def update_list_display(self):
        query = self.search_input.text().strip().lower()
        collapsed = process_and_collapse_networks(self.all_ips)
        
        # Check if we need to update
        if (collapsed == self._last_collapsed and 
            query == getattr(self, '_last_query', '') and 
            not getattr(self, '_info_updated', False)):
            return
            
        self._last_collapsed = collapsed
        self._last_query = query
        self._info_updated = False
        
        self.list_widget.clear()
        
        for net in collapsed:
            ip_str = str(net.network_address)
            
            # Check local cache first
            info = self.ip_info_cache.get(ip_str)
            
            # If not in cache and not already requested, fetch in background
            if info is None and ip_str not in self.pending_info_requests:
                self.pending_info_requests.add(ip_str)
                worker = InfoWorker(ip_str)
                self._active_workers.add(worker)

                def on_finished(ip, info_text, w=worker):
                    self.ip_info_cache[ip] = info_text
                    self._info_updated = True
                    self.pending_info_requests.discard(ip)
                    self._active_workers.discard(w)

                worker.signals.finished.connect(on_finished)
                self.threadpool.start(worker)
            
            # Formatting: IP on the left, Info on the right
            net_str = str(net)
            if info:
                display_text = f"{net_str} {info}"
            else:
                display_text = net_str
            
            # Filter by search query
            if query and query not in display_text.lower():
                continue
                
            conn_count = self.conn_counts.get(net_str, 0)

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, display_text)
            item.setData(Qt.ItemDataRole.UserRole + 1, net_str)
            item.setData(Qt.ItemDataRole.UserRole + 2, info if info else "")
            item.setData(Qt.ItemDataRole.UserRole + 3, net in self.new_ips)
            item.setData(Qt.ItemDataRole.UserRole + 4, conn_count)
                
            self.list_widget.addItem(item)
        
        # Auto-scroll to bottom if new items added and not searching
        if not query:
            self.list_widget.scrollToBottom()

    def _clear_highlights(self):
        self.new_ips.clear()
        self.update_list_display()

    def show_toast(self, text, level="info"):
        if not self.settings.value("show_toasts", True, type=bool):
            return

        toast = Toast(text, level)
        self._toasts.append(toast)

        self._cleanup_toasts()
        self._reposition_toasts()
        toast.show_toast()

        # Schedule cleanup after toast lifetime
        QTimer.singleShot(TOAST_DURATION_MS + TOAST_ANIM_MS + 200, self._cleanup_toasts)

    def _cleanup_toasts(self):
        self._toasts = [t for t in self._toasts if t.is_alive() and not t._closing]
        self._reposition_toasts()

    def _reposition_toasts(self):
        for i, t in enumerate(reversed(self._toasts)):
            if t.is_alive():
                t.reposition(i)

    def _copy_single_ip(self, item):
        ip = item.data(Qt.ItemDataRole.UserRole + 1)
        if ip:
            QApplication.clipboard().setText(ip)
            self.show_toast(self.tr("Copied"), "success")

    def copy_to_clipboard(self):
        collapsed = process_and_collapse_networks(self.all_ips)
        text = "\n".join(str(n) for n in collapsed)
        if text:
            QApplication.clipboard().setText(text)
            self.show_toast(self.tr("Copied"), "success")
        else:
            self.show_toast(self.tr("ListEmpty"), "warn")

    def save_to_file_dialog(self):
        if not self.all_ips:
            self.show_toast(self.tr("ListEmpty"), "warn")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, self.tr("SaveDialog"), "", self.tr("TextFiles"))
        if path:
            if save_subnets_to_file(self.all_ips, path):
                self.show_toast(self.tr("Saved"), "success")
            else:
                self.show_toast(self.tr("SaveError"), "error")

    def closeEvent(self, event):
        if self.monitor:
            self.monitor.stop()
        event.accept()
