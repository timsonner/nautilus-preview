# nautilus-preview

Space in Files opens a preview of the selected file. Markdown is rendered, and `r` or the header button switches between that view and the source. Images open in the same window.

This is a Nautilus previewer. It owns the `org.gnome.NautilusPreviewer` bus name that Files already calls, which is the same slot [Sushi](https://gitlab.gnome.org/GNOME/sushi) uses. It is not an Omarchy shell plugin. The [plugin library](https://plugins.omarchy.org/publish.html) only lists Quickshell plugins (`manifest.json`, QML entry points, `omarchy plugin add`). A Nautilus preview cannot pass that check, so this repository is installed with the script below.

## Install

Dependencies:

```sh
omarchy pkg add webkitgtk-6.0 python-cmarkgfm
```

Then:

```sh
./scripts/install.sh
```

Restart Files. Select a file and press Space. Press Space again, or Escape, to close the preview. Up, Down, Left, and Right move the selection in Files.

Keep this and Sushi uninstalled together. Both claim `org.gnome.NautilusPreviewer`, and only one of them can answer Space.

## Markdown and images

`.md`, `.markdown`, and `.mdown` open rendered. The header button is labeled **Raw** in that view and **Rendered** after you switch. `r` toggles the same way. Relative images in the Markdown are loaded from the file's directory. JavaScript and remote `http`/`https` content stay off.

`png`, `jpeg`, `gif`, `webp`, and `bmp` open as images. Other files show the name, type, and size.

## Remove

```sh
./scripts/uninstall.sh
```

Restart Files afterward.
