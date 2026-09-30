"""Nieprzezroczyste kolory i zakresy geometrii."""

from __future__ import annotations

from dataclasses import dataclass

COLOR_KEYS: tuple[str, ...] = (
    "window_bg",
    "window_fg",
    "view_bg",
    "view_fg",
    "sidebar_bg",
    "sidebar_fg",
    "card_bg",
    "card_fg",
    "dialog_bg",
    "dialog_fg",
    "popover_bg",
    "popover_fg",
    "headerbar_bg",
    "headerbar_fg",
    "headerbar_backdrop_bg",
    "headerbar_backdrop_fg",
    "headerbar_line",
    "accent_bg",
    "accent_fg",
    "focus",
    "border",
    "border_active",
    "border_inactive",
    "shadow",
    "headerbar_shadow_color",
    "scrollbar",
    "scrollbar_trough",
    "input_bg",
    "input_fg",
    "input_border",
    "destructive_bg",
    "destructive_fg",
    "success",
    "warning",
    "error",
)

LIMITS: dict[str, tuple[int, int]] = {
    "radius": (0, 48),
    "headerbar_height": (28, 80),
    "headerbar_padding": (0, 24),
    "headerbar_pad_x": (0, 24),
    "headerbar_pad_y": (0, 24),
    "headerbar_radius": (0, 48),
    "headerbar_line": (0, 8),
    "controls_size": (16, 40),
    "controls_gap": (0, 20),
    "title_size": (0, 28),
    "border_width": (1, 4),
    "shadow_offset": (0, 48),
    "shadow_spread": (0, 32),
    "shadow_blur": (0, 64),
    "shadow_alpha": (0, 100),
    "shadow_alpha_idle": (0, 100),
    "headerbar_shadow_blur": (0, 48),
    "headerbar_shadow_alpha": (0, 100),
    "interface_size": (0, 32),
    "monospace_size": (0, 32),
}

IMAGE_FITS: tuple[str, ...] = ("cover", "contain", "tile", "center")


def parse_hex(value: str) -> str:
    """Zwraca #RRGGBB. Odrzuca kanał alfa inny niż pełne krycie."""
    text = str(value).strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) == 3 and all(c in "0123456789abcdefABCDEF" for c in text):
        text = "".join(c * 2 for c in text)
    if len(text) == 8 and all(c in "0123456789abcdefABCDEF" for c in text):
        if text[6:].lower() != "ff":
            raise ValueError(f"kolor z alfą: #{text}")
        text = text[:6]
    if len(text) != 6 or any(c not in "0123456789abcdefABCDEF" for c in text):
        raise ValueError(f"oczekiwano #RRGGBB, jest: {value!r}")
    return "#" + text.upper()


def hex_from_channels(red: float, green: float, blue: float) -> str:
    def channel(value: float) -> int:
        return max(0, min(255, round(value * 255)))

    return f"#{channel(red):02X}{channel(green):02X}{channel(blue):02X}"


def contrast_fg(color: str) -> str:
    """Czarny albo biały tekst na podanym tle."""
    hex_color = parse_hex(color)
    red = int(hex_color[1:3], 16) / 255
    green = int(hex_color[3:5], 16) / 255
    blue = int(hex_color[5:7], 16) / 255

    def linear(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)
    return "#000000" if luminance > 0.45 else "#FFFFFF"


def clean_theme_name(name: object) -> str:
    """Nazwa motywu ikon albo kursora. Pusta zostawia motyw systemu."""
    text = " ".join(str(name or "").split())
    if not text or len(text) > 80:
        return ""
    if text.startswith("."):
        return ""
    if any(char in text for char in "\n\r\t=#[]{};\"'\\/`"):
        return ""
    return text


def clean_font_family(name: object) -> str:
    """Nazwa rodziny albo pusty napis, gdy ma zostać czcionka systemu.

    Odrzuca znaki, które weszłyby do CSS jako osobna deklaracja.
    """
    text = " ".join(str(name or "").split())
    if not text or len(text) > 80:
        return ""
    if any(char in text for char in "\\\"';{}<>\n\r\t"):
        return ""
    return text


