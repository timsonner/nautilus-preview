import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _gtk_ready() -> bool:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gtk

    return bool(Gtk.init_check())


class WindowTests(unittest.TestCase):
    def test_markdown_toggle_image_and_arrows(self) -> None:
        if not _gtk_ready():
            self.skipTest("GTK display is not available")

        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk, Gio, GLib, Gtk

        from nautilus_preview.window import PreviewWindow

        class Harness(Gtk.Application):
            def __init__(self) -> None:
                super().__init__(
                    application_id="org.timsonner.NautilusPreviewHarness",
                    flags=Gio.ApplicationFlags.NON_UNIQUE,
                )
                self.moved = None
                self.error = None

            def move_selection(self, direction: Gtk.DirectionType) -> None:
                self.moved = int(direction)

            def do_activate(self) -> None:
                GLib.idle_add(self._exercise)

            def _exercise(self) -> bool:
                window = None
                try:
                    window = PreviewWindow(self)
                    window.load_file(Gio.File.new_for_path(str(ROOT / "samples" / "demo.md")))
                    if window.visible_page() != "rendered" or window._source_button.get_label() != "Raw":
                        raise AssertionError(f"rendered page not shown: {window.visible_page()}")
                    window._on_key(None, Gdk.KEY_r, 0, Gdk.ModifierType(0))
                    if window.visible_page() != "raw" or "# Preview demo" not in window.raw_text():
                        raise AssertionError("raw markdown was not shown")
                    if "print(1)" not in window.raw_text():
                        raise AssertionError("raw markdown is missing the code sample")
                    window._on_key(None, Gdk.KEY_r, 0, Gdk.ModifierType(0))
                    if window.visible_page() != "rendered" or window._source_button.get_label() != "Raw":
                        raise AssertionError("toggle did not return to rendered markdown")

                    window.load_file(Gio.File.new_for_path(str(ROOT / "samples" / "demo.png")))
                    if window.visible_page() != "image" or window._picture.get_paintable() is None:
                        raise AssertionError("image preview did not load")

                    window.load_file(Gio.File.new_for_path(str(ROOT / "scripts" / "install.sh")))
                    info = window._info.get_text()
                    if window.visible_page() != "info" or "install.sh" not in info or "No preview" not in info:
                        raise AssertionError(f"unsupported file was not explained: {info}")

                    window.load_file(Gio.File.new_for_path(str(ROOT / "README.md")))
                    window._on_key(None, Gdk.KEY_Up, 0, Gdk.ModifierType(0))
                    if self.moved != int(Gtk.DirectionType.UP):
                        raise AssertionError(f"arrow key did not request selection move: {self.moved}")
                except Exception as error:  # noqa: BLE001 - reported after the main loop exits
                    self.error = error
                finally:
                    if window is not None:
                        window.destroy()
                    self.quit()
                return False

        app = Harness()
        status = app.run()
        if app.error is not None:
            raise app.error
        if status not in (0, None):
            self.fail(f"GTK application exited {status}")


if __name__ == "__main__":
    unittest.main()
