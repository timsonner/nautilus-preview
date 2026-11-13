# nautilus-preview

nautilus-preview is the Space previewer for GNOME Files (Nautilus). It owns the `org.gnome.NautilusPreviewer` bus name that Files already calls, renders Markdown, and shows images in the same window. Sushi claims that same name; quit Sushi, or another previewer, so Space opens this one.

## Prerequisites

- An Omarchy session with Python 3 and a user D-Bus session
- PyGObject (`import gi`; Arch package `python-gobject`)
- GTK 4 and WebKitGTK 6.0 (Arch package `webkitgtk-6.0`, which depends on GTK 4)
- `python-cmarkgfm` for GitHub-flavored Markdown

## Install, run, and test

Install the packages, then copy this tree into the user data directory. `scripts/install.sh` writes `~/.local/bin/nautilus-preview` and `org.gnome.NautilusPreviewer.service` under `${XDG_DATA_HOME:-$HOME/.local/share}/dbus-1/services`. The service starts `nautilus-preview --gapplication-service`.

```sh
omarchy pkg add webkitgtk-6.0 python-gobject python-cmarkgfm
./scripts/install.sh
```

Restart Files. Select a file and press Space.

From a checkout, the same process opens one file and keeps the bus name:

```sh
python3 -m nautilus_preview samples/demo.md
```

Run the tests from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

`tests/test_window.py` opens a GTK window and skips when no display is available.

Remove the installed copy, then restart Files:

```sh
./scripts/uninstall.sh
```

## Usage

Press Space or Escape to close the preview. Up, Down, Left, and Right ask Files to move the selection.

`.md`, `.markdown`, and `.mdown` open rendered. The header button is **Raw** in that view and **Rendered** after you switch. `r` toggles the same way. Relative images load from the file's directory. JavaScript stays off, and `http`/`https` responses are ignored.

`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, and `.bmp` open as images. Other local files show the name, content type, and size. A URI with no local path shows the name and "Only local files can be previewed."

`samples/demo.md` and `samples/demo.png` are the fixtures the window test loads.

## Layout

- `nautilus_preview/` — previewer package (`python3 -m nautilus_preview`)
- `data/` — D-Bus service template and `preview.css`
- `scripts/` — `install.sh` and `uninstall.sh`
- `samples/` — `demo.md` and `demo.png`
- `tests/` — `unittest` modules

## License

[MIT](LICENSE)
