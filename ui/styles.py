# -*- coding: utf-8 -*-

import os

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

ICON_PATH = os.path.join(IMAGES_DIR, "icon.png")
LOGO_PATH = os.path.join(IMAGES_DIR, "icon.png")

# --- Configuration & Constants ---
OUTPUT_FILE = "ips_output.txt"
TOAST_DURATION_MS = 3500
TOAST_ANIM_MS = 400
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
NEW_IP_HIGHLIGHT_MS = 3000
LIST_UPDATE_INTERVAL_MS = 2000

# --- Colors ---
COLOR_BG_MAIN = "#0B0F17"
COLOR_BG_SIDEBAR = "#080B12"
COLOR_BG_CARD = "#111827"
COLOR_BG_INPUT = "#0F1724"
COLOR_BORDER = "#1F2937"
COLOR_ACCENT = "#3B82F6"
COLOR_ACCENT_HOVER = "#2563EB"
COLOR_TEXT_PRIMARY = "#F3F4F6"
COLOR_TEXT_SECONDARY = "#94A3B8"
COLOR_TEXT_DIM = "#64748B"
COLOR_DANGER = "#EF4444"
COLOR_WARNING = "#F59E0B"
COLOR_SUCCESS = "#10B981"
COLOR_NEW_IP = "#60A5FA"

# --- Stylesheet ---
MAIN_STYLE = f"""
    QWidget#main_window {{
        background-color: {COLOR_BG_MAIN};
        color: {COLOR_TEXT_PRIMARY};
        font-family: 'Exo 2', 'Inter', 'Segoe UI', sans-serif;
    }}
    
    QLabel {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: 14px;
    }}
    
    QWidget#sidebar {{
        background-color: {COLOR_BG_SIDEBAR};
        border-right: 1px solid {COLOR_BORDER};
    }}
    
    QPushButton#nav_btn {{
        background-color: transparent;
        border: none;
        border-radius: 12px;
        color: {COLOR_TEXT_SECONDARY};
        text-align: left;
        padding: 14px 20px;
        font-size: 15px;
        font-weight: 500;
        margin-bottom: 4px;
        outline: none;
    }}
    
    QPushButton#nav_btn:hover {{
        background-color: #162029;
        color: {COLOR_TEXT_PRIMARY};
    }}
    
    QPushButton#nav_btn:focus {{
        outline: none;
        border: none;
    }}

    QPushButton#nav_btn[active="true"] {{
        background-color: #1E293B;
        color: {COLOR_ACCENT};
        font-weight: 600;
    }}
    
    QLabel#title {{
        font-size: 22px;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        letter-spacing: -0.5px;
    }}
    
    QLabel#section_title {{
        font-size: 24px;
        font-weight: 700;
        color: {COLOR_TEXT_PRIMARY};
        margin-bottom: 20px;
    }}
    
    QLabel#desc {{
        font-size: 14px;
        color: {COLOR_TEXT_SECONDARY};
        line-height: 1.4;
    }}
    
    QLabel#footer {{
        font-size: 12px;
        color: {COLOR_TEXT_DIM};
    }}
    
    QLineEdit {{
        background-color: {COLOR_BG_INPUT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 12px;
        padding: 12px 16px;
        color: {COLOR_TEXT_PRIMARY};
        font-size: 14px;
        selection-background-color: {COLOR_ACCENT}40;
    }}
    
    QLineEdit:focus {{
        border: 1px solid {COLOR_ACCENT};
        background-color: {COLOR_BG_INPUT}CC;
    }}
    
    QPushButton {{
        background-color: {COLOR_BG_CARD};
        border: 1px solid {COLOR_BORDER};
        border-radius: 12px;
        padding: 12px 24px;
        color: {COLOR_TEXT_PRIMARY};
        font-weight: 600;
        font-size: 14px;
        outline: none;
    }}
    
    QPushButton:focus {{
        outline: none;
        border: 1px solid {COLOR_ACCENT};
    }}

    QPushButton:hover {{
        background-color: #1E293B;
        border: 1px solid {COLOR_TEXT_DIM};
    }}
    
    QPushButton#start_btn {{
        background-color: {COLOR_ACCENT};
        border: none;
        font-size: 16px;
        padding: 14px 28px;
    }}
    
    QPushButton#start_btn:hover {{
        background-color: {COLOR_ACCENT_HOVER};
    }}
    
    QPushButton#stop_btn {{
        background-color: {COLOR_DANGER};
        border: none;
        font-size: 16px;
        padding: 14px 28px;
    }}
    
    QPushButton#stop_btn:hover {{
        background-color: #DC2626;
    }}

    /* Settings Toggle Buttons */
    QPushButton#toggle_on {{
        background-color: {COLOR_SUCCESS}20;
        border: 1px solid {COLOR_SUCCESS};
        color: {COLOR_SUCCESS};
        border-radius: 16px;
        padding: 8px 18px;
        font-size: 13px;
        font-weight: 600;
    }}
    
    QPushButton#toggle_off {{
        background-color: {COLOR_DANGER}20;
        border: 1px solid {COLOR_DANGER};
        color: {COLOR_DANGER};
        border-radius: 16px;
        padding: 8px 18px;
        font-size: 13px;
        font-weight: 600;
    }}
    
    QListWidget {{
        background-color: {COLOR_BG_INPUT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 16px;
        padding: 12px;
        color: {COLOR_TEXT_PRIMARY};
        outline: none;
        font-size: 14px;
    }}
    
    QListWidget::item {{
        padding: 14px;
        border-radius: 10px;
        margin-bottom: 6px;
        background-color: transparent;
    }}

    QListWidget#proc_list::item {{
        padding: 10px 14px;
    }}
    
    QListWidget::item:selected {{
        background-color: {COLOR_ACCENT}20;
        border: 1px solid {COLOR_ACCENT}50;
        color: {COLOR_TEXT_PRIMARY};
    }}
    
    QListWidget::item:hover {{
        background-color: #1E293B;
    }}
    
    QToolButton {{
        background-color: #1E293B;
        border: 1px solid {COLOR_BORDER};
        border-radius: 10px;
        padding: 10px 14px;
        color: {COLOR_TEXT_PRIMARY};
        font-weight: 500;
        font-size: 12px;
    }}
    
    QToolButton:hover {{
        background-color: #334155;
    }}
    
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background: {COLOR_BORDER};
        min-height: 20px;
        border-radius: 4px;
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
"""
