"""Aplikacja Libadwaita."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

from .window import KonturWindow

APP_ID = "pl.gorian.Kontur"


class KonturApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app: Adw.Application) -> None:
        window = self.props.active_window
        if window is None:
            window = KonturWindow(self)
        window.present()


def run_app() -> int:
    app = KonturApp()
    return int(app.run(sys.argv))