def clamp_int(value: object, low: int, high: int, default: int) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _fit_name(value: object) -> str:
    text = str(value or "cover")
    return text if text in IMAGE_FITS else "cover"


@dataclass
class Backdrop:
    """Obrazki tła. Pusty path znaczy sam kolor."""

    path: str = ""
    fit: str = "cover"
    on_content: bool = True
    header_path: str = ""
    header_fit: str = "cover"
    sidebar_path: str = ""
    sidebar_fit: str = "cover"

    def clamped(self) -> Backdrop:
        return Backdrop(
            path=str(self.path or "").strip(),
            fit=_fit_name(self.fit),
            on_content=bool(self.on_content),
            header_path=str(self.header_path or "").strip(),
            header_fit=_fit_name(self.header_fit),
            sidebar_path=str(self.sidebar_path or "").strip(),
            sidebar_fit=_fit_name(self.sidebar_fit),
        )

    def to_dict(self) -> dict[str, str | bool]:
        item = self.clamped()
        return {
            "path": item.path,
            "fit": item.fit,
            "on_content": item.on_content,
            "header_path": item.header_path,
            "header_fit": item.header_fit,
            "sidebar_path": item.sidebar_path,
            "sidebar_fit": item.sidebar_fit,
        }

    @classmethod
    def from_dict(cls, data: object) -> Backdrop:
        raw = data if isinstance(data, dict) else {}
        return cls(
            path=str(raw.get("path") or ""),
            fit=str(raw.get("fit") or "cover"),
            on_content=bool(raw.get("on_content", True)),
            header_path=str(raw.get("header_path") or ""),
            header_fit=str(raw.get("header_fit") or "cover"),
            sidebar_path=str(raw.get("sidebar_path") or ""),
            sidebar_fit=str(raw.get("sidebar_fit") or "cover"),
        ).clamped()


@dataclass
class Appearance:
    """Motyw ikon i kursorów w programach GTK. Pusta nazwa zostawia system."""

    icons: str = ""
    cursor: str = ""

    def clamped(self) -> Appearance:
        return Appearance(icons=clean_theme_name(self.icons), cursor=clean_theme_name(self.cursor))

    def to_dict(self) -> dict[str, str]:
        item = self.clamped()
        return {"icons": item.icons, "cursor": item.cursor}

    @classmethod
    def from_dict(cls, data: object) -> Appearance:
        raw = data if isinstance(data, dict) else {}
        return cls(
            icons=str(raw.get("icons") or ""),
            cursor=str(raw.get("cursor") or ""),
        ).clamped()


@dataclass
class Fonts:
    """Czcionki okien. Pusta rodzina i rozmiar 0 zostawiają wartość systemu."""

    interface: str = ""
    interface_size: int = 0
    monospace: str = ""
    monospace_size: int = 0
    title: str = ""

    def clamped(self) -> Fonts:
        return Fonts(
            interface=clean_font_family(self.interface),
            interface_size=clamp_int(self.interface_size, *LIMITS["interface_size"], 0),
            monospace=clean_font_family(self.monospace),
            monospace_size=clamp_int(self.monospace_size, *LIMITS["monospace_size"], 0),
            title=clean_font_family(self.title),
        )

    def to_dict(self) -> dict[str, str | int]:
        item = self.clamped()
        return {
            "interface": item.interface,
            "interface_size": item.interface_size,
            "monospace": item.monospace,
            "monospace_size": item.monospace_size,
            "title": item.title,
        }

    @classmethod
    def from_dict(cls, data: object) -> Fonts:
        raw = data if isinstance(data, dict) else {}
        return cls(
            interface=str(raw.get("interface") or ""),
            interface_size=raw.get("interface_size") or 0,
            monospace=str(raw.get("monospace") or ""),
            monospace_size=raw.get("monospace_size") or 0,
            title=str(raw.get("title") or ""),
        ).clamped()


