"""D-Bus previewer service Nautilus calls when Space is pressed."""

from __future__ import annotations

import os
import sys

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib, Gtk

from nautilus_preview.window import PreviewWindow

APP_ID = "org.timsonner.NautilusPreview"
PREVIEWER_NAME = "org.gnome.NautilusPreviewer"
PREVIEWER_PATH = "/org/gnome/NautilusPreviewer"
PREVIEWER_IFACE = "org.gnome.NautilusPreviewer2"

# Nautilus 50 unpacks SelectionEvent as (u). Sushi's XML still says q, but its
# running code emits u, and that is the body Files actually reads.
_INTROSPECTION = """
<node>
  <interface name="org.gnome.NautilusPreviewer2">
    <method name="ShowFile">
      <arg type="s" name="uri" direction="in"/>
      <arg type="s" name="windowHandle" direction="in"/>
      <arg type="b" name="closeIfAlreadyShown" direction="in"/>
      <arg type="s" name="activationToken" direction="in"/>
    </method>
    <method name="Close"/>
    <property name="ParentHandle" type="s" access="read"/>
    <property name="Visible" type="b" access="read"/>
    <signal name="SelectionEvent">
      <arg type="u" name="direction"/>
    </signal>
  </interface>
</node>
"""


def _owner_is_this_previewer(connection: Gio.DBusConnection | None) -> bool:
    if connection is None:
        return False
    try:
        owner = connection.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "GetNameOwner",
            GLib.Variant("(s)", (PREVIEWER_NAME,)),
            GLib.VariantType("(s)"),
            Gio.DBusCallFlags.NONE,
            1000,
            None,
        ).unpack()[0]
        pid = connection.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "GetConnectionUnixProcessID",
            GLib.Variant("(s)", (owner,)),
            GLib.VariantType("(u)"),
            Gio.DBusCallFlags.NONE,
            1000,
            None,
        ).unpack()[0]
    except GLib.Error:
        return False
    try:
        command = open(f"/proc/{pid}/cmdline", "rb").read()
    except OSError:
        return False
    return b"nautilus_preview" in command or b"nautilus-preview" in command


class PreviewApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self._window: PreviewWindow | None = None
        self._connection: Gio.DBusConnection | None = None
        self._node_info = Gio.DBusNodeInfo.new_for_xml(_INTROSPECTION)
        self._registration_id = 0
        self._owner_id = 0
        self._visible = False
        self._parent_handle = ""
        self._releasing = False

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        self.hold()
        self._owner_id = Gio.bus_own_name(
            Gio.BusType.SESSION,
            PREVIEWER_NAME,
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus_acquired,
            self._on_name_acquired,
            self._on_name_lost,
        )

    def do_shutdown(self) -> None:
        self._releasing = True
        if self._connection is not None and self._registration_id:
            self._connection.unregister_object(self._registration_id)
            self._registration_id = 0
        if self._owner_id:
            Gio.bus_unown_name(self._owner_id)
            self._owner_id = 0
        Gtk.Application.do_shutdown(self)

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        args = command_line.get_arguments()[1:]
        if args:
            cwd = command_line.get_cwd() or os.getcwd()
            uri = GLib.filename_to_uri(GLib.canonicalize_filename(args[0], cwd), None)
            self.show_file(uri, "", False, "")
        return 0

    def show_file(self, uri: str, window_handle: str, close_if_already_shown: bool, activation_token: str) -> None:
        file = Gio.File.new_for_uri(uri)
        window = self._window
        if (
            close_if_already_shown
            and window is not None
            and window.file is not None
            and window.file.equal(file)
        ):
            window.close()
            return

        window = self._ensure_window()
        if activation_token:
            set_startup_id = getattr(window, "set_startup_id", None)
            if set_startup_id is not None:
                set_startup_id(activation_token)
        if window_handle:
            self._parent_handle = window_handle
            self._notify_property("ParentHandle", GLib.Variant("s", window_handle))
        self._set_visible(True)
        window.load_file(file)
        window.present()

    def move_selection(self, direction: Gtk.DirectionType) -> None:
        if self._connection is None:
            return
        self._connection.emit_signal(
            None,
            PREVIEWER_PATH,
            PREVIEWER_IFACE,
            "SelectionEvent",
            GLib.Variant("(u)", (int(direction),)),
        )

    def _ensure_window(self) -> PreviewWindow:
        if self._window is None:
            self._window = PreviewWindow(self)
            self._window.connect("close-request", self._on_close_request)
        return self._window

    def _on_close_request(self, window: PreviewWindow) -> bool:
        # GTK keeps the widget alive while we hold it, so the destroy signal
        # never arrives. Drop the reference here, before the default handler
        # finishes closing the surface.
        if self._window is window:
            self._window = None
        self._set_visible(False)
        return False

    def _close_window(self) -> None:
        if self._window is not None:
            self._window.close()

    def _on_bus_acquired(self, connection: Gio.DBusConnection, _name: str) -> None:
        self._connection = connection
        try:
            self._registration_id = connection.register_object(
                PREVIEWER_PATH,
                self._node_info.interfaces[0],
                self._on_method_call,
                self._on_get_property,
                None,
            )
        except GLib.Error as error:
            print(f"nautilus-preview: failed to export {PREVIEWER_PATH}: {error}", file=sys.stderr)

    def _on_name_acquired(self, _connection: Gio.DBusConnection, _name: str) -> None:
        return

    def _on_name_lost(self, connection: Gio.DBusConnection | None, _name: str) -> None:
        if self._releasing or _owner_is_this_previewer(connection):
            return
        print(
            "nautilus-preview: org.gnome.NautilusPreviewer is owned by another program. "
            "Quit Sushi, or another previewer, so Space can open this one.",
            file=sys.stderr,
        )

    def _on_method_call(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _object_path: str,
        _interface_name: str,
        method_name: str,
        parameters: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        try:
            if method_name == "ShowFile":
                uri, handle, close, token = parameters.unpack()
                self.show_file(uri, handle, bool(close), token or "")
                invocation.return_value(None)
            elif method_name == "Close":
                self._close_window()
                invocation.return_value(None)
            else:
                invocation.return_error_literal(
                    Gio.dbus_error_quark(),
                    Gio.DBusError.UNKNOWN_METHOD,
                    method_name,
                )
        except Exception as error:  # noqa: BLE001 - report any failure back to Nautilus
            invocation.return_error_literal(
                Gio.dbus_error_quark(),
                Gio.DBusError.FAILED,
                str(error),
            )

    def _on_get_property(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _object_path: str,
        _interface_name: str,
        property_name: str,
    ) -> GLib.Variant:
        if property_name == "Visible":
            return GLib.Variant("b", self._visible)
        if property_name == "ParentHandle":
            return GLib.Variant("s", self._parent_handle)
        return GLib.Variant("b", False)

    def _set_visible(self, visible: bool) -> None:
        if visible == self._visible:
            return
        self._visible = visible
        self._notify_property("Visible", GLib.Variant("b", visible))

    def _notify_property(self, name: str, value: GLib.Variant) -> None:
        if self._connection is None:
            return
        changed = GLib.Variant("a{sv}", {name: value})
        body = GLib.Variant.new_tuple(
            GLib.Variant("s", PREVIEWER_IFACE),
            changed,
            GLib.Variant("as", []),
        )
        self._connection.emit_signal(
            None,
            PREVIEWER_PATH,
            "org.freedesktop.DBus.Properties",
            "PropertiesChanged",
            body,
        )


def main() -> int:
    try:
        app = PreviewApplication()
    except (ModuleNotFoundError, ValueError) as error:
        print(f"nautilus-preview: {error}", file=sys.stderr)
        print("Install dependencies with: omarchy pkg add webkitgtk-6.0 python-cmarkgfm", file=sys.stderr)
        return 1
    return app.run(sys.argv)
