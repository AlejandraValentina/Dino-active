"""Central semantic palette and Qt style rules for the Windows desktop."""

COLORS = {
    "canvas": "#101722",
    "panel": "#152130",
    "panel_deep": "#0c121b",
    "text": "#e5edf6",
    "text_muted": "#9eb7cf",
    "variant": "#43c5f5",
    "baseline": "#f6bd60",
    "valid": "#34d399",
    "warning": "#f6bd60",
    "error": "#fb7185",
}


def stylesheet() -> str:
    c = COLORS
    return f"""
        QMainWindow,QWidget {{ background:{c['canvas']}; color:{c['text']}; font-family:'Segoe UI'; font-size:10pt; }}
        QLabel#title {{font-size:22pt;font-weight:600;color:#f3f8ff;padding:4px 0;}}
        QGroupBox {{border:1px solid #2a3b50;border-radius:8px;margin-top:12px;padding:12px 10px 10px;font-weight:600;}}
        QGroupBox::title {{subcontrol-origin:margin;left:12px;padding:0 5px;color:#91cbed;}}
        QPushButton {{background:#1b293a;border:1px solid #344b65;border-radius:6px;padding:8px 12px;}}
        QPushButton:hover {{background:#263a51;}} QPushButton:disabled {{color:#708296;}}
        QPushButton#primaryAction {{background:#1479ad;border-color:#219bd7;font-weight:600;}}
        QLineEdit,QDoubleSpinBox,QComboBox,QTableWidget,QPlainTextEdit,QListWidget {{background:{c['panel_deep']};border:1px solid #30435a;border-radius:4px;padding:5px;selection-background-color:#17638c;}}
        QHeaderView::section {{background:#26394d;color:#f0f6fc;font-weight:600;padding:7px 5px;border-right:1px solid #3b5067;}}
        QTableWidget {{alternate-background-color:#182536;color:{c['text']};gridline-color:#33465b;}}
        QTableView::item {{color:{c['text']};}}
        QTabBar::tab {{background:#202d3c;color:#d7e2ee;border:1px solid #3a4d63;padding:9px 12px;min-height:22px;}}
        QTabBar::tab:selected {{background:#145579;color:#ffffff;border-color:#42b9ed;}}
        QTabBar::tab:hover {{background:#2b4054;color:#ffffff;}}
        QTabWidget::pane {{border:1px solid #2b3e53;border-radius:5px;top:-1px;background:{c['canvas']};}}
        QTableView::item:alternate {{background:#1b2a3b;color:{c['text']};}}
        QTableView::item:selected {{background:#145579;color:#ffffff;}}
        QHeaderView::section {{min-height:25px;}}
        QLabel#notice {{color:{c['text_muted']};background:#162332;border:1px solid #263e55;border-radius:5px;padding:9px;}}
        QWidget#contextBar {{background:{c['panel']};border-bottom:1px solid #31455b;}}
        QLabel#modeBadge {{background:#4b3514;color:#ffd58a;border:1px solid #76551d;border-radius:8px;padding:4px 9px;font-weight:600;}}
        QGroupBox#inspector {{border:0;border-left:1px solid #2b3b4d;border-radius:0;margin:0;padding:12px;}}
        QStatusBar {{background:#0b1119;color:#9db2c7;}}
        QComboBox,QSpinBox,QDoubleSpinBox {{color:#eff6ff;min-height:24px;}}
        QProgressBar {{background:{c['panel_deep']};border:1px solid #354a61;border-radius:4px;text-align:center;color:#eff6ff;}}
        QProgressBar::chunk {{background:#1479ad;border-radius:3px;}}
        QWidget#simulationStatusStrip {{background:{c['panel']};border-top:1px solid #354b62;}}
        QLabel#metricCard {{background:#152130;border:1px solid #354b62;border-radius:6px;padding:8px;color:#e5edf6;font-weight:600;}}
    """
