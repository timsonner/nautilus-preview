#!/bin/sh
set -eu

DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

if pgrep -f "python3 -m nautilus_preview" >/dev/null 2>&1; then
  pkill -f "python3 -m nautilus_preview" || true
fi

rm -rf "$DATA_HOME/nautilus-preview"
rm -f "$HOME/.local/bin/nautilus-preview"
rm -f "$DATA_HOME/dbus-1/services/org.gnome.NautilusPreviewer.service"
echo "Removed nautilus-preview."
