#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}
DEST="$DATA_HOME/nautilus-preview"
BIN_DIR="$HOME/.local/bin"
SERVICE_DIR="$DATA_HOME/dbus-1/services"
BIN="$BIN_DIR/nautilus-preview"

if pgrep -f "python3 -m nautilus_preview" >/dev/null 2>&1; then
  pkill -f "python3 -m nautilus_preview" || true
  sleep 0.2
fi

rm -rf "$DEST"
install -d "$DEST" "$BIN_DIR" "$SERVICE_DIR"
cp -a "$ROOT/nautilus_preview" "$DEST/nautilus_preview"
cp -a "$ROOT/data" "$DEST/data"
find "$DEST" -type d -name __pycache__ -print0 | xargs -0r rm -rf

cat > "$BIN" << EOF
#!/bin/sh
export PYTHONPATH="$DEST\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m nautilus_preview "\$@"
EOF
chmod 755 "$BIN"

sed "s|@BIN@|$BIN|" "$ROOT/data/org.gnome.NautilusPreviewer.service" > "$SERVICE_DIR/org.gnome.NautilusPreviewer.service"
echo "Installed nautilus-preview. Restart Files, then press Space on a file."