@dataclass
class Geometry:
    radius: int = 15
    headerbar_height: int = 46
    headerbar_padding: int = 6
    headerbar_pad_x: int = 6
    headerbar_pad_y: int = 6
    headerbar_radius: int = 15
    headerbar_line: int = 1
    controls_size: int = 24
    controls_gap: int = 6
    title_size: int = 0
    title_bold: bool = True
    border_width: int = 1
    shadow_enabled: bool = False
    shadow_offset: int = 4
    shadow_spread: int = 0
    shadow_blur: int = 16
    shadow_alpha: int = 45
    shadow_alpha_idle: int = 25
    headerbar_shadow: bool = False
    headerbar_shadow_blur: int = 10
    headerbar_shadow_alpha: int = 40

    def clamped(self) -> Geometry:
        pad_y = clamp_int(self.headerbar_pad_y, *LIMITS["headerbar_pad_y"], 6)
        return Geometry(
            radius=clamp_int(self.radius, *LIMITS["radius"], 15),
            headerbar_height=clamp_int(self.headerbar_height, *LIMITS["headerbar_height"], 46),
            headerbar_padding=pad_y,
            headerbar_pad_x=clamp_int(self.headerbar_pad_x, *LIMITS["headerbar_pad_x"], 6),
            headerbar_pad_y=pad_y,
            headerbar_radius=clamp_int(self.headerbar_radius, *LIMITS["headerbar_radius"], 15),
            headerbar_line=clamp_int(self.headerbar_line, *LIMITS["headerbar_line"], 1),
            controls_size=clamp_int(self.controls_size, *LIMITS["controls_size"], 24),
            controls_gap=clamp_int(self.controls_gap, *LIMITS["controls_gap"], 6),
            title_size=clamp_int(self.title_size, *LIMITS["title_size"], 0),
            title_bold=bool(self.title_bold),
            border_width=clamp_int(self.border_width, *LIMITS["border_width"], 1),
            shadow_enabled=bool(self.shadow_enabled),
            shadow_offset=clamp_int(self.shadow_offset, *LIMITS["shadow_offset"], 4),
            shadow_spread=clamp_int(self.shadow_spread, *LIMITS["shadow_spread"], 0),
            shadow_blur=clamp_int(self.shadow_blur, *LIMITS["shadow_blur"], 16),
            shadow_alpha=clamp_int(self.shadow_alpha, *LIMITS["shadow_alpha"], 45),
            shadow_alpha_idle=clamp_int(self.shadow_alpha_idle, *LIMITS["shadow_alpha_idle"], 25),
            headerbar_shadow=bool(self.headerbar_shadow),
            headerbar_shadow_blur=clamp_int(self.headerbar_shadow_blur, *LIMITS["headerbar_shadow_blur"], 10),
            headerbar_shadow_alpha=clamp_int(self.headerbar_shadow_alpha, *LIMITS["headerbar_shadow_alpha"], 40),
        )

    def to_dict(self) -> dict[str, int | bool]:
        geo = self.clamped()
        return {
            "radius": geo.radius,
            "headerbar_height": geo.headerbar_height,
            "headerbar_padding": geo.headerbar_pad_y,
            "headerbar_pad_x": geo.headerbar_pad_x,
            "headerbar_pad_y": geo.headerbar_pad_y,
            "headerbar_radius": geo.headerbar_radius,
            "headerbar_line": geo.headerbar_line,
            "controls_size": geo.controls_size,
            "controls_gap": geo.controls_gap,
            "title_size": geo.title_size,
            "title_bold": geo.title_bold,
            "border_width": geo.border_width,
            "shadow_enabled": geo.shadow_enabled,
            "shadow_offset": geo.shadow_offset,
            "shadow_spread": geo.shadow_spread,
            "shadow_blur": geo.shadow_blur,
            "shadow_alpha": geo.shadow_alpha,
            "shadow_alpha_idle": geo.shadow_alpha_idle,
            "headerbar_shadow": geo.headerbar_shadow,
            "headerbar_shadow_blur": geo.headerbar_shadow_blur,
            "headerbar_shadow_alpha": geo.headerbar_shadow_alpha,
        }

    @classmethod
    def from_dict(cls, data: object) -> Geometry:
        raw = data if isinstance(data, dict) else {}
        base = cls()
        legacy_pad = clamp_int(
            raw.get("headerbar_padding", base.headerbar_padding),
            *LIMITS["headerbar_padding"],
            base.headerbar_padding,
        )
        pad_x = clamp_int(raw.get("headerbar_pad_x", legacy_pad), *LIMITS["headerbar_pad_x"], legacy_pad)
        pad_y = clamp_int(raw.get("headerbar_pad_y", legacy_pad), *LIMITS["headerbar_pad_y"], legacy_pad)
        radius = clamp_int(raw.get("radius", base.radius), *LIMITS["radius"], base.radius)
        return cls(
            radius=radius,
            headerbar_height=clamp_int(
                raw.get("headerbar_height", base.headerbar_height),
                *LIMITS["headerbar_height"],
                base.headerbar_height,
            ),
            headerbar_padding=pad_y,
            headerbar_pad_x=pad_x,
            headerbar_pad_y=pad_y,
            headerbar_radius=clamp_int(
                raw.get("headerbar_radius", radius),
                *LIMITS["headerbar_radius"],
                radius,
            ),
            headerbar_line=clamp_int(
                raw.get("headerbar_line", base.headerbar_line),
                *LIMITS["headerbar_line"],
                base.headerbar_line,
            ),
            controls_size=clamp_int(
                raw.get("controls_size", base.controls_size),
                *LIMITS["controls_size"],
                base.controls_size,
            ),
            controls_gap=clamp_int(
                raw.get("controls_gap", base.controls_gap),
                *LIMITS["controls_gap"],
                base.controls_gap,
            ),
            title_size=clamp_int(raw.get("title_size", base.title_size), *LIMITS["title_size"], base.title_size),
            title_bold=bool(raw.get("title_bold", base.title_bold)),
            border_width=clamp_int(
                raw.get("border_width", base.border_width),
                *LIMITS["border_width"],
                base.border_width,
            ),
            shadow_enabled=bool(raw.get("shadow_enabled", base.shadow_enabled)),
            shadow_offset=clamp_int(
                raw.get("shadow_offset", base.shadow_offset),
                *LIMITS["shadow_offset"],
                base.shadow_offset,
            ),
            shadow_spread=clamp_int(
                raw.get("shadow_spread", base.shadow_spread),
                *LIMITS["shadow_spread"],
                base.shadow_spread,
            ),
            shadow_blur=clamp_int(raw.get("shadow_blur", base.shadow_blur), *LIMITS["shadow_blur"], base.shadow_blur),
            shadow_alpha=clamp_int(
                raw.get("shadow_alpha", base.shadow_alpha),
                *LIMITS["shadow_alpha"],
                base.shadow_alpha,
            ),
            shadow_alpha_idle=clamp_int(
                raw.get("shadow_alpha_idle", base.shadow_alpha_idle),
                *LIMITS["shadow_alpha_idle"],
                base.shadow_alpha_idle,
            ),
            headerbar_shadow=bool(raw.get("headerbar_shadow", base.headerbar_shadow)),
            headerbar_shadow_blur=clamp_int(
                raw.get("headerbar_shadow_blur", base.headerbar_shadow_blur),
                *LIMITS["headerbar_shadow_blur"],
                base.headerbar_shadow_blur,
            ),
            headerbar_shadow_alpha=clamp_int(
                raw.get("headerbar_shadow_alpha", base.headerbar_shadow_alpha),
                *LIMITS["headerbar_shadow_alpha"],
                base.headerbar_shadow_alpha,
            ),
        ).clamped()


