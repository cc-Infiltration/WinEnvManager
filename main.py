"""变量管理器 —— Windows 环境变量管理（深色模式，Material 3 Expressive）。

运行：python main.py（PySide6 原生桌面程序，详见 requirements.txt）
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

import core as app_core
from ui import theme
from ui.app import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("变量管理器")
    app.setApplicationVersion("1.0.0")

    theme.load_material_fonts()
    # 设计稿指定 Roboto；Windows 上通常未安装，回退到系统 Segoe UI
    font = QFont()
    font.setFamilies(["Roboto", "Segoe UI"])
    font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(theme.build_qss())

    app_core.ensure_dirs()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
