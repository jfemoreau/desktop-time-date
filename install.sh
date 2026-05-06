#!/bin/bash
set -e

APP_DIR="$HOME/.local/share/desktop-time-date"
APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

echo "Installing Desktop Time & Date…"

# Verify PyQt6 is available
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo "PyQt6 not found — installing via pip…"
    pip install --user PyQt6
fi

# Copy application files
mkdir -p "$APP_DIR"
cp main.py time_display.py settings_dialog.py "$APP_DIR/"

# Launcher script
cat > "$APP_DIR/desktop-time-date" << EOF
#!/bin/bash
cd "$APP_DIR"
exec python3 main.py "\$@"
EOF
chmod +x "$APP_DIR/desktop-time-date"

# Icon
mkdir -p "$ICON_DIR"
cp icon.svg "$ICON_DIR/desktop-time-date.svg"

# Desktop entry
mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/desktop-time-date.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Desktop Time and Date
GenericName=Clock Widget
Comment=Display a live clock, day of the week, and date as a desktop widget
Exec=$APP_DIR/desktop-time-date
Icon=desktop-time-date
Categories=Utility;Clock;
Keywords=clock;time;date;calendar;desktop;widget;
StartupNotify=false
EOF

# Refresh caches so GNOME picks up the new entry immediately
update-desktop-database "$APPS_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "Done! Search for 'Desktop Time & Date' in GNOME Activities."
echo ""
echo "To start automatically at login, run:"
echo "  cp $APPS_DIR/desktop-time-date.desktop ~/.config/autostart/"