class Palette:
    def __init__(self, values: dict[str, str]):
        cleaned: dict[str, str] = {}
        for key in COLOR_KEYS:
            if key not in values:
                raise KeyError(key)
            cleaned[key] = parse_hex(values[key])
        self.values = cleaned

    def __getitem__(self, key: str) -> str:
        return self.values[key]

    def to_dict(self) -> dict[str, str]:
        return dict(self.values)

    @classmethod
    def from_dict(cls, data: object, fallback: Palette | None = None) -> Palette:
        base = (fallback or default_palette()).to_dict()
        raw = data if isinstance(data, dict) else {}
        merged: dict[str, str] = {}
        for key in COLOR_KEYS:
            if key == "headerbar_shadow_color" and key not in raw and raw.get("headerbar_line"):
                try:
                    merged[key] = parse_hex(str(raw["headerbar_line"]))
                    continue
                except ValueError:
                    pass
            try:
                merged[key] = parse_hex(str(raw.get(key, base[key])))
            except ValueError:
                merged[key] = base[key]
        return cls(merged)


def _palette(overrides: dict[str, str], base: dict[str, str] | None = None) -> Palette:
    values = dict(base or _light())
    values.update(overrides)
    missing = [key for key in COLOR_KEYS if key not in values]
    if missing:
        raise KeyError(", ".join(missing))
    return Palette(values)


