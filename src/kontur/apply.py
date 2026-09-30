"""Zapis bloku Kontur do gtk.css bez ruszania reszty pliku."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .colors import (
    Appearance,
    Backdrop,
    Fonts,
    Geometry,
    Palette,
    default_geometry,
    default_palette,
    preset_by_id,
)
from .cssgen import BEGIN, remove_block, render_gtk3, render_gtk4, upsert_block
from .i18n import language_codes, t
from .themes import apply_appearance, gtk3_settings_path, gtk4_settings_path

CONFIG_VERSION = 1


def config_path() -> Path:
    return Path.home() / ".config" / "kontur" / "config.json"


def gtk4_path() -> Path:
    return Path.home() / ".config" / "gtk-4.0" / "gtk.css"


def gtk3_path() -> Path:
    return Path.home() / ".config" / "gtk-3.0" / "gtk.css"


class StyleConfig:
    def __init__(
        self,
        preset: str,
        palette: Palette,
        geometry: Geometry,
        backdrop: Backdrop | None = None,
        language: str = "pl",
        fonts: Fonts | None = None,
        appearance: Appearance | None = None,
        appearance_backup: dict | None = None,
    ):
        self.preset = preset
        self.palette = palette
        self.geometry = geometry.clamped()
        self.backdrop = (backdrop or Backdrop()).clamped()
        self.language = language if language in language_codes() else "pl"
        self.fonts = (fonts or Fonts()).clamped()
        self.appearance = (appearance or Appearance()).clamped()
        self.appearance_backup = appearance_backup if isinstance(appearance_backup, dict) else {}

    def to_dict(self) -> dict:
        return {
            "version": CONFIG_VERSION,
            "preset": self.preset,
            "language": self.language,
            "palette": self.palette.to_dict(),
            "geometry": self.geometry.to_dict(),
            "backdrop": self.backdrop.to_dict(),
            "fonts": self.fonts.to_dict(),
            "appearance": self.appearance.to_dict(),
            "appearance_backup": self.appearance_backup,
        }

    @classmethod
    def from_dict(cls, data: object) -> StyleConfig:
        raw = data if isinstance(data, dict) else {}
        preset_id = str(raw.get("preset") or "adwaita-light")
        fallback = preset_by_id(preset_id)
        base_palette = fallback.palette if fallback else default_palette()
        base_geometry = fallback.geometry if fallback else default_geometry()
        palette = Palette.from_dict(raw.get("palette"), base_palette)
        geometry = Geometry.from_dict(raw.get("geometry") or base_geometry.to_dict())
        backdrop = Backdrop.from_dict(raw.get("backdrop"))
        language = str(raw.get("language") or "pl")
        fonts = Fonts.from_dict(raw.get("fonts"))
        appearance = Appearance.from_dict(raw.get("appearance"))
        backup = raw.get("appearance_backup") if isinstance(raw.get("appearance_backup"), dict) else {}
        return cls(preset_id, palette, geometry, backdrop, language, fonts, appearance, backup)


def default_config() -> StyleConfig:
    preset = preset_by_id("adwaita-light")
    assert preset is not None
    return StyleConfig(preset.id, preset.palette, preset.geometry)


def load_config(path: Path | None = None) -> StyleConfig:
    target = path or config_path()
    if not target.is_file():
        return default_config()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_config()
    return StyleConfig.from_dict(data)


def save_config(config: StyleConfig, path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(target, json.dumps(config.to_dict(), indent=2, ensure_ascii=False) + "\n")
    return target


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _backup_once(path: Path, original: str) -> None:
    if BEGIN in original or not original.strip():
        return
    backup = path.with_name(path.name + ".kontur-bak")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")


def _read(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def write_styles(
    config: StyleConfig,
    gtk4: Path | None = None,
    gtk3: Path | None = None,
) -> tuple[Path, Path]:
    path4 = gtk4 or gtk4_path()
    path3 = gtk3 or gtk3_path()
    current4 = _read(path4)
    current3 = _read(path3)
    _backup_once(path4, current4)
    _backup_once(path3, current3)
    _atomic_write(
        path4,
        upsert_block(current4, render_gtk4(config.palette, config.geometry, config.backdrop, config.fonts)),
    )
    _atomic_write(
        path3,
        upsert_block(current3, render_gtk3(config.palette, config.geometry, config.backdrop, config.fonts)),
    )
    return path4, path3


def apply_saved(path: Path | None = None) -> StyleConfig:
    config = load_config(path)
    config.appearance_backup = apply_appearance(config.appearance, config.appearance_backup)
    save_config(config, path)
    write_styles(config)
    return config


def reset_overrides(
    gtk4: Path | None = None,
    gtk3: Path | None = None,
    gtk4_settings: Path | None = None,
    gtk3_settings: Path | None = None,
    config_file: Path | None = None,
) -> StyleConfig:
    """Zdejmuje blok CSS i przywraca motyw ikon oraz kursor sprzed podmiany."""
    reset_styles(gtk4, gtk3)
    config = load_config(config_file)
    apply_appearance(
        Appearance(),
        config.appearance_backup,
        gtk3_settings or gtk3_settings_path(),
        gtk4_settings or gtk4_settings_path(),
    )
    config.appearance = Appearance()
    config.appearance_backup = {}
    save_config(config, config_file)
    return config


def reset_styles(gtk4: Path | None = None, gtk3: Path | None = None) -> tuple[Path, Path]:
    path4 = gtk4 or gtk4_path()
    path3 = gtk3 or gtk3_path()
    if path4.is_file():
        _atomic_write(path4, remove_block(_read(path4)))
    if path3.is_file():
        _atomic_write(path3, remove_block(_read(path3)))
    return path4, path3


def palettes_path() -> Path:
    return config_path().parent / "palettes.json"


def backgrounds_dir() -> Path:
    return config_path().parent / "backgrounds"


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def remember_image(source: str, directory: Path | None = None) -> str:
    """Kopiuje obrazek do konfiguracji Kontura. Zwraca pusty napis, gdy pliku nie ma."""
    file = Path(source)
    if not file.is_file():
        return ""
    payload = file.read_bytes()
    if not payload:
        return ""
    suffix = file.suffix.lower()
    if suffix not in _IMAGE_SUFFIXES:
        suffix = ".img"
    digest = hashlib.sha256(payload).hexdigest()[:20]
    folder = directory or backgrounds_dir()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{digest}{suffix}"
    if not target.exists():
        target.write_bytes(payload)
    return str(target)


def _clean_palette_name(name: str) -> str:
    text = re.sub(r"\s+", " ", name).strip()
    if not text:
        raise ValueError(t("err_name"))
    if len(text) > 40:
        raise ValueError(t("err_name_long"))
    return text


def load_saved_palettes(path: Path | None = None) -> list[dict]:
    target = path or palettes_path()
    if not target.is_file():
        return []
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = data.get("palettes") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    cleaned: list[dict] = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            continue
        cleaned.append(item)
    return cleaned


def save_named_palette(name: str, config: StyleConfig, path: Path | None = None) -> str:
    title = _clean_palette_name(name)
    target = path or palettes_path()
    items = [item for item in load_saved_palettes(target) if str(item.get("name")) != title]
    items.append(
        {
            "name": title,
            "palette": config.palette.to_dict(),
            "geometry": config.geometry.to_dict(),
            "backdrop": config.backdrop.to_dict(),
            "fonts": config.fonts.to_dict(),
        }
    )
    items.sort(key=lambda item: str(item["name"]).casefold())
    target.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(target, json.dumps({"palettes": items}, indent=2, ensure_ascii=False) + "\n")
    return title


def delete_named_palette(name: str, path: Path | None = None) -> bool:
    title = _clean_palette_name(name)
    target = path or palettes_path()
    items = load_saved_palettes(target)
    kept = [item for item in items if str(item.get("name")) != title]
    if len(kept) == len(items):
        return False
    _atomic_write(target, json.dumps({"palettes": kept}, indent=2, ensure_ascii=False) + "\n")
    return True


def saved_palette(name: str, path: Path | None = None) -> StyleConfig | None:
    title = name.strip()
    for item in load_saved_palettes(path):
        if str(item.get("name")) != title:
            continue
        return StyleConfig.from_dict(
            {
                "preset": "custom",
                "palette": item.get("palette"),
                "geometry": item.get("geometry"),
                "backdrop": item.get("backdrop"),
                "fonts": item.get("fonts"),
            }
        )
    return None


def styles_installed(gtk4: Path | None = None, gtk3: Path | None = None) -> bool:
    return BEGIN in _read(gtk4 or gtk4_path()) or BEGIN in _read(gtk3 or gtk3_path())
