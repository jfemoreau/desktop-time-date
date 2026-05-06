import os
import subprocess
import sys

# Wayland forbids apps from setting their own window position.
# Force XWayland (xcb) so move() / setGeometry() work correctly.
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from time_display import TimeDisplay


def _is_dark_mode(app: QApplication) -> bool:
    if app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return True
    try:
        out = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True, text=True, timeout=2,
        ).stdout.strip().lower()
        if "dark" in out:
            return True
        if "light" in out or "default" in out:
            return False
    except Exception:
        pass
    try:
        out = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True, text=True, timeout=2,
        ).stdout.strip().lower()
        if "dark" in out:
            return True
    except Exception:
        pass
    return False


def _build_dark_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(53, 53, 53))
    p.setColor(QPalette.ColorRole.WindowText,       Qt.GlobalColor.white)
    p.setColor(QPalette.ColorRole.Base,             QColor(35, 35, 35))
    p.setColor(QPalette.ColorRole.AlternateBase,    QColor(53, 53, 53))
    p.setColor(QPalette.ColorRole.ToolTipBase,      QColor(25, 25, 25))
    p.setColor(QPalette.ColorRole.ToolTipText,      Qt.GlobalColor.white)
    p.setColor(QPalette.ColorRole.Text,             Qt.GlobalColor.white)
    p.setColor(QPalette.ColorRole.Button,           QColor(53, 53, 53))
    p.setColor(QPalette.ColorRole.ButtonText,       Qt.GlobalColor.white)
    p.setColor(QPalette.ColorRole.BrightText,       Qt.GlobalColor.red)
    p.setColor(QPalette.ColorRole.Link,             QColor(42, 130, 218))
    p.setColor(QPalette.ColorRole.Highlight,        QColor(42, 130, 218))
    p.setColor(QPalette.ColorRole.HighlightedText,  QColor(35, 35, 35))
    dim = QColor(127, 127, 127)
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, dim)
    return p


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DesktopTimeDate")
    app.setOrganizationName("DesktopTimeDate")

    app.setStyle("Fusion")
    if _is_dark_mode(app):
        app.setPalette(_build_dark_palette())
    
    display = TimeDisplay()
    display.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