def _light() -> dict[str, str]:
    return {
        "window_bg": "#FAFAFA",
        "window_fg": "#1E1E1E",
        "view_bg": "#FFFFFF",
        "view_fg": "#1E1E1E",
        "sidebar_bg": "#EBEBED",
        "sidebar_fg": "#1E1E1E",
        "card_bg": "#FFFFFF",
        "card_fg": "#1E1E1E",
        "dialog_bg": "#FFFFFF",
        "dialog_fg": "#1E1E1E",
        "popover_bg": "#FFFFFF",
        "popover_fg": "#1E1E1E",
        "headerbar_bg": "#FFFFFF",
        "headerbar_fg": "#1E1E1E",
        "headerbar_backdrop_bg": "#F3F3F5",
        "headerbar_backdrop_fg": "#1E1E1E",
        "headerbar_line": "#C7C7C7",
        "accent_bg": "#3584E4",
        "accent_fg": "#FFFFFF",
        "focus": "#3584E4",
        "border": "#C7C7C7",
        "border_active": "#3584E4",
        "border_inactive": "#D6D6D6",
        "shadow": "#000000",
        "headerbar_shadow_color": "#000000",
        "scrollbar": "#B8B8B8",
        "scrollbar_trough": "#E6E6E6",
        "input_bg": "#FFFFFF",
        "input_fg": "#1E1E1E",
        "input_border": "#C7C7C7",
        "destructive_bg": "#E01B24",
        "destructive_fg": "#FFFFFF",
        "success": "#2EC27E",
        "warning": "#E5A50A",
        "error": "#E01B24",
    }


def _dark() -> dict[str, str]:
    light = _light()
    light.update(
        {
            "window_bg": "#222226",
            "window_fg": "#FFFFFF",
            "view_bg": "#1A1A1E",
            "view_fg": "#FFFFFF",
            "sidebar_bg": "#2A2A2E",
            "sidebar_fg": "#FFFFFF",
            "card_bg": "#2E2E32",
            "card_fg": "#FFFFFF",
            "dialog_bg": "#2E2E32",
            "dialog_fg": "#FFFFFF",
            "popover_bg": "#303034",
            "popover_fg": "#FFFFFF",
            "headerbar_bg": "#2E2E32",
            "headerbar_fg": "#FFFFFF",
            "headerbar_backdrop_bg": "#222226",
            "headerbar_backdrop_fg": "#FFFFFF",
            "headerbar_line": "#45454A",
            "accent_bg": "#78AEED",
            "accent_fg": "#000000",
            "focus": "#78AEED",
            "border": "#45454A",
            "border_active": "#78AEED",
            "border_inactive": "#3A3A3E",
            "headerbar_shadow_color": "#000000",
            "scrollbar": "#6E6E73",
            "scrollbar_trough": "#2A2A2E",
            "input_bg": "#1A1A1E",
            "input_fg": "#FFFFFF",
            "input_border": "#45454A",
            "success": "#57E389",
            "warning": "#F8E45C",
            "error": "#FF7B63",
        }
    )
    return light


@dataclass(frozen=True)
class Preset:
    id: str
    title: str
    palette: Palette
    geometry: Geometry


