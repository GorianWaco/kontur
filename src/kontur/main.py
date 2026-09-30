"""Punkt wejścia: okno albo zapis CSS z zapisanej konfiguracji."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kontur",
        description="Kolory, obrys, czcionki i geometria okien GTK. Bez przezroczystości.",
    )
    parser.add_argument("command", nargs="?", choices=("apply", "reset"))
    args = parser.parse_args(argv)

    if args.command == "apply":
        from .apply import apply_saved

        config = apply_saved()
        print(f"Zapisano paletę „{config.preset}” do gtk.css (GTK 3 i GTK 4).")
        return 0
    if args.command == "reset":
        from .apply import reset_overrides

        reset_overrides()
        print("Usunięto blok Kontur z gtk.css. Motyw ikon i kursor wrócił, reszta plików została.")
        return 0

    from .app import run_app

    return run_app()


if __name__ == "__main__":
    sys.exit(main())
