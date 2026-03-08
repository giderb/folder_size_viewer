"""Dark Matter UI — color palette, fonts, and application stylesheet."""
from __future__ import annotations
import sys as _sys
from pathlib import Path

from PyQt6.QtGui import QFontDatabase

# ── Color palette ─────────────────────────────────────────────────────────────
VOID          = "#060612"
SURFACE       = "#0d0d1f"
SURFACE_HIGH  = "#12122a"
BORDER        = "#1e1e3f"
BORDER_BRIGHT = "#2d2d5e"
CYAN          = "#00d4ff"
CYAN_DIM      = "#0099bb"
VIOLET        = "#6d28d9"
TEXT          = "#e8e8ff"
TEXT_MID      = "#8888aa"
TEXT_DIM      = "#44445a"

if getattr(_sys, 'frozen', False):
    # PyInstaller onefile: fonts land at _MEIPASS/fonts/
    _FONTS_DIR = Path(_sys._MEIPASS) / "fonts"
else:
    _FONTS_DIR = Path(__file__).parent / "fonts"

_FONT_FILES = {
    "outfit":         "Outfit-Regular.ttf",
    "outfit_medium":  "Outfit-Medium.ttf",
    "jetbrains_mono": "JetBrainsMono-Regular.ttf",
}

_family_cache: dict[str, str] = {}


def load_fonts() -> dict[str, str]:
    """Register bundled TTF files and return a map of key → family name."""
    if _family_cache:
        return _family_cache

    for key, filename in _FONT_FILES.items():
        path = _FONTS_DIR / filename
        if path.exists():
            fid = QFontDatabase.addApplicationFont(str(path))
            if fid >= 0:
                families = QFontDatabase.applicationFontFamilies(fid)
                if families:
                    _family_cache[key] = families[0]
                    continue
        # Fallback: use system fonts
        _family_cache[key] = "Segoe UI" if key.startswith("outfit") else "Consolas"

    return _family_cache


def make_input_style() -> str:
    return f"""
        background: #080818;
        border: 1px solid {BORDER};
        border-radius: 6px;
        color: {TEXT};
        padding: 2px 6px;
    """


def make_button_style(primary: bool = True) -> str:
    if primary:
        return f"""
            QPushButton {{
                background: {CYAN};
                color: {VOID};
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 11pt;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #33ddff;
            }}
            QPushButton:pressed {{
                background: {CYAN_DIM};
            }}
        """
    else:
        return f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_MID};
                border: 1px solid {BORDER_BRIGHT};
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                color: {TEXT};
                border-color: {CYAN};
            }}
            QPushButton:pressed {{
                color: {CYAN};
            }}
        """


APP_STYLESHEET = f"""
/* ── Application-wide base ── */
QWidget {{
    background: {VOID};
    color: {TEXT};
    font-family: "Outfit", "Segoe UI", sans-serif;
    font-size: 12pt;
}}

QMainWindow {{
    background: {VOID};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: {BORDER};
    width: 1px;
}}

/* ── ScrollBars ── */
QScrollBar:vertical {{
    background: {SURFACE};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_BRIGHT};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {SURFACE};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_BRIGHT};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── ToolTip ── */
QToolTip {{
    background: {SURFACE_HIGH};
    color: {TEXT};
    border: 1px solid {BORDER_BRIGHT};
    border-radius: 4px;
    padding: 6px 10px;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 10pt;
}}

/* ── Menu ── */
QMenu {{
    background: {SURFACE_HIGH};
    color: {TEXT};
    border: 1px solid {BORDER_BRIGHT};
    border-radius: 6px;
    padding: 4px;
    font-size: 11pt;
}}
QMenu::item {{
    padding: 6px 22px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {BORDER};
    color: {CYAN};
}}

/* ── Calendar popup ── */
QCalendarWidget {{
    background: {SURFACE};
    color: {TEXT};
}}
QCalendarWidget QAbstractItemView {{
    background: {SURFACE};
    color: {TEXT};
    selection-background-color: {CYAN};
    selection-color: {VOID};
}}
"""