def presets() -> tuple[Preset, ...]:
    light = _light()
    stock = Geometry()
    return (
        Preset("adwaita-light", "preset_light", Palette(light), stock),
        Preset("adwaita-dark", "preset_dark", Palette(_dark()), stock),
        Preset(
            "kontrast",
            "preset_contrast",
            _palette(
                {
                    "window_bg": "#FFFFFF",
                    "window_fg": "#000000",
                    "view_bg": "#FFFFFF",
                    "view_fg": "#000000",
                    "sidebar_bg": "#F2F2F2",
                    "sidebar_fg": "#000000",
                    "card_bg": "#FFFFFF",
                    "card_fg": "#000000",
                    "dialog_bg": "#FFFFFF",
                    "dialog_fg": "#000000",
                    "popover_bg": "#FFFFFF",
                    "popover_fg": "#000000",
                    "headerbar_bg": "#FFFFFF",
                    "headerbar_fg": "#000000",
                    "headerbar_backdrop_bg": "#FFFFFF",
                    "headerbar_backdrop_fg": "#000000",
                    "headerbar_line": "#000000",
                    "accent_bg": "#000000",
                    "accent_fg": "#FFFFFF",
                    "focus": "#000000",
                    "border": "#000000",
                    "border_active": "#000000",
                    "border_inactive": "#4D4D4D",
                    "shadow": "#000000",
                    "scrollbar": "#000000",
                    "scrollbar_trough": "#E0E0E0",
                    "input_bg": "#FFFFFF",
                    "input_fg": "#000000",
                    "input_border": "#000000",
                    "destructive_bg": "#000000",
                    "destructive_fg": "#FFFFFF",
                    "success": "#000000",
                    "warning": "#000000",
                    "error": "#000000",
                }
            ),
            Geometry(
                radius=0,
                headerbar_height=44,
                headerbar_padding=4,
                headerbar_pad_x=4,
                headerbar_pad_y=4,
                headerbar_radius=0,
                headerbar_line=4,
                border_width=4,
                shadow_enabled=False,
                shadow_offset=0,
                shadow_spread=0,
                shadow_blur=0,
                shadow_alpha=100,
                shadow_alpha_idle=100,
            ),
        ),
        Preset(
            "atrament",
            "preset_ink",
            _palette(
                {
                    "window_bg": "#14120E",
                    "window_fg": "#F3EDE2",
                    "view_bg": "#1C1914",
                    "view_fg": "#F3EDE2",
                    "sidebar_bg": "#100E0B",
                    "sidebar_fg": "#F3EDE2",
                    "card_bg": "#242018",
                    "card_fg": "#F3EDE2",
                    "dialog_bg": "#242018",
                    "dialog_fg": "#F3EDE2",
                    "popover_bg": "#242018",
                    "popover_fg": "#F3EDE2",
                    "headerbar_bg": "#1C1914",
                    "headerbar_fg": "#F3EDE2",
                    "headerbar_backdrop_bg": "#100E0B",
                    "headerbar_backdrop_fg": "#F3EDE2",
                    "headerbar_line": "#3A3328",
                    "accent_bg": "#E0A100",
                    "accent_fg": "#14120E",
                    "focus": "#E0A100",
                    "border": "#3A3328",
                    "border_active": "#E0A100",
                    "border_inactive": "#2A241C",
                    "shadow": "#000000",
                    "scrollbar": "#8A7A58",
                    "scrollbar_trough": "#1C1914",
                    "input_bg": "#100E0B",
                    "input_fg": "#F3EDE2",
                    "input_border": "#3A3328",
                    "destructive_bg": "#C01C28",
                    "destructive_fg": "#FFFFFF",
                    "success": "#3D9A6A",
                    "warning": "#E0A100",
                    "error": "#C01C28",
                }
            ),
            Geometry(
                radius=4,
                headerbar_height=46,
                headerbar_padding=6,
                headerbar_pad_x=8,
                headerbar_pad_y=6,
                headerbar_radius=4,
                headerbar_line=2,
                title_bold=True,
                border_width=2,
                shadow_enabled=True,
                shadow_offset=5,
                shadow_spread=0,
                shadow_blur=12,
                shadow_alpha=70,
                shadow_alpha_idle=35,
                headerbar_shadow=True,
                headerbar_shadow_blur=8,
                headerbar_shadow_alpha=45,
            ),
        ),
        _moody_preset(
            "night",
            "preset_night",
            14,
            {
                "window_bg": "#0E141B",
                "window_fg": "#E7EEF6",
                "view_bg": "#121A24",
                "view_fg": "#E7EEF6",
                "sidebar_bg": "#0A1016",
                "sidebar_fg": "#E7EEF6",
                "card_bg": "#182230",
                "card_fg": "#E7EEF6",
                "dialog_bg": "#182230",
                "dialog_fg": "#E7EEF6",
                "popover_bg": "#1C2836",
                "popover_fg": "#E7EEF6",
                "headerbar_bg": "#121A24",
                "headerbar_fg": "#E7EEF6",
                "headerbar_backdrop_bg": "#0A1016",
                "headerbar_backdrop_fg": "#C5D0DC",
                "headerbar_line": "#2A3A4C",
                "accent_bg": "#7EB6FF",
                "accent_fg": "#0E141B",
                "focus": "#7EB6FF",
                "border": "#2A3A4C",
                "border_active": "#7EB6FF",
                "border_inactive": "#1C2834",
                "scrollbar": "#5C738C",
                "scrollbar_trough": "#121A24",
                "input_bg": "#0A1016",
                "input_fg": "#E7EEF6",
                "input_border": "#2A3A4C",
                "destructive_bg": "#E35D6A",
                "destructive_fg": "#FFFFFF",
                "success": "#3DDC97",
                "warning": "#E6C15A",
                "error": "#FF8B7A",
            },
        ),
        _moody_preset(
            "coal",
            "preset_coal",
            6,
            {
                "window_bg": "#161311",
                "window_fg": "#F3EBE3",
                "view_bg": "#1C1815",
                "view_fg": "#F3EBE3",
                "sidebar_bg": "#100E0C",
                "sidebar_fg": "#F3EBE3",
                "card_bg": "#24201C",
                "card_fg": "#F3EBE3",
                "dialog_bg": "#24201C",
                "dialog_fg": "#F3EBE3",
                "popover_bg": "#2A241F",
                "popover_fg": "#F3EBE3",
                "headerbar_bg": "#1C1815",
                "headerbar_fg": "#F3EBE3",
                "headerbar_backdrop_bg": "#100E0C",
                "headerbar_backdrop_fg": "#D9CBBC",
                "headerbar_line": "#3A332C",
                "accent_bg": "#E0A15A",
                "accent_fg": "#161311",
                "focus": "#E0A15A",
                "border": "#3A332C",
                "border_active": "#E0A15A",
                "border_inactive": "#2A241F",
                "scrollbar": "#8A7560",
                "scrollbar_trough": "#1C1815",
                "input_bg": "#100E0C",
                "input_fg": "#F3EBE3",
                "input_border": "#3A332C",
                "destructive_bg": "#D4534A",
                "destructive_fg": "#FFFFFF",
                "success": "#C6A15A",
                "warning": "#E0A15A",
                "error": "#E07A72",
            },
        ),
        _moody_preset(
            "forest",
            "preset_forest",
            16,
            {
                "window_bg": "#0E1612",
                "window_fg": "#E5F2EA",
                "view_bg": "#13201A",
                "view_fg": "#E5F2EA",
                "sidebar_bg": "#0A120E",
                "sidebar_fg": "#E5F2EA",
                "card_bg": "#1A2A22",
                "card_fg": "#E5F2EA",
                "dialog_bg": "#1A2A22",
                "dialog_fg": "#E5F2EA",
                "popover_bg": "#1E3228",
                "popover_fg": "#E5F2EA",
                "headerbar_bg": "#13201A",
                "headerbar_fg": "#E5F2EA",
                "headerbar_backdrop_bg": "#0A120E",
                "headerbar_backdrop_fg": "#C5D9CE",
                "headerbar_line": "#2C4036",
                "accent_bg": "#7DCEA0",
                "accent_fg": "#0E1612",
                "focus": "#7DCEA0",
                "border": "#2C4036",
                "border_active": "#7DCEA0",
                "border_inactive": "#1A2A22",
                "scrollbar": "#5E8A72",
                "scrollbar_trough": "#13201A",
                "input_bg": "#0A120E",
                "input_fg": "#E5F2EA",
                "input_border": "#2C4036",
                "destructive_bg": "#D45D55",
                "destructive_fg": "#FFFFFF",
                "success": "#7DCEA0",
                "warning": "#D6C15A",
                "error": "#E07A72",
            },
        ),
        _moody_preset(
            "plum",
            "preset_plum",
            20,
            {
                "window_bg": "#160E18",
                "window_fg": "#F6E8F4",
                "view_bg": "#1E1222",
                "view_fg": "#F6E8F4",
                "sidebar_bg": "#100A12",
                "sidebar_fg": "#F6E8F4",
                "card_bg": "#28182E",
                "card_fg": "#F6E8F4",
                "dialog_bg": "#28182E",
                "dialog_fg": "#F6E8F4",
                "popover_bg": "#301C36",
                "popover_fg": "#F6E8F4",
                "headerbar_bg": "#1E1222",
                "headerbar_fg": "#F6E8F4",
                "headerbar_backdrop_bg": "#100A12",
                "headerbar_backdrop_fg": "#E0C8DC",
                "headerbar_line": "#4A3050",
                "accent_bg": "#E39AD4",
                "accent_fg": "#160E18",
                "focus": "#E39AD4",
                "border": "#4A3050",
                "border_active": "#E39AD4",
                "border_inactive": "#301C36",
                "scrollbar": "#8A6888",
                "scrollbar_trough": "#1E1222",
                "input_bg": "#100A12",
                "input_fg": "#F6E8F4",
                "input_border": "#4A3050",
                "destructive_bg": "#E35D6A",
                "destructive_fg": "#FFFFFF",
                "success": "#C48AD4",
                "warning": "#E0B45A",
                "error": "#FF8B9A",
            },
        ),
        _moody_preset(
            "storm",
            "preset_storm",
            10,
            {
                "window_bg": "#121418",
                "window_fg": "#E4E8F0",
                "view_bg": "#181C24",
                "view_fg": "#E4E8F0",
                "sidebar_bg": "#0C0E12",
                "sidebar_fg": "#E4E8F0",
                "card_bg": "#222834",
                "card_fg": "#E4E8F0",
                "dialog_bg": "#222834",
                "dialog_fg": "#E4E8F0",
                "popover_bg": "#2A3140",
                "popover_fg": "#E4E8F0",
                "headerbar_bg": "#181C24",
                "headerbar_fg": "#E4E8F0",
                "headerbar_backdrop_bg": "#0C0E12",
                "headerbar_backdrop_fg": "#C5CDD8",
                "headerbar_line": "#343C4C",
                "accent_bg": "#9BB0D0",
                "accent_fg": "#121418",
                "focus": "#9BB0D0",
                "border": "#343C4C",
                "border_active": "#9BB0D0",
                "border_inactive": "#222834",
                "scrollbar": "#6E7C90",
                "scrollbar_trough": "#181C24",
                "input_bg": "#0C0E12",
                "input_fg": "#E4E8F0",
                "input_border": "#343C4C",
                "destructive_bg": "#D4656C",
                "destructive_fg": "#FFFFFF",
                "success": "#8FB4C8",
                "warning": "#D4C48A",
                "error": "#E08A90",
            },
        ),
    )


def _moody_preset(preset_id: str, title_key: str, radius: int, colors: dict[str, str]) -> Preset:
    base = _dark()
    base.update(colors)
    return Preset(
        preset_id,
        title_key,
        Palette(base),
        Geometry(
            radius=radius,
            headerbar_radius=radius,
            shadow_enabled=True,
            shadow_offset=4,
            shadow_blur=18,
            shadow_alpha=55,
            shadow_alpha_idle=28,
        ),
    )


def preset_by_id(preset_id: str) -> Preset | None:
    for preset in presets():
        if preset.id == preset_id:
            return preset
    return None


def default_palette() -> Palette:
    return presets()[0].palette


def default_geometry() -> Geometry:
    return presets()[0].geometry
