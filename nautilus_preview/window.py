"""Preview window for Markdown, images, and a short fallback."""

from __future__ import annotations

import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gdk, Gio, GLib, Gtk, WebKit

from nautilus_preview.render import classify, render_document

_MARKDOWN = "markdown"
_IMAGE = "image"


class PreviewWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="Preview")
        self.set_default_size(840, 640)
        self.file: Gio.File | None = None
        self.kind = "other"
        self._showing_raw = False

        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        self._source_button = Gtk.Button(label="Raw")
        self._source_button.set_visible(False)
        self._source_button.connect("clicked", lambda *_args: self.toggle_source())
        header.pack_end(self._source_button)

        self._stack = Gtk.Stack()
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)
        self.set_child(self._stack)

        self._web = WebKit.WebView()
        settings = self._web.get_settings()
        settings.set_enable_javascript(False)
        settings.set_enable_javascript_markup(False)
        settings.set_allow_file_access_from_file_urls(True)
        self._web.connect("decide-policy", self._on_decide_policy)
        self._allow_next_navigation = False

        self._raw = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            monospace=True,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            left_margin=16,
            right_margin=16,
            top_margin=16,
            bottom_margin=16,
        )
        raw_scroll = Gtk.ScrolledWindow(child=self._raw, hexpand=True, vexpand=True)

        self._picture = Gtk.Picture(
            can_shrink=True,
            content_fit=Gtk.ContentFit.CONTAIN,
            hexpand=True,
            vexpand=True,
        )
        self._info = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        self._info.set_margin_top(24)
        self._info.set_margin_bottom(24)
        self._info.set_margin_start(24)
        self._info.set_margin_end(24)

        self._stack.add_named(self._web, "rendered")
        self._stack.add_named(raw_scroll, "raw")
        self._stack.add_named(self._picture, "image")
        self._stack.add_named(self._info, "info")

        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

    def load_file(self, file: Gio.File) -> None:
        self.file = file
        name = file.get_basename() or file.get_uri()
        self.set_title(name)
        path_text = file.get_path()
        if not path_text or not os.path.isfile(path_text):
            self._show_message(name, "Only local files can be previewed.")
            return

        path = Path(path_text)
        self.kind = classify(path)
        self._showing_raw = False
        self._source_button.set_visible(self.kind == _MARKDOWN)
        try:
            if self.kind == _MARKDOWN:
                self._show_markdown(path)
            elif self.kind == _IMAGE:
                self._show_image(path)
            else:
                self._show_other(path)
        except (OSError, GLib.Error) as error:
            self._show_message(path.name, str(error))

    def toggle_source(self) -> None:
        if self.kind != _MARKDOWN:
            return
        self._showing_raw = not self._showing_raw
        if self._showing_raw:
            self._stack.set_visible_child_name("raw")
            self._source_button.set_label("Rendered")
            self._source_button.set_tooltip_text("Show rendered Markdown (r)")
        else:
            self._stack.set_visible_child_name("rendered")
            self._source_button.set_label("Raw")
            self._source_button.set_tooltip_text("Show the Markdown source (r)")

    def raw_text(self) -> str:
        buffer = self._raw.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

    def visible_page(self) -> str:
        return self._stack.get_visible_child_name() or ""

    def _show_markdown(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        self._raw.get_buffer().set_text(text, -1)
        self._allow_next_navigation = True
        self._web.load_html(render_document(text, path.parent), path.as_uri())
        self._stack.set_visible_child_name("rendered")
        self._source_button.set_label("Raw")
        self._source_button.set_tooltip_text("Show the Markdown source (r)")

    def _show_image(self, path: Path) -> None:
        texture = Gdk.Texture.new_from_filename(str(path))
        self._picture.set_paintable(texture)
        self._stack.set_visible_child_name("image")

    def _show_other(self, path: Path) -> None:
        content_type, _uncertain = Gio.content_type_guess(str(path), None)
        size = _format_size(path.stat().st_size)
        self._show_message(
            path.name,
            f"{content_type or 'unknown'}\n{size}\n\nNo preview for this file type.",
        )

    def _show_message(self, title: str, body: str) -> None:
        self.kind = "other"
        self._source_button.set_visible(False)
        self._info.set_text(f"{title}\n\n{body}")
        self._stack.set_visible_child_name("info")

    def _on_key(self, _controller: Gtk.EventControllerKey, keyval: int, _keycode: int, state: Gdk.ModifierType) -> bool:
        if keyval in (Gdk.KEY_Escape, Gdk.KEY_space):
            self.close()
            return True
        if keyval in (Gdk.KEY_r, Gdk.KEY_R) and not state & Gdk.ModifierType.CONTROL_MASK:
            if self.kind == _MARKDOWN:
                self.toggle_source()
                return True
            return False
        directions = {
            Gdk.KEY_Up: Gtk.DirectionType.UP,
            Gdk.KEY_Down: Gtk.DirectionType.DOWN,
            Gdk.KEY_Left: Gtk.DirectionType.LEFT,
            Gdk.KEY_Right: Gtk.DirectionType.RIGHT,
        }
        direction = directions.get(keyval)
        if direction is None:
            return False
        application = self.get_application()
        move = getattr(application, "move_selection", None)
        if move is not None:
            move(direction)
        return True

    def _on_decide_policy(self, _web: WebKit.WebView, decision: WebKit.PolicyDecision, decision_type: WebKit.PolicyDecisionType) -> bool:
        if decision_type == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
            decision.ignore()
            return True
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            if self._allow_next_navigation:
                self._allow_next_navigation = False
                decision.use()
            else:
                decision.ignore()
            return True
        if decision_type == WebKit.PolicyDecisionType.RESPONSE:
            request = decision.get_request()
            uri = request.get_uri() if request is not None else ""
            if uri.startswith(("http://", "https://")):
                decision.ignore()
            else:
                decision.use()
            return True
        return False


def _format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if unit == "B" or value < 1024:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
