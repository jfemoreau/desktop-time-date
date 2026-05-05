#!/bin/bash
set -e

echo "Uninstalling Desktop Time & Date…"

rm -rf  "$HOME/.local/share/desktop-time-date"
rm -f   "$HOME/.local/share/applications/desktop-time-date.desktop"
rm -f   "$HOME/.local/share/icons/hicolor/scalable/apps/desktop-time-date.svg"
rm -f   "$HOME/.config/autostart/desktop-time-date.desktop"

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Done."
