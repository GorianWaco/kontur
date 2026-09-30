"""Motywy ikon i kursorów w settings.ini programów GTK.

Kontur dopisuje tylko gtk-icon-theme-name i gtk-cursor-theme-name.
Reszta pliku zostaje. Pasek GNOME tych kluczy nie czyta.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .colors import Appearance, clean_theme_name

ICON_KEY = "gtk-icon-theme-name"
CURSOR_KEY = "gtk-cursor-theme-name"
_KEYS = (ICON_KEY, CURSOR_KEY)


def gtk3_settings_path() -> Path:
    return Path.home() / ".config" / "gtk-3.0" / "settings.ini"


def gtk4_settings_path() -> Path:
    return Path.home() / ".config" / "gtk-4.0" / "settings.ini"


def _roots() -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    candidates = [
        Path.home() / ".icons",
        Path.home() / ".local" / "share" / "icons",
    ]
    data_home = os.environ.get("XDG_DATA_HOME", "").strip()
    if data_home:
        candidates.insert(1, Path(data_home) / "icons")
    data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    for item in data_dirs.split(":"):
        if item.strip():
            candidates.append(Path(item.strip()) / "icons")
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not path.is_dir():
            continue
        seen.add(resolved)
        found.append(path)
    return found


def _index_text(path: Path) -> str:
    index = path / "index.theme"
    if not index.is_file():
        return ""
    try:
        return index.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _icon_section(text: str) -> list[str]:
    lines: list[str] = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            inside = stripped.lower() == "[icon theme]"
            continue
        if inside:
            lines.append(stripped)
    return lines


def _display_name(path: Path, section: list[str]) -> str:
    for line in section:
        if line.lower().startswith("name="):
            name = line.split("=", 1)[1].strip()
            if name:
                return name
    return path.name


def _has_icon_dirs(path: Path, section: list[str]) -> bool:
    for line in section:
        if line.lower().startswith("directories=") and line.split("=", 1)[1].strip():
            return True
    try:
        for child in path.iterdir():
            if not child.is_dir():
                continue
            lowered = child.name.lower()
            if lowered in {"scalable", "symbolic"} or re.fullmatch(r"\d+x\d+(@\d+)?", lowered):
                return True
    except OSError:
        return False
    return False


def _has_cursors(path: Path) -> bool:
    cursors = path / "cursors"
    if not cursors.is_dir():
        return False
    try:
        return any(cursors.iterdir())
    except OSError:
        return False


def _catalog(kind: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    seen: set[str] = set()
    for root in _roots():
        try:
            children = sorted(root.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            continue
        for path in children:
            if not path.is_dir() or path.name in seen or path.name.startswith("."):
                continue
            text = _index_text(path)
            section = _icon_section(text)
            if kind == "icons":
                # Hidden=true chowa Adwaitę na GNOME, a to wciąż właściwy motyw ikon.
                if not section or not _has_icon_dirs(path, section):
                    continue
            elif not _has_cursors(path):
                continue
            theme_id = clean_theme_name(path.name)
            if not theme_id:
                continue
            seen.add(path.name)
            label = _display_name(path, section)
            if label != theme_id:
                label = f"{label} ({theme_id})"
            items.append((theme_id, label))
    items.sort(key=lambda item: item[1].casefold())
    return items


def icon_themes() -> list[tuple[str, str]]:
    return _catalog("icons")


def cursor_themes() -> list[tuple[str, str]]:
    return _catalog("cursors")


def _settings_span(lines: list[str]) -> tuple[int, int] | None:
    start = None
    for index, line in enumerate(lines):
        if line.strip().lower() == "[settings]":
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = index
            break
    return start, end


def setting_value(text: str, key: str) -> str | None:
    lines = text.splitlines()
    span = _settings_span(lines)
    if span is None:
        return None
    start, end = span
    for line in lines[start + 1 : end]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() == key:
            return value.strip()
    return None


def render_settings(text: str, changes: dict[str, str | None]) -> str:
    """Podmienia klucze w [Settings]. None usuwa klucz. Reszta linii zostaje."""
    lines = text.splitlines()
    span = _settings_span(lines)
    if span is None:
        additions = [f"{key}={value}" for key, value in changes.items() if value]
        if not additions:
            return text if text.endswith("\n") or text == "" else text + "\n"
        body = list(lines)
        if body and body[-1] != "":
            body.append("")
        body.append("[Settings]")
        body.extend(additions)
        return "\n".join(body) + "\n"
    start, end = span
    pending = dict(changes)
    section: list[str] = []
    for line in lines[start + 1 : end]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
            section.append(line)
            continue
        name = stripped.split("=", 1)[0].strip()
        if name not in pending:
            section.append(line)
            continue
        value = pending.pop(name)
        if value is not None:
            section.append(f"{name}={value}")
    for key, value in pending.items():
        if value is not None:
            section.append(f"{key}={value}")
    merged = lines[: start + 1] + section + lines[end:]
    rendered = "\n".join(merged)
    if text.endswith("\n") or text == "":
        rendered += "\n"
    return rendered


def _normalize_backup(data: object) -> dict[str, dict[str, str | None]]:
    raw = data if isinstance(data, dict) else {}
    cleaned: dict[str, dict[str, str | None]] = {}
    for slot in ("gtk3", "gtk4"):
        item = raw.get(slot)
        if not isinstance(item, dict):
            continue
        slot_map: dict[str, str | None] = {}
        for key in _KEYS:
            if key not in item:
                continue
            value = item[key]
            slot_map[key] = None if value is None else str(value).strip()
        if slot_map:
            cleaned[slot] = slot_map
    return cleaned


def apply_appearance(
    appearance: Appearance,
    backup: object,
    gtk3: Path | None = None,
    gtk4: Path | None = None,
) -> dict[str, dict[str, str | None]]:
    """Zapisuje motyw. Zwraca kopię zapasową wartości sprzed pierwszej podmiany."""
    chosen = appearance.clamped()
    stored = _normalize_backup(backup)
    targets = (
        ("gtk3", gtk3 or gtk3_settings_path()),
        ("gtk4", gtk4 or gtk4_settings_path()),
    )
    for slot, path in targets:
        try:
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
        except OSError:
            text = ""
        slot_backup = dict(stored.get(slot) or {})
        changes: dict[str, str | None] = {}
        for key, choice in ((ICON_KEY, chosen.icons), (CURSOR_KEY, chosen.cursor)):
            current = setting_value(text, key)
            if choice:
                if key not in slot_backup:
                    slot_backup[key] = current
                if current != choice:
                    changes[key] = choice
                continue
            if key not in slot_backup:
                continue
            previous = slot_backup.pop(key)
            if previous:
                if current != previous:
                    changes[key] = previous
            elif current is not None:
                changes[key] = None
        if changes:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_settings(text, changes), encoding="utf-8")
        if slot_backup:
            stored[slot] = slot_backup
        else:
            stored.pop(slot, None)
    return stored
