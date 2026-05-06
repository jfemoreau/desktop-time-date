from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFontDatabase
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


def _color_btn(color_str: str) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(52, 24)
    _refresh_btn(btn, color_str)
    return btn


def _refresh_btn(btn: QPushButton, color_str: str):
    c = QColor(color_str)
    if not c.isValid() or c.alpha() == 0:
        btn.setText("none")
        btn.setStyleSheet("background: transparent; border: 1px solid #888; color: #888;")
    else:
        luma = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        fg = "#000" if luma > 140 else "#fff"
        btn.setText("")
        btn.setStyleSheet(
            f"background-color: {c.name(QColor.NameFormat.HexArgb)};"
            f" border: 1px solid #888; color: {fg};"
        )


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Desktop Time & Date — Settings")
        self.setMinimumWidth(460)
        self._colors: dict[str, str] = {}
        self._btns:   dict[str, QPushButton] = {}
        self._build_ui()
        self._load_from_widget()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # Appearance
        ag = QGroupBox("Appearance")
        af = QFormLayout(ag)
        for key, label, default in (
            ("time", "Time color:",         "#FFFFFF"),
            ("day",  "Day of week color:",  "#DDDDDD"),
            ("date", "Date color:",         "#CCCCCC"),
            ("bg",   "Background:",         "#00000000"),
        ):
            btn = _color_btn(default)
            self._btns[key] = btn
            alpha = (key == "bg")
            btn.clicked.connect(lambda _=False, k=key, b=btn, a=alpha: self._pick_color(k, b, a))
            af.addRow(label, btn)
        root.addWidget(ag)

        # Font
        fg = QGroupBox("Font")
        ff = QFormLayout(fg)

        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.addItem("(system default)", "")
        for fam in sorted(QFontDatabase.families()):
            self.font_combo.addItem(fam, fam)
        ff.addRow("Font family:", self.font_combo)

        self.time_size_spin = QSpinBox()
        self.time_size_spin.setRange(6, 300)
        self.time_size_spin.setSuffix(" pt")
        ff.addRow("Time size:", self.time_size_spin)

        self.date_size_spin = QSpinBox()
        self.date_size_spin.setRange(6, 200)
        self.date_size_spin.setSuffix(" pt")
        ff.addRow("Day / Date size:", self.date_size_spin)

        self.bold_check = QCheckBox("Bold")
        ff.addRow("", self.bold_check)
        root.addWidget(fg)

        # Format
        fmtg = QGroupBox("Format")
        fmtf = QFormLayout(fmtg)
        self.h24_check = QCheckBox("24-hour clock")
        self.sec_check = QCheckBox("Show seconds")
        fmtf.addRow("", self.h24_check)
        fmtf.addRow("", self.sec_check)
        root.addWidget(fmtg)

        # Shadow
        shg = QGroupBox("Shadow")
        shf = QFormLayout(shg)
        self.shadow_check = QCheckBox("Enable drop shadow")
        shf.addRow("", self.shadow_check)

        btn = _color_btn("#c0000000")
        self._btns["shadow"] = btn
        btn.clicked.connect(lambda _=False, k="shadow", b=btn: self._pick_color(k, b, True))
        shf.addRow("Shadow color:", btn)

        self.shadow_offset_spin = QSpinBox()
        self.shadow_offset_spin.setRange(0, 20)
        self.shadow_offset_spin.setSuffix(" px")
        shf.addRow("Offset:", self.shadow_offset_spin)
        root.addWidget(shg)

        # Position & Size
        pg = QGroupBox("Position && Size")
        pf = QFormLayout(pg)

        xy_row = QHBoxLayout()
        self.x_spin = QSpinBox(); self.x_spin.setRange(-9999, 9999)
        self.y_spin = QSpinBox(); self.y_spin.setRange(-9999, 9999)
        xy_row.addWidget(QLabel("X:")); xy_row.addWidget(self.x_spin)
        xy_row.addSpacing(12)
        xy_row.addWidget(QLabel("Y:")); xy_row.addWidget(self.y_spin)
        pf.addRow("Position:", xy_row)

        wh_row = QHBoxLayout()
        self.w_spin = QSpinBox(); self.w_spin.setRange(100, 9999)
        self.h_spin = QSpinBox(); self.h_spin.setRange(60,  9999)
        wh_row.addWidget(QLabel("W:")); wh_row.addWidget(self.w_spin)
        wh_row.addSpacing(12)
        wh_row.addWidget(QLabel("H:")); wh_row.addWidget(self.h_spin)
        pf.addRow("Size:", wh_row)
        root.addWidget(pg)

        # Window
        wg = QGroupBox("Window")
        wf = QFormLayout(wg)
        self.top_check = QCheckBox("Always on top")
        wf.addRow("", self.top_check)
        root.addWidget(wg)

        # Buttons
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply)
        root.addWidget(bb)

    # ------------------------------------------------------------------
    # Data flow
    # ------------------------------------------------------------------

    def _load_from_widget(self):
        w = self.parent()
        for key, attr in (("time", "time_color"), ("day", "day_color"),
                          ("date", "date_color"), ("bg",  "bg_color")):
            val = getattr(w, attr)
            self._colors[key] = val
            _refresh_btn(self._btns[key], val)

        fam = w.font_family
        if not fam:
            self.font_combo.setCurrentIndex(0)
        else:
            idx = self.font_combo.findText(fam)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)
            else:
                self.font_combo.setCurrentText(fam)

        self.time_size_spin.setValue(w.time_size)
        self.date_size_spin.setValue(w.date_size)
        self.bold_check.setChecked(w.bold)
        self.h24_check.setChecked(w.format_24h)
        self.sec_check.setChecked(w.show_seconds)
        self.top_check.setChecked(w.always_on_top)

        self._colors["shadow"] = w.shadow_color
        _refresh_btn(self._btns["shadow"], w.shadow_color)
        self.shadow_check.setChecked(w.shadow_enabled)
        self.shadow_offset_spin.setValue(w.shadow_offset)

        geo = w.geometry()
        self.x_spin.setValue(geo.x())
        self.y_spin.setValue(geo.y())
        self.w_spin.setValue(geo.width())
        self.h_spin.setValue(geo.height())

    def _pick_color(self, key: str, btn: QPushButton, alpha: bool):
        initial = QColor(self._colors.get(key, "#ffffff"))
        opts = QColorDialog.ColorDialogOption(0)
        if alpha:
            opts |= QColorDialog.ColorDialogOption.ShowAlphaChannel
        color = QColorDialog.getColor(initial, self, "Choose color", opts)
        if color.isValid():
            fmt = QColor.NameFormat.HexArgb if alpha else QColor.NameFormat.HexRgb
            self._colors[key] = color.name(fmt)
            _refresh_btn(btn, self._colors[key])

    def apply_stay_on_top(self, enabled: bool):
        flags = Qt.WindowType.Dialog
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        self.raise_()
        self.activateWindow()

    def sync_geometry(self, x: int, y: int, w: int, h: int):
        for spin, val in ((self.x_spin, x), (self.y_spin, y),
                          (self.w_spin, w), (self.h_spin, h)):
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)

    def _collect(self) -> dict:
        idx = self.font_combo.currentIndex()
        if idx == 0:
            font_family = ""
        elif idx > 0:
            font_family = self.font_combo.currentData() or self.font_combo.currentText()
        else:
            font_family = self.font_combo.currentText()
        return dict(
            time_color    = self._colors.get("time", "#FFFFFF"),
            day_color     = self._colors.get("day",  "#DDDDDD"),
            date_color    = self._colors.get("date", "#CCCCCC"),
            bg_color      = self._colors.get("bg",   "#00000000"),
            font_family   = font_family,
            time_size     = self.time_size_spin.value(),
            date_size     = self.date_size_spin.value(),
            bold          = self.bold_check.isChecked(),
            format_24h    = self.h24_check.isChecked(),
            show_seconds  = self.sec_check.isChecked(),
            always_on_top  = self.top_check.isChecked(),
            shadow_enabled = self.shadow_check.isChecked(),
            shadow_color   = self._colors.get("shadow", "#c0000000"),
            shadow_offset  = self.shadow_offset_spin.value(),
            x=self.x_spin.value(), y=self.y_spin.value(),
            w=self.w_spin.value(), h=self.h_spin.value(),
        )

    def _apply(self):
        self.parent().apply_settings(**self._collect())

    def _ok(self):
        self._apply()
        self.accept()
