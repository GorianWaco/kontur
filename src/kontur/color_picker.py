"""Większe okno koloru. Pole barwy zostaje kwadratem i rośnie z oknem."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, GObject, Gtk  # noqa: E402

from .i18n import t

# Miejsce obok kwadratu: pasek odcienia i przełącznik trybu.
_H_CHROME = 118
# Wiersz próbki i pola hex nad kwadratem.
_V_CHROME = 78
_MIN_PLANE = 460


def _find_plane(widget: Gtk.Widget) -> Gtk.Widget | None:
    if widget.get_css_name() == "plane":
        return widget
    child = widget.get_first_child()
    while child is not None:
        found = _find_plane(child)
        if found is not None:
            return found
        child = child.get_next_sibling()
    return None


def _hide_palette(chooser: Gtk.ColorChooserWidget) -> None:
    box = chooser.get_first_child()
    if box is None:
        return
    child = box.get_first_child()
    while child is not None:
        nxt = child.get_next_sibling()
        if type(child).__name__ != "GtkColorEditor":
            child.set_visible(False)
        child = nxt


class ColorPicker(Adw.Window):
    def __init__(self, parent: Gtk.Window, rgba: Gdk.RGBA, on_pick) -> None:
        super().__init__(
            transient_for=parent,
            modal=True,
            title=t("color_title"),
            destroy_with_parent=True,
        )
        self.set_default_size(860, 760)
        self._on_pick = on_pick
        self._plane: Gtk.Widget | None = None
        self._tick = 0

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        cancel = Gtk.Button(label=t("cancel"))
        cancel.connect("clicked", lambda *_a: self.close())
        choose = Gtk.Button(label=t("choose"))
        choose.add_css_class("suggested-action")
        choose.connect("clicked", self._choose)
        header.pack_start(cancel)
        header.pack_end(choose)
        toolbar.add_top_bar(header)

        self._chooser = Gtk.ColorChooserWidget(show_editor=True, use_alpha=False)
        self._chooser.set_rgba(rgba)
        self._chooser.set_hexpand(True)
        self._chooser.set_vexpand(True)
        self._chooser.set_margin_top(12)
        self._chooser.set_margin_bottom(12)
        self._chooser.set_margin_start(12)
        self._chooser.set_margin_end(12)
        _hide_palette(self._chooser)
        toolbar.set_content(self._chooser)
        self.set_content(toolbar)
        self.connect("map", self._on_map)
        self.connect("close-request", self._on_close)

    def _on_map(self, *_args) -> None:
        self._plane = _find_plane(self._chooser)
        if self._plane is not None:
            self._plane.set_hexpand(False)
            self._plane.set_vexpand(False)
            self._plane.set_halign(Gtk.Align.CENTER)
            self._plane.set_valign(Gtk.Align.CENTER)
        self._tick = self.add_tick_callback(self._refit)

    def _on_close(self, *_args) -> bool:
        if self._tick:
            self.remove_tick_callback(self._tick)
            self._tick = 0
        return False

    def _refit(self, *_args) -> bool:
        plane = self._plane
        if plane is None:
            return GLib.SOURCE_CONTINUE
        width = self._chooser.get_width()
        height = self._chooser.get_height()
        if width < 200 or height < 200:
            return GLib.SOURCE_CONTINUE
        side = min(width - _H_CHROME, height - _V_CHROME)
        side = max(_MIN_PLANE, side)
        current = plane.get_size_request()
        if current.width != side or current.height != side:
            plane.set_size_request(side, side)
        return GLib.SOURCE_CONTINUE

    def _choose(self, *_args) -> None:
        color = self._chooser.get_rgba()
        color.alpha = 1
        self._on_pick(color)
        self.close()


class ColorButton(Gtk.Button):
    """Próbka koloru otwierająca własne okno wyboru."""

    __gtype_name__ = "KonturColorButton"

    def __init__(self) -> None:
        super().__init__(valign=Gtk.Align.CENTER)
        self._rgba = Gdk.RGBA()
        self._rgba.parse("#000000")
        self._rgba.alpha = 1
        self._chip = Gtk.Box()
        self._chip.set_size_request(52, 30)
        self._chip.add_css_class("kontur-color-chip")
        self._style = Gtk.CssProvider()
        self._chip.get_style_context().add_provider(
            self._style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.set_child(self._chip)
        self._paint()
        self.connect("clicked", self._open)

    @GObject.Property(type=GObject.TYPE_PYOBJECT)
    def rgba(self):  # noqa: ANN201
        return self._rgba

    @rgba.setter
    def rgba(self, value: Gdk.RGBA) -> None:
        color = value.copy()
        color.alpha = 1
        if self._same(color):
            return
        self._rgba = color
        self._paint()

    def get_rgba(self) -> Gdk.RGBA:
        return self._rgba.copy()

    def set_rgba(self, value: Gdk.RGBA) -> None:
        self.props.rgba = value

    def _same(self, color: Gdk.RGBA) -> bool:
        return (
            abs(color.red - self._rgba.red) < 0.001
            and abs(color.green - self._rgba.green) < 0.001
            and abs(color.blue - self._rgba.blue) < 0.001
        )

    def _paint(self) -> None:
        red = int(round(self._rgba.red * 255))
        green = int(round(self._rgba.green * 255))
        blue = int(round(self._rgba.blue * 255))
        self._style.load_from_string(
            ".kontur-color-chip {"
            f"background-color: rgb({red} {green} {blue});"
            "border-radius: 6px;"
            "border: 1px solid rgb(127 127 127);"
            "min-width: 52px;"
            "min-height: 30px;"
            "}"
        )

    def _open(self, *_args) -> None:
        root = self.get_root()
        if not isinstance(root, Gtk.Window):
            return
        dialog = ColorPicker(root, self._rgba.copy(), self.set_rgba)
        dialog.present()
