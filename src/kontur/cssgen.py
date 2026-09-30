"""Szablony CSS dla GTK 3, GTK 4 i Libadwaita.

Kolory kontrolek zostają #RRGGBB. Cień okna i cień paska tytułu
mają rozmycie oraz kanał alfa. Tło okna może dostać obrazek.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from .colors import Backdrop, Fonts, Geometry, Palette, clean_font_family, contrast_fg, parse_hex

BEGIN = "/* kontur:begin */"
END = "/* kontur:end */"


def _rule(selector: str, declarations: list[str]) -> str:
    body = "\n".join(f"  {item};" for item in declarations)
    return f"{selector} {{\n{body}\n}}\n"


def shadow_rgba(color: str, alpha_percent: int) -> str:
    """Kanał alfa cienia: 0 to nic, 100 to pełne krycie koloru."""
    hex_color = parse_hex(color)
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    alpha = max(0, min(100, int(alpha_percent))) / 100
    return f"rgb({red} {green} {blue} / {alpha:.2f})"


def css_image_url(path: str) -> str | None:
    text = str(path or "").strip()
    if not text:
        return None
    file = Path(text)
    if not file.is_file():
        return None
    quoted = quote(str(file.resolve()), safe="/")
    return f'url("file://{quoted}")'


def _image_declarations(backdrop: Backdrop) -> list[str] | None:
    return _fitted_image(backdrop.path, backdrop.fit)


def _fitted_image(path: str, fit: str) -> list[str] | None:
    uri = css_image_url(path)
    if uri is None:
        return None
    fit = fit if fit in {"cover", "contain", "tile", "center"} else "cover"
    if fit == "contain":
        size, repeat, position = "contain", "no-repeat", "center center"
    elif fit == "tile":
        size, repeat, position = "auto", "repeat", "left top"
    elif fit == "center":
        size, repeat, position = "auto", "no-repeat", "center center"
    else:
        size, repeat, position = "cover", "no-repeat", "center center"
    return [
        f"background-image: {uri}",
        f"background-size: {size}",
        f"background-repeat: {repeat}",
        f"background-position: {position}",
    ]


def _layer(path: str, fit: str) -> list[str]:
    return _fitted_image(path, fit) or ["background-image: none"]


def _shadow(geometry: Geometry, border: str, shadow: str, alpha: int) -> str:
    parts = [f"0 0 0 {geometry.border_width}px {parse_hex(border)}"]
    if geometry.shadow_enabled:
        parts.append(
            f"{geometry.shadow_offset}px {geometry.shadow_offset}px {geometry.shadow_blur}px "
            f"{geometry.shadow_spread}px {shadow_rgba(shadow, alpha)}"
        )
    return ", ".join(parts)


def _headerbar_shadow(geometry: Geometry, color: str) -> str:
    if not geometry.headerbar_shadow:
        return "none"
    return f"0 4px {geometry.headerbar_shadow_blur}px {shadow_rgba(color, geometry.headerbar_shadow_alpha)}"


def _extent(geometry: Geometry) -> int:
    extra = 0
    if geometry.shadow_enabled:
        extra = geometry.shadow_offset + geometry.shadow_spread + geometry.shadow_blur
    return geometry.border_width + extra


def render_gtk4(
    palette: Palette,
    geometry: Geometry,
    backdrop: Backdrop | None = None,
    fonts: Fonts | None = None,
) -> str:
    p = palette
    g = geometry.clamped()
    chosen = (fonts or Fonts()).clamped()
    image = (backdrop or Backdrop()).clamped()
    image_decls = _image_declarations(image)
    success_fg = contrast_fg(p["success"])
    warning_fg = contrast_fg(p["warning"])
    error_fg = contrast_fg(p["error"])
    floating = (
        "window.csd:not(.maximized):not(.fullscreen):not(.tiled)"
        ":not(.tiled-top):not(.tiled-bottom):not(.tiled-left):not(.tiled-right)"
    )
    variables = [
        f"--window-bg-color: {p['window_bg']}",
        f"--window-fg-color: {p['window_fg']}",
        f"--view-bg-color: {p['view_bg']}",
        f"--view-fg-color: {p['view_fg']}",
        f"--sidebar-bg-color: {p['sidebar_bg']}",
        f"--sidebar-fg-color: {p['sidebar_fg']}",
        f"--sidebar-border-color: {p['border']}",
        f"--sidebar-backdrop-color: {p['sidebar_bg']}",
        f"--sidebar-shade-color: {p['border']}",
        f"--secondary-sidebar-bg-color: {p['sidebar_bg']}",
        f"--secondary-sidebar-fg-color: {p['sidebar_fg']}",
        f"--secondary-sidebar-border-color: {p['border']}",
        f"--secondary-sidebar-backdrop-color: {p['sidebar_bg']}",
        f"--secondary-sidebar-shade-color: {p['border']}",
        f"--headerbar-bg-color: {p['headerbar_bg']}",
        f"--headerbar-fg-color: {p['headerbar_fg']}",
        f"--headerbar-border-color: {p['headerbar_line']}",
        f"--headerbar-backdrop-color: {p['headerbar_backdrop_bg']}",
        f"--headerbar-shade-color: {p['headerbar_line']}",
        f"--headerbar-darker-shade-color: {p['headerbar_line']}",
        f"--card-bg-color: {p['card_bg']}",
        f"--card-fg-color: {p['card_fg']}",
        f"--card-shade-color: {p['border']}",
        f"--dialog-bg-color: {p['dialog_bg']}",
        f"--dialog-fg-color: {p['dialog_fg']}",
        f"--popover-bg-color: {p['popover_bg']}",
        f"--popover-fg-color: {p['popover_fg']}",
        f"--popover-shade-color: {p['border']}",
        f"--accent-bg-color: {p['accent_bg']}",
        f"--accent-fg-color: {p['accent_fg']}",
        f"--accent-color: {p['accent_bg']}",
        f"--destructive-bg-color: {p['destructive_bg']}",
        f"--destructive-fg-color: {p['destructive_fg']}",
        f"--destructive-color: {p['destructive_bg']}",
        f"--success-bg-color: {p['success']}",
        f"--success-fg-color: {success_fg}",
        f"--success-color: {p['success']}",
        f"--warning-bg-color: {p['warning']}",
        f"--warning-fg-color: {warning_fg}",
        f"--warning-color: {p['warning']}",
        f"--error-bg-color: {p['error']}",
        f"--error-fg-color: {error_fg}",
        f"--error-color: {p['error']}",
        f"--shade-color: {p['border']}",
        f"--border-color: {p['border']}",
        f"--scrollbar-outline-color: {p['border']}",
        f"--overview-bg-color: {p['window_bg']}",
        f"--overview-fg-color: {p['window_fg']}",
        f"--thumbnail-bg-color: {p['card_bg']}",
        f"--thumbnail-fg-color: {p['card_fg']}",
        f"--active-toggle-bg-color: {p['accent_bg']}",
        f"--active-toggle-fg-color: {p['accent_fg']}",
        f"--standalone-color: {p['window_fg']}",
        f"--window-radius: {g.radius}px",
        "--border-opacity: 1",
    ]
    card_radius = min(g.radius, 16)
    parts = [
        "/* Kontur: nieprzezroczyste kolory i geometria okien GTK 4 / Libadwaita. */",
        _rule("window", variables + [
            f"background-color: {p['window_bg']}",
            f"color: {p['window_fg']}",
            *(image_decls or ["background-image: none"]),
        ]),
        _rule(floating, [
            f"border-radius: {g.radius}px",
            "outline: none",
            f"box-shadow: {_shadow(g, p['border_active'], p['shadow'], g.shadow_alpha)}",
        ]),
        _rule(f"{floating}:backdrop", [
            "outline: none",
            f"box-shadow: {_shadow(g, p['border_inactive'], p['shadow'], g.shadow_alpha_idle)}",
        ]),
        _rule(
            "window.csd.maximized, window.csd.fullscreen, window.csd.tiled, "
            "window.csd.tiled-top, window.csd.tiled-bottom, window.csd.tiled-left, "
            "window.csd.tiled-right",
            [
                "--window-radius: 0px",
                "border-radius: 0",
                "outline: none",
                "box-shadow: none",
            ],
        ),
        _rule("window.ssd", [
            "outline: none",
            f"box-shadow: 0 0 0 {g.border_width}px {p['border_active']}",
        ]),
        _rule("window.ssd:backdrop", [
            f"box-shadow: 0 0 0 {g.border_width}px {p['border_inactive']}",
        ]),
        _rule("window headerbar, window headerbar.titlebar, window .titlebar headerbar", [
            f"min-height: {g.headerbar_height}px",
            f"background-color: {p['headerbar_bg']}",
            f"color: {p['headerbar_fg']}",
            *_layer(image.header_path, image.header_fit),
            "filter: none",
            f"border-radius: {g.headerbar_radius}px {g.headerbar_radius}px 0 0",
            _header_line(g, p["headerbar_line"]),
            f"box-shadow: {_headerbar_shadow(g, p['headerbar_shadow_color'])}",
        ]),
        _rule(
            "window.maximized headerbar, window.fullscreen headerbar, window.tiled headerbar",
            ["border-radius: 0"],
        ),
        _rule("window headerbar:backdrop, window .titlebar:backdrop", [
            f"background-color: {p['headerbar_backdrop_bg']}",
            f"color: {p['headerbar_backdrop_fg']}",
            "filter: none",
            f"border-bottom-color: {p['border_inactive']}",
        ]),
        _rule("window headerbar:backdrop > windowhandle", ["filter: none"]),
        _rule("window headerbar > windowhandle > box", [
            f"padding: {g.headerbar_pad_y}px {g.headerbar_pad_x}px",
        ]),
        _rule("window headerbar .title, window windowtitle .title", _title_declarations(g, chosen)),
        _rule("window windowcontrols", [f"border-spacing: {g.controls_gap}px"]),
        _rule("window windowcontrols > button", [
            f"min-width: {g.controls_size}px",
            f"min-height: {g.controls_size}px",
        ]),
        _rule("window:not(.ssd-frame) > .titlebar:not(.flat)", [
            f"box-shadow: {_headerbar_shadow(g, p['headerbar_shadow_color'])}",
        ]),
        _rule(".sidebar, .navigation-sidebar, .sidebar-pane", [
            f"background-color: {p['sidebar_bg']}",
            f"color: {p['sidebar_fg']}",
            *_layer(image.sidebar_path, image.sidebar_fit),
        ]),
        _rule(".card", [
            f"background-color: {p['card_bg']}",
            f"color: {p['card_fg']}",
            f"border: {g.border_width}px solid {p['border']}",
            f"border-radius: {card_radius}px",
            "box-shadow: none",
        ]),
        _rule("window.dialog, window.messagedialog", [
            f"background-color: {p['dialog_bg']}",
            f"color: {p['dialog_fg']}",
        ]),
        _rule("popover, popover.background, menu", [
            f"background-color: {p['popover_bg']}",
            f"color: {p['popover_fg']}",
            f"border: 1px solid {p['border']}",
            "box-shadow: none",
            "opacity: 1",
        ]),
        _rule("tooltip", [
            f"background-color: {p['window_fg']}",
            f"color: {p['window_bg']}",
            f"border: 1px solid {p['border']}",
            "opacity: 1",
        ]),
        _rule("entry, text, textview, spinbutton", [
            f"background-color: {p['input_bg']}",
            f"color: {p['input_fg']}",
            f"caret-color: {p['input_fg']}",
            f"border: 1px solid {p['input_border']}",
        ]),
        _rule("entry:focus, entry:focus-within, textview:focus-within, spinbutton:focus-within", [
            f"border-color: {p['focus']}",
            f"outline: 2px solid {p['focus']}",
            "outline-offset: -2px",
        ]),
        _rule("entry selection, text selection, textview selection, label selection", [
            f"background-color: {p['accent_bg']}",
            f"color: {p['accent_fg']}",
        ]),
        _rule(
            "button:not(.flat):not(.image-button):not(.suggested-action):not(.destructive-action)",
            [
                f"background-color: {p['card_bg']}",
                f"color: {p['card_fg']}",
                "background-image: none",
                f"border: 1px solid {p['border']}",
                "box-shadow: none",
            ],
        ),
        _rule("button.suggested-action, button.suggested-action:hover, button.suggested-action:active", [
            f"background-color: {p['accent_bg']}",
            f"color: {p['accent_fg']}",
            f"border-color: {p['accent_bg']}",
            "background-image: none",
            "box-shadow: none",
        ]),
        _rule("button.destructive-action, button.destructive-action:hover, button.destructive-action:active", [
            f"background-color: {p['destructive_bg']}",
            f"color: {p['destructive_fg']}",
            f"border-color: {p['destructive_bg']}",
            "background-image: none",
            "box-shadow: none",
        ]),
        _rule("button.toggle:checked", [
            f"background-color: {p['accent_bg']}",
            f"color: {p['accent_fg']}",
            f"border-color: {p['accent_bg']}",
        ]),
        _rule("button:focus-visible, entry:focus-visible, row:focus-visible, switch:focus-visible, scale:focus-visible", [
            f"outline: 2px solid {p['focus']}",
            "outline-offset: -2px",
        ]),
        _rule("switch", [
            f"background-color: {p['scrollbar_trough']}",
            f"border: 1px solid {p['border']}",
            f"color: {p['window_fg']}",
        ]),
        _rule("switch:checked", [
            f"background-color: {p['accent_bg']}",
            f"border-color: {p['accent_bg']}",
            f"color: {p['accent_fg']}",
        ]),
        _rule("switch slider", [
            f"background-color: {p['card_bg']}",
            f"border: 1px solid {p['border']}",
        ]),
        _rule("scale > trough, scale trough", [
            f"background-color: {p['scrollbar_trough']}",
            f"border: 1px solid {p['border']}",
        ]),
        _rule("scale > trough > highlight, scale highlight, scale fill", [
            f"background-color: {p['accent_bg']}",
        ]),
        _rule("scale > trough > slider, scale slider", [
            f"background-color: {p['card_bg']}",
            f"border: 1px solid {p['border']}",
            "border-radius: 99px",
            "min-width: 18px",
            "min-height: 18px",
        ]),
        _rule("scrollbar > range > trough, scrollbar trough", [
            f"background-color: {p['scrollbar_trough']}",
            "opacity: 1",
        ]),
        _rule("scrollbar > range > trough > slider, scrollbar slider", [
            f"background-color: {p['scrollbar']}",
            f"border: 1px solid {p['border']}",
            "min-width: 8px",
            "min-height: 8px",
            "border-radius: 4px",
            "opacity: 1",
        ]),
        _rule("notebook > header > tabs > tab:checked", [
            f"background-color: {p['view_bg']}",
            f"color: {p['view_fg']}",
            f"border-bottom: {g.border_width}px solid {p['accent_bg']}",
            "box-shadow: none",
        ]),
        _rule("tabbar tab:checked", [f"color: {p['accent_bg']}"]),
    ]
    if image_decls is not None and image.on_content:
        parts.append(
            _rule("window .view, window leaflet, window navigation-view", image_decls)
        )
    parts.extend(_interface_font_rules(chosen))
    return "\n".join(parts)


def _header_line(geometry: Geometry, color: str) -> str:
    if geometry.headerbar_line <= 0:
        return "border-bottom: none"
    return f"border-bottom: {geometry.headerbar_line}px solid {parse_hex(color)}"


def _font_family(name: str, generic: str) -> str | None:
    cleaned = clean_font_family(name)
    if not cleaned:
        return None
    return f'"{cleaned}", {generic}'


def _title_declarations(geometry: Geometry, fonts: Fonts | None = None) -> list[str]:
    weight = "bold" if geometry.title_bold else "normal"
    decls = [f"font-weight: {weight}"]
    if geometry.title_size > 0:
        decls.append(f"font-size: {geometry.title_size}px")
    family = _font_family((fonts or Fonts()).title, "sans-serif")
    if family:
        decls.append(f"font-family: {family}")
    return decls


def _interface_font_rules(fonts: Fonts | None) -> list[str]:
    chosen = (fonts or Fonts()).clamped()
    rules: list[str] = []
    ui: list[str] = []
    family = _font_family(chosen.interface, "sans-serif")
    if family:
        ui.append(f"font-family: {family}")
    if chosen.interface_size > 0:
        ui.append(f"font-size: {chosen.interface_size}px")
    if ui:
        rules.append(_rule("window", ui))
    mono: list[str] = []
    mono_family = _font_family(chosen.monospace, "monospace")
    if mono_family:
        mono.append(f"font-family: {mono_family}")
    if chosen.monospace_size > 0:
        mono.append(f"font-size: {chosen.monospace_size}px")
    if mono:
        rules.append(
            _rule(
                ".monospace, label.monospace, entry.monospace, textview.monospace, textview.monospace text",
                mono,
            )
        )
    return rules


def render_gtk3(
    palette: Palette,
    geometry: Geometry,
    backdrop: Backdrop | None = None,
    fonts: Fonts | None = None,
) -> str:
    p = palette
    g = geometry.clamped()
    chosen = (fonts or Fonts()).clamped()
    defines = {
        "theme_bg_color": p["window_bg"],
        "theme_fg_color": p["window_fg"],
        "theme_base_color": p["view_bg"],
        "theme_text_color": p["view_fg"],
        "theme_selected_bg_color": p["accent_bg"],
        "theme_selected_fg_color": p["accent_fg"],
        "theme_unfocused_bg_color": p["headerbar_backdrop_bg"],
        "theme_unfocused_fg_color": p["headerbar_backdrop_fg"],
        "theme_unfocused_base_color": p["view_bg"],
        "theme_unfocused_text_color": p["view_fg"],
        "theme_unfocused_selected_bg_color": p["accent_bg"],
        "theme_unfocused_selected_fg_color": p["accent_fg"],
        "insensitive_bg_color": p["scrollbar_trough"],
        "insensitive_fg_color": p["border"],
        "borders": p["border"],
        "unfocused_borders": p["border_inactive"],
        "warning_color": p["warning"],
        "error_color": p["error"],
        "success_color": p["success"],
        "link_color": p["accent_bg"],
    }
    image = (backdrop or Backdrop()).clamped()
    image_decls = _image_declarations(image)
    lines = ["/* Kontur: kolory, obrys, cień i geometria okien GTK 3. */"]
    lines.extend(f"@define-color {name} {color};" for name, color in defines.items())
    lines.append("")
    extent = _extent(g)
    parts = [
        "\n".join(lines),
        _rule("window, .background", [
            f"background-color: {p['window_bg']}",
            f"color: {p['window_fg']}",
            *(image_decls or ["background-image: none"]),
        ]),
        _rule("decoration", [
            f"border-radius: {g.radius}px",
            f"margin: {extent}px",
            "border: none",
            f"box-shadow: {_shadow(g, p['border_active'], p['shadow'], g.shadow_alpha)}",
        ]),
        _rule("decoration:backdrop", [
            f"box-shadow: {_shadow(g, p['border_inactive'], p['shadow'], g.shadow_alpha_idle)}",
        ]),
        _rule(".maximized decoration, .fullscreen decoration, .tiled decoration", [
            "border-radius: 0",
            "margin: 0",
            "box-shadow: none",
        ]),
        _rule(".titlebar, headerbar", [
            f"min-height: {g.headerbar_height}px",
            f"padding: {g.headerbar_pad_y}px {g.headerbar_pad_x}px",
            f"background-color: {p['headerbar_bg']}",
            f"color: {p['headerbar_fg']}",
            *_layer(image.header_path, image.header_fit),
            f"border-radius: {g.headerbar_radius}px {g.headerbar_radius}px 0 0",
            _header_line(g, p["headerbar_line"]),
            f"box-shadow: {_headerbar_shadow(g, p['headerbar_shadow_color'])}",
            *_title_declarations(g),
        ]),
        _rule("headerbar:backdrop, .titlebar:backdrop", [
            f"background-color: {p['headerbar_backdrop_bg']}",
            f"color: {p['headerbar_backdrop_fg']}",
            "background-image: none",
            f"border-bottom-color: {p['border_inactive']}",
        ]),
        _rule(".sidebar, .sidebar-pane", [
            f"background-color: {p['sidebar_bg']}",
            f"color: {p['sidebar_fg']}",
            *_layer(image.sidebar_path, image.sidebar_fit),
        ]),
        _rule(".view, textview, textview text, iconview", [
            f"background-color: {p['view_bg']}",
            f"color: {p['view_fg']}",
            *((image_decls or []) if image.on_content and image_decls else []),
        ]),
        _rule(".card, frame, .frame", [
            f"background-color: {p['card_bg']}",
            f"color: {p['card_fg']}",
            f"border: {g.border_width}px solid {p['border']}",
            "box-shadow: none",
        ]),
        _rule("dialog, messagedialog, .dialog", [
            f"background-color: {p['dialog_bg']}",
            f"color: {p['dialog_fg']}",
        ]),
        _rule("menu, .menu, popover, .popover", [
            f"background-color: {p['popover_bg']}",
            f"color: {p['popover_fg']}",
            f"border: 1px solid {p['border']}",
            "box-shadow: none",
        ]),
        _rule("tooltip", [
            f"background-color: {p['window_fg']}",
            f"color: {p['window_bg']}",
            f"border: 1px solid {p['border']}",
        ]),
        _rule("entry", [
            f"background-color: {p['input_bg']}",
            f"color: {p['input_fg']}",
            f"caret-color: {p['input_fg']}",
            f"border: 1px solid {p['input_border']}",
            "background-image: none",
        ]),
        _rule("entry:focus", [
            f"border-color: {p['focus']}",
            f"box-shadow: 0 0 0 2px {p['focus']}",
        ]),
        _rule("entry selection, text selection, label selection", [
            f"background-color: {p['accent_bg']}",
            f"color: {p['accent_fg']}",
        ]),
        _rule("button:not(.flat):not(.titlebutton)", [
            f"background-color: {p['card_bg']}",
            f"color: {p['card_fg']}",
            "background-image: none",
            f"border: 1px solid {p['border']}",
            "box-shadow: none",
        ]),
        _rule("button.suggested-action", [
            f"background-color: {p['accent_bg']}",
            f"color: {p['accent_fg']}",
            f"border-color: {p['accent_bg']}",
            "background-image: none",
        ]),
        _rule("button.destructive-action", [
            f"background-color: {p['destructive_bg']}",
            f"color: {p['destructive_fg']}",
            f"border-color: {p['destructive_bg']}",
            "background-image: none",
        ]),
        _rule("button.titlebutton, button.titlebutton:hover, button.titlebutton:backdrop", [
            "background: none",
            "background-image: none",
            "border: none",
            "box-shadow: none",
        ]),
        _rule("switch", [
            f"background-color: {p['scrollbar_trough']}",
            f"border: 1px solid {p['border']}",
            "background-image: none",
        ]),
        _rule("switch:checked", [
            f"background-color: {p['accent_bg']}",
            f"border-color: {p['accent_bg']}",
        ]),
        _rule("switch slider", [
            f"background-color: {p['card_bg']}",
            f"border: 1px solid {p['border']}",
        ]),
        _rule("scale trough", [
            f"background-color: {p['scrollbar_trough']}",
            f"border: 1px solid {p['border']}",
            "min-height: 6px",
        ]),
        _rule("scale highlight", [f"background-color: {p['accent_bg']}"]),
        _rule("scale slider", [
            f"background-color: {p['card_bg']}",
            f"border: 1px solid {p['border']}",
            "border-radius: 99px",
            "min-width: 18px",
            "min-height: 18px",
        ]),
        _rule("scrollbar trough", [
            f"background-color: {p['scrollbar_trough']}",
        ]),
        _rule("scrollbar slider", [
            f"background-color: {p['scrollbar']}",
            f"border: 1px solid {p['border']}",
            "border-radius: 4px",
            "min-width: 8px",
            "min-height: 8px",
        ]),
        _rule("notebook tab:checked", [
            f"background-color: {p['view_bg']}",
            f"color: {p['view_fg']}",
            f"border-bottom: {g.border_width}px solid {p['accent_bg']}",
            "box-shadow: none",
        ]),
    ]
    title_family = _font_family(chosen.title, "sans-serif")
    if title_family:
        parts.append(_rule("headerbar .title, .titlebar .title", [f"font-family: {title_family}"]))
    parts.extend(_interface_font_rules(chosen))
    return "\n".join(parts)


def wrap_block(body: str) -> str:
    return f"{BEGIN}\n{body.rstrip()}\n{END}\n"


def upsert_block(existing: str, body: str) -> str:
    block = wrap_block(body)
    start = existing.find(BEGIN)
    end = existing.find(END)
    if start != -1 and end != -1 and end >= start:
        tail = existing[end + len(END):]
        if tail.startswith("\n"):
            tail = tail[1:]
        head = existing[:start].rstrip()
        if head:
            return f"{head}\n\n{block}{tail}"
        return f"{block}{tail}"
    stripped = existing.rstrip()
    if not stripped:
        return block
    return f"{stripped}\n\n{block}"


def remove_block(existing: str) -> str:
    start = existing.find(BEGIN)
    end = existing.find(END)
    if start == -1 or end == -1 or end < start:
        return existing
    head = existing[:start].rstrip()
    tail = existing[end + len(END):].lstrip("\n")
    if head and tail:
        return f"{head}\n\n{tail}"
    if head:
        return head + "\n"
    return tail
