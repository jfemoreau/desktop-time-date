from datetime import datetime
from enum import IntFlag

from PyQt6.QtCore import Qt, QRect, QPoint, QSettings, QTimer
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

_MARGIN   = 8
_FADE_MS  = 250   # ms for each half of the transition (out then in)
_FADE_FPS = 60


class _Edge(IntFlag):
    NONE   = 0
    LEFT   = 1
    RIGHT  = 2
    TOP    = 4
    BOTTOM = 8


_CURSOR_MAP: dict[_Edge, Qt.CursorShape] = {
    _Edge.LEFT:                  Qt.CursorShape.SizeHorCursor,
    _Edge.RIGHT:                 Qt.CursorShape.SizeHorCursor,
    _Edge.TOP:                   Qt.CursorShape.SizeVerCursor,
    _Edge.BOTTOM:                Qt.CursorShape.SizeVerCursor,
    _Edge.TOP   | _Edge.LEFT:   Qt.CursorShape.SizeBDiagCursor,
    _Edge.BOTTOM | _Edge.RIGHT: Qt.CursorShape.SizeBDiagCursor,
    _Edge.TOP   | _Edge.RIGHT:  Qt.CursorShape.SizeFDiagCursor,
    _Edge.BOTTOM | _Edge.LEFT:  Qt.CursorShape.SizeFDiagCursor,
}


class TimeDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("DesktopTimeDate", "DesktopTimeDate")
        self._settings_dialog = None

        self._drag_edge          = _Edge.NONE
        self._drag_start_global: QPoint | None = None
        self._drag_start_geo:    QRect  | None = None

        self._load_settings()
        self._apply_window_flags()
        self.setMouseTracking(True)

        x = int(self.settings.value("x",      100))
        y = int(self.settings.value("y",      100))
        w = int(self.settings.value("width",  400))
        h = int(self.settings.value("height", 220))
        self._restore_position(x, y, w, h)

        QApplication.instance().screenAdded.connect(self._on_screen_added)

        now = datetime.now()
        self._disp_hours, self._disp_min, self._disp_sec, self._disp_ampm = self._split_time(now)
        self._displayed_day, self._displayed_date = self._make_day_date(now)
        self._pend_min: str | None = None
        self._pend_sec: str | None = None
        self._min_alpha: float = 1.0
        self._sec_alpha: float = 1.0
        self._min_dir: int = 0   # -1 fading out, 0 stable, +1 fading in
        self._sec_dir: int = 0

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start(250)

        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(1000 // _FADE_FPS)
        self._fade_timer.timeout.connect(self._fade_step)

    # ------------------------------------------------------------------
    # Settings load
    # ------------------------------------------------------------------

    def _load_settings(self):
        s = self.settings
        self.time_color    = s.value("time_color",    "#FFFFFF")
        self.day_color     = s.value("day_color",     "#DDDDDD")
        self.date_color    = s.value("date_color",    "#CCCCCC")
        self.bg_color      = s.value("bg_color",      "#00000000")
        self.font_family   = s.value("font_family",   "")
        self.time_size     = int(s.value("time_size",  64))
        self.date_size     = int(s.value("date_size",  28))
        self.bold           = s.value("bold",            True,  type=bool)
        self.format_24h     = s.value("format_24h",      False, type=bool)
        self.show_seconds   = s.value("show_seconds",    True,  type=bool)
        self.always_on_top  = s.value("always_on_top",   True,  type=bool)
        self.shadow_enabled = s.value("shadow_enabled",  True,  type=bool)
        self.shadow_color   = s.value("shadow_color",    "#c0000000")
        self.shadow_offset  = int(s.value("shadow_offset", 2))

    # ------------------------------------------------------------------
    # Window flags
    # ------------------------------------------------------------------

    def _apply_window_flags(self, reshow: bool = False):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus
        if self.always_on_top:
            flags |= Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_X11DoNotAcceptFocus,   True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        if reshow:
            self.show()
            if self._settings_dialog and self._settings_dialog.isVisible():
                self._settings_dialog.apply_stay_on_top(self.always_on_top)

    # ------------------------------------------------------------------
    # Screen-aware position save / restore (KVM / multi-monitor support)
    # ------------------------------------------------------------------

    def _save_geo_settings(self, x: int, y: int, w: int, h: int):
        self.settings.setValue("x",      x)
        self.settings.setValue("y",      y)
        self.settings.setValue("width",  w)
        self.settings.setValue("height", h)
        screen = QApplication.screenAt(QPoint(x, y)) or QApplication.primaryScreen()
        if screen:
            sg = screen.geometry()
            self.settings.setValue("screen_name", screen.name())
            self.settings.setValue("rel_x",       x - sg.left())
            self.settings.setValue("rel_y",       y - sg.top())

    def _restore_position(self, saved_x: int, saved_y: int, w: int, h: int):
        x, y = saved_x, saved_y
        screen_name = self.settings.value("screen_name", "")
        rel_x       = self.settings.value("rel_x",       None)
        rel_y       = self.settings.value("rel_y",       None)
        if screen_name and rel_x is not None and rel_y is not None:
            for s in QApplication.screens():
                if s.name() == screen_name:
                    sg = s.geometry()
                    x  = sg.left() + int(rel_x)
                    y  = sg.top()  + int(rel_y)
                    break
        self.setGeometry(x, y, w, h)

    def _on_screen_added(self, screen):
        screen_name = self.settings.value("screen_name", "")
        if not screen_name or screen.name() != screen_name:
            return
        rel_x = self.settings.value("rel_x", None)
        rel_y = self.settings.value("rel_y", None)
        if rel_x is not None and rel_y is not None:
            sg = screen.geometry()
            self.move(sg.left() + int(rel_x), sg.top() + int(rel_y))

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def _make_font(self, size: int) -> QFont:
        f = QFont(self.font_family) if self.font_family else QFont()
        f.setPointSize(size)
        f.setBold(self.bold)
        return f

    def _split_time(self, now: datetime) -> tuple[str, str, str, str]:
        if self.format_24h:
            return (
                now.strftime("%H:"),
                now.strftime("%M"),
                (":" + now.strftime("%S")) if self.show_seconds else "",
                "",
            )
        else:
            h = now.hour % 12 or 12
            return (
                f"{h}:",
                now.strftime("%M"),
                (":" + now.strftime("%S")) if self.show_seconds else "",
                " " + now.strftime("%p"),
            )

    def _make_day_date(self, now: datetime) -> tuple[str, str]:
        return now.strftime("%A"), now.strftime("%B %-d, %Y")

    def _tick(self):
        now = datetime.now()
        hours, minutes, seconds, ampm = self._split_time(now)
        day_str, date_str = self._make_day_date(now)

        if day_str != self._displayed_day or date_str != self._displayed_date:
            self._displayed_day  = day_str
            self._displayed_date = date_str
            self.update()

        if hours != self._disp_hours or ampm != self._disp_ampm:
            self._disp_hours = hours
            self._disp_ampm  = ampm
            self.update()

        if minutes != self._disp_min and self._pend_min is None:
            self._pend_min = minutes
            self._min_dir  = -1
            if not self._fade_timer.isActive():
                self._fade_timer.start()

        if seconds != self._disp_sec and self._pend_sec is None:
            self._pend_sec = seconds
            self._sec_dir  = -1
            if not self._fade_timer.isActive():
                self._fade_timer.start()

    def _fade_step(self):
        step = 1.0 / (_FADE_MS / 1000 * _FADE_FPS)

        if self._min_dir != 0:
            self._min_alpha += self._min_dir * step
            if self._min_dir == -1 and self._min_alpha <= 0:
                self._min_alpha    = 0.0
                self._disp_min     = self._pend_min
                self._pend_min     = None
                self._min_dir      = 1
            elif self._min_dir == 1 and self._min_alpha >= 1:
                self._min_alpha    = 1.0
                self._min_dir      = 0

        if self._sec_dir != 0:
            self._sec_alpha += self._sec_dir * step
            if self._sec_dir == -1 and self._sec_alpha <= 0:
                self._sec_alpha    = 0.0
                self._disp_sec     = self._pend_sec
                self._pend_sec     = None
                self._sec_dir      = 1
            elif self._sec_dir == 1 and self._sec_alpha >= 1:
                self._sec_alpha    = 1.0
                self._sec_dir      = 0

        if self._min_dir == 0 and self._sec_dir == 0:
            self._fade_timer.stop()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        bg = QColor(self.bg_color)
        if bg.isValid() and bg.alpha() > 0:
            painter.fillRect(self.rect(), bg)

        time_font = self._make_font(self.time_size)
        date_font = self._make_font(self.date_size)
        gap = max(4, self.date_size // 4)

        time_h = QFontMetrics(time_font).height()
        date_h = QFontMetrics(date_font).height()
        block_h = time_h + gap + date_h + gap + date_h
        start_y = (self.height() - block_h) // 2

        y2 = start_y + time_h + gap
        y3 = y2 + date_h + gap

        painter.setFont(time_font)
        self._draw_time_segments(painter, start_y, time_h, time_font)

        painter.setFont(date_font)
        self._draw_text(painter, QRect(0, y2, self.width(), date_h), self._displayed_day,  self.day_color)
        self._draw_text(painter, QRect(0, y3, self.width(), date_h), self._displayed_date, self.date_color)

        if self._is_interactive():
            self._draw_interactive_frame(painter)

        painter.end()

    def _draw_time_segments(self, painter: QPainter, start_y: int, time_h: int, font: QFont):
        fm = QFontMetrics(font)
        segments = [
            (self._disp_hours, 1.0),
            (self._disp_min,   self._min_alpha),
            (self._disp_sec,   self._sec_alpha),
            (self._disp_ampm,  1.0),
        ]
        total_w = sum(fm.horizontalAdvance(t) for t, _ in segments if t)
        x = (self.width() - total_w) // 2
        baseline = start_y + fm.ascent() + (time_h - fm.height()) // 2
        for text, alpha in segments:
            if not text:
                continue
            w = fm.horizontalAdvance(text)
            painter.save()
            painter.setOpacity(alpha)
            if self.shadow_enabled:
                painter.setPen(QColor(self.shadow_color))
                painter.drawText(x + self.shadow_offset, baseline + self.shadow_offset, text)
            painter.setPen(QColor(self.time_color))
            painter.drawText(x, baseline, text)
            painter.restore()
            x += w

    def _draw_text(self, painter: QPainter, rect: QRect, text: str, color_str: str):
        if self.shadow_enabled:
            painter.setPen(QColor(self.shadow_color))
            painter.drawText(rect.translated(self.shadow_offset, self.shadow_offset),
                             Qt.AlignmentFlag.AlignCenter, text)
        painter.setPen(QColor(color_str))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_interactive_frame(self, painter: QPainter):
        painter.save()
        r = self.rect().adjusted(1, 1, -2, -2)

        # Dashed border
        painter.setPen(QPen(QColor("#3b82f6"), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(r)

        # 8 resize handles: corners + edge midpoints
        hs = 4
        cx = r.left() + r.width() // 2
        cy = r.top() + r.height() // 2
        for hx, hy in (
            (r.left(), r.top()),    (cx, r.top()),    (r.right(), r.top()),
            (r.left(), cy),                            (r.right(), cy),
            (r.left(), r.bottom()), (cx, r.bottom()), (r.right(), r.bottom()),
        ):
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            painter.setBrush(QColor("#3b82f6"))
            painter.drawRect(hx - hs, hy - hs, hs * 2, hs * 2)

        painter.restore()

    # ------------------------------------------------------------------
    # Interactive drag / resize (only while settings dialog is open)
    # ------------------------------------------------------------------

    def _is_interactive(self) -> bool:
        return bool(self._settings_dialog and self._settings_dialog.isVisible())

    def _detect_edge(self, pos: QPoint) -> _Edge:
        edge = _Edge.NONE
        r = self.rect()
        if pos.x() <= _MARGIN:
            edge |= _Edge.LEFT
        elif pos.x() >= r.width() - _MARGIN:
            edge |= _Edge.RIGHT
        if pos.y() <= _MARGIN:
            edge |= _Edge.TOP
        elif pos.y() >= r.height() - _MARGIN:
            edge |= _Edge.BOTTOM
        return edge

    def mousePressEvent(self, event):
        if not self._is_interactive() or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._drag_edge         = self._detect_edge(event.position().toPoint())
        self._drag_start_global = event.globalPosition().toPoint()
        self._drag_start_geo    = self.geometry()
        self.grabMouse()

    def mouseMoveEvent(self, event):
        if not self._is_interactive():
            self.unsetCursor()
            super().mouseMoveEvent(event)
            return

        pos = event.position().toPoint()

        if not (event.buttons() & Qt.MouseButton.LeftButton):
            edge = self._detect_edge(pos)
            self.setCursor(_CURSOR_MAP.get(edge, Qt.CursorShape.SizeAllCursor))
            return

        if self._drag_start_global is None:
            return

        delta = event.globalPosition().toPoint() - self._drag_start_global
        geo   = self._drag_start_geo

        if self._drag_edge == _Edge.NONE:
            self.move(geo.topLeft() + delta)
        else:
            new_geo = QRect(geo)
            if self._drag_edge & _Edge.LEFT:
                new_geo.setLeft(min(geo.left() + delta.x(), geo.right() - 100))
            if self._drag_edge & _Edge.RIGHT:
                new_geo.setRight(max(geo.right() + delta.x(), geo.left() + 100))
            if self._drag_edge & _Edge.TOP:
                new_geo.setTop(min(geo.top() + delta.y(), geo.bottom() - 60))
            if self._drag_edge & _Edge.BOTTOM:
                new_geo.setBottom(max(geo.bottom() + delta.y(), geo.top() + 60))
            self.setGeometry(new_geo)

        if self._settings_dialog:
            g = self.geometry()
            self._settings_dialog.sync_geometry(g.x(), g.y(), g.width(), g.height())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.releaseMouse()
            if self._is_interactive():
                g = self.geometry()
                self._save_geo_settings(g.x(), g.y(), g.width(), g.height())
            self._drag_start_global = None
            self._drag_start_geo    = None
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)

    # ------------------------------------------------------------------
    # Apply settings from dialog
    # ------------------------------------------------------------------

    def apply_settings(
        self,
        time_color: str, day_color: str, date_color: str, bg_color: str,
        font_family: str, time_size: int, date_size: int,
        bold: bool, format_24h: bool, show_seconds: bool,
        always_on_top: bool,
        shadow_enabled: bool, shadow_color: str, shadow_offset: int,
        x: int, y: int, w: int, h: int,
    ):
        self.time_color     = time_color
        self.day_color      = day_color
        self.date_color     = date_color
        self.bg_color       = bg_color
        self.font_family    = font_family
        self.time_size      = time_size
        self.date_size      = date_size
        self.bold           = bold
        self.format_24h     = format_24h
        self.show_seconds   = show_seconds
        self.always_on_top  = always_on_top
        self.shadow_enabled = shadow_enabled
        self.shadow_color   = shadow_color
        self.shadow_offset  = shadow_offset

        s = self.settings
        s.setValue("time_color",    time_color)
        s.setValue("day_color",     day_color)
        s.setValue("date_color",    date_color)
        s.setValue("bg_color",      bg_color)
        s.setValue("font_family",   font_family)
        s.setValue("time_size",     time_size)
        s.setValue("date_size",     date_size)
        s.setValue("bold",          bold)
        s.setValue("format_24h",    format_24h)
        s.setValue("show_seconds",  show_seconds)
        s.setValue("always_on_top", always_on_top)
        s.setValue("shadow_enabled",shadow_enabled)
        s.setValue("shadow_color",  shadow_color)
        s.setValue("shadow_offset", shadow_offset)

        self.setGeometry(x, y, w, h)
        self._save_geo_settings(x, y, w, h)
        self._apply_window_flags(reshow=True)

        # Reset fade state so new format strings appear immediately
        self._fade_timer.stop()
        now = datetime.now()
        self._disp_hours, self._disp_min, self._disp_sec, self._disp_ampm = self._split_time(now)
        self._displayed_day, self._displayed_date = self._make_day_date(now)
        self._pend_min  = None
        self._pend_sec  = None
        self._min_alpha = 1.0
        self._sec_alpha = 1.0
        self._min_dir   = 0
        self._sec_dir   = 0
        self.update()

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Settings…", self._open_settings)
        menu.addSeparator()
        menu.addAction("Quit", QApplication.quit)
        menu.exec(event.globalPos())

    def resizeEvent(self, event):
        self.update()
        super().resizeEvent(event)

    def closeEvent(self, event):
        pos, size = self.pos(), self.size()
        self._save_geo_settings(pos.x(), pos.y(), size.width(), size.height())
        super().closeEvent(event)

    def _open_settings(self):
        if self._settings_dialog and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        from settings_dialog import SettingsDialog
        self._settings_dialog = SettingsDialog(self)
        self._settings_dialog.apply_stay_on_top(self.always_on_top)
