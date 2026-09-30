"""Okno Kontura: miejsca interfejsu, czcionki i opcje."""

from __future__ import annotations

import gi
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .apply import (
    StyleConfig,
    delete_named_palette,
    load_config,
    load_saved_palettes,
    remember_image,
    reset_styles,
    save_config,
    save_named_palette,
    saved_palette,
    styles_installed,
    write_styles,
)
from .color_picker import ColorButton
from .i18n import LANGUAGES, get_language, set_language, t, tf
from .colors import (
    IMAGE_FITS,
    LIMITS,
    Appearance,
    Backdrop,
    Fonts,
    Geometry,
    Palette,
    hex_from_channels,
    parse_hex,
    presets,
)
from .cssgen import render_gtk4
from .themes import apply_appearance, cursor_themes, icon_themes


def _installed_families() -> list[str]:
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import PangoCairo

    fontmap = PangoCairo.FontMap.get_default()
    if fontmap is None:
        return []
    names = {family.get_name() for family in fontmap.list_families() if family.get_name()}
    return sorted(names, key=str.casefold)


class KonturWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="Kontur")
        self.set_default_size(1080, 780)
        self._loading = True
        self._preset_lock = False
        self._write_id = 0
        self._color_buttons: dict[str, ColorButton] = {}
        self._spins: dict[str, Adw.SpinRow] = {}
        self._flags: dict[str, Adw.SwitchRow] = {}
        self._fit_lock = False
        self._lang_lock = False
        self._font_lock = False
        self._font_names = _installed_families()
        self._font_rows: dict[str, Adw.ComboRow] = {}
        self._font_family = {"interface": "", "monospace": "", "title": ""}
        self._font_spins: dict[str, Adw.SpinRow] = {}
        self._image_slots: dict[str, dict] = {}
        self._theme_lock = False
        self._theme_rows: dict[str, Adw.ComboRow] = {}
        self._theme_value = {"icons": "", "cursor": ""}
        self._icon_catalog = icon_themes()
        self._cursor_catalog = cursor_themes()
        settings = Gtk.Settings.get_default()
        self._startup_icons = str(settings.get_property("gtk-icon-theme-name") or "") if settings else ""
        self._startup_cursor = str(settings.get_property("gtk-cursor-theme-name") or "") if settings else ""
        self._i18n: list[tuple] = []
        self._config = load_config()
        self._appearance_backup = dict(self._config.appearance_backup)
        set_language(self._config.language)

        self._provider = Gtk.CssProvider()
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                self._provider,
                Gtk.STYLE_PROVIDER_PRIORITY_USER + 1,
            )

        self._toast = Adw.ToastOverlay()
        self.set_content(self._toast)

        self._stack = Adw.ViewStack()
        self._stack.connect("notify::visible-child", self._sync_section_title)
        self._add_section(self._set_page(), "set", "page_set", "preferences-desktop-appearance-symbolic")
        self._add_section(
            self._window_page(),
            "window",
            "page_window",
            "window-maximize-symbolic",
            section="nav_places",
        )
        self._add_section(self._header_page(), "header", "page_header", "view-restore-symbolic")
        self._add_section(self._sidebar_page(), "sidebar", "page_sidebar", "sidebar-show-symbolic")
        self._add_section(self._place_page("grp_cards", (
            ("card_bg", "lbl_card_bg", ""),
            ("card_fg", "lbl_card_fg", ""),
        )), "cards", "page_cards", "view-paged-symbolic")
        self._add_section(self._place_page("grp_view", (
            ("view_bg", "lbl_view_bg", "sub_lists"),
            ("view_fg", "lbl_view_fg", ""),
            ("input_bg", "lbl_input_bg", "sub_fields"),
            ("input_fg", "lbl_input_fg", ""),
            ("input_border", "lbl_input_border", ""),
        )), "view", "page_view", "view-list-symbolic")
        self._add_section(self._place_page("grp_menus", (
            ("popover_bg", "lbl_menu_bg", "sub_menus"),
            ("popover_fg", "lbl_menu_fg", ""),
        )), "menus", "page_menus", "open-menu-symbolic")
        self._add_section(self._place_page("grp_dialogs", (
            ("dialog_bg", "lbl_dialog_bg", "sub_modals"),
            ("dialog_fg", "lbl_dialog_fg", ""),
        )), "dialogs", "page_dialogs", "dialog-information-symbolic")
        self._add_section(self._place_page("grp_accent", (
            ("accent_bg", "lbl_accent", "sub_accent"),
            ("accent_fg", "lbl_accent_fg", ""),
            ("focus", "lbl_focus", "sub_focus"),
        )), "accent", "page_accent", "emblem-important-symbolic")
        self._add_section(self._place_page("grp_scroll", (
            ("scrollbar", "lbl_scroll", "sub_scroll"),
            ("scrollbar_trough", "lbl_trough", ""),
        )), "scroll", "page_scroll", "pan-down-symbolic")
        self._add_section(self._place_page("grp_states", (
            ("destructive_bg", "lbl_destructive", "sub_destructive"),
            ("destructive_fg", "lbl_destructive_fg", ""),
            ("success", "lbl_success", ""),
            ("warning", "lbl_warning", ""),
            ("error", "lbl_error", ""),
        )), "states", "page_states", "dialog-warning-symbolic")
        self._add_section(
            self._fonts_page(),
            "fonts",
            "page_fonts",
            "preferences-desktop-font-symbolic",
            section="nav_text",
        )
        self._add_section(
            self._icons_page(),
            "icons",
            "page_icons",
            "view-app-grid-symbolic",
            section="nav_app",
        )
        self._add_section(
            self._options_page(),
            "options",
            "page_options",
            "preferences-system-symbolic",
        )
        self._add_section(self._preview_page(), "preview", "page_preview", "view-reveal-symbolic")

        switcher = Adw.ViewSwitcherSidebar()
        switcher.set_stack(self._stack)
        switcher.connect("activated", self._on_section_activated)
        sidebar_view = Adw.ToolbarView()
        sidebar_view.add_top_bar(Adw.HeaderBar())
        sidebar_view.set_content(switcher)
        sidebar_page = Adw.NavigationPage(title="Kontur", child=sidebar_view)

        self._banner = Adw.Banner(title=t("banner"))
        self._i18n.append(("banner", self._banner, ("banner",)))
        self._banner.set_revealed(styles_installed())
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body.append(self._banner)
        body.append(self._stack)
        self._stack.set_vexpand(True)

        bar = Gtk.ActionBar()
        remove = Gtk.Button(label=t("btn_remove"))
        self._i18n.append(("button", remove, ("btn_remove",)))
        remove.add_css_class("destructive-action")
        remove.connect("clicked", self._confirm_reset)
        apply_button = Gtk.Button(label=t("btn_apply"))
        self._i18n.append(("button", apply_button, ("btn_apply",)))
        apply_button.add_css_class("suggested-action")
        apply_button.connect("clicked", self._apply_now)
        bar.pack_start(remove)
        bar.pack_end(apply_button)

        content_view = Adw.ToolbarView()
        content_view.add_top_bar(Adw.HeaderBar())
        content_view.set_content(body)
        content_view.add_bottom_bar(bar)
        self._content_page = Adw.NavigationPage(title=t("page_set"), child=content_view)

        self._split = Adw.NavigationSplitView()
        self._split.set_min_sidebar_width(220)
        self._split.set_max_sidebar_width(300)
        self._split.set_sidebar_width_fraction(0.28)
        self._split.set_sidebar(sidebar_page)
        self._split.set_content(self._content_page)
        self._toast.set_child(self._split)

        self._fill(
            self._config.palette,
            self._config.geometry,
            self._config.preset,
            self._config.backdrop,
            self._config.fonts,
            self._config.appearance,
        )
        self._loading = False
        self._preview()
        self.connect("close-request", self._on_close)

    def current_gtk4_css(self) -> str:
        palette, geometry, backdrop, fonts, _appearance = self._collect()
        return render_gtk4(palette, geometry, backdrop, fonts)

    def _add_section(
        self,
        child: Gtk.Widget,
        name: str,
        title_key: str,
        icon: str,
        section: str | None = None,
    ) -> None:
        page = self._stack.add_titled_with_icon(child, name, t(title_key), icon)
        self._i18n.append(("page", page, (title_key,)))
        if section:
            page.set_starts_section(True)
            page.set_section_title(t(section))
            self._i18n.append(("section", page, (section,)))

    def _on_section_activated(self, *_args: object) -> None:
        self._split.set_show_content(True)
        self._sync_section_title()

    def _sync_section_title(self, *_args: object) -> None:
        content = getattr(self, "_content_page", None)
        if content is None:
            return
        child = self._stack.get_visible_child()
        if child is None:
            return
        content.set_title(self._stack.get_page(child).get_title())

    def _scrolled(self) -> tuple[Gtk.ScrolledWindow, Gtk.Box]:
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)
        scroll.set_child(box)
        return scroll, box

    def _set_page(self) -> Gtk.Widget:
        scroll, box = self._scrolled()
        preset_group = self._group("grp_set", "grp_set_desc")
        self._preset = Adw.ComboRow(title=t("row_palette"))
        self._remember_row(self._preset, "row_palette", None)
        self._preset.connect("notify::selected", self._on_preset)
        preset_group.add(self._preset)
        self._reload_preset_titles()
        self._palette_name = Adw.EntryRow(title=t("row_palette_name"))
        self._remember_row(self._palette_name, "row_palette_name", None)
        preset_group.add(self._palette_name)
        save_box = Gtk.Box(spacing=8, homogeneous=True)
        save_box.set_margin_top(6)
        save_button = Gtk.Button(label=t("btn_save_palette"))
        self._remember_button(save_button, "btn_save_palette")
        save_button.connect("clicked", self._save_palette)
        delete_button = Gtk.Button(label=t("btn_delete_palette"))
        self._remember_button(delete_button, "btn_delete_palette")
        delete_button.connect("clicked", self._delete_palette)
        save_box.append(save_button)
        save_box.append(delete_button)
        preset_group.add(save_box)
        self._saved = Adw.ComboRow(title=t("row_saved"))
        self._remember_row(self._saved, "row_saved", None)
        self._saved.connect("notify::selected", self._on_saved)
        preset_group.add(self._saved)
        self._saved_lock = False
        self._reload_saved()
        box.append(preset_group)
        return scroll

    def _window_page(self) -> Gtk.Widget:
        scroll, box = self._scrolled()
        self._color_group(box, "grp_window", (
            ("window_bg", "lbl_bg", "sub_client"),
            ("window_fg", "lbl_text", "sub_main_text"),
        ))
        box.append(self._image_group("window", "grp_image", "grp_image_desc", content=True))
        shape = self._group("grp_shape", "grp_shape_desc")
        self._add_spin(shape, "radius", "spin_radius", "sub_radius")
        self._add_spin(shape, "border_width", "spin_border", "sub_border")
        box.append(shape)
        self._color_group(box, "grp_border", (
            ("border", "lbl_line", "sub_line"),
            ("border_active", "lbl_border_active", ""),
            ("border_inactive", "lbl_border_idle", ""),
        ))
        shadow = self._group("grp_shadow", "grp_shadow_desc")
        self._add_color(shadow, "shadow", "lbl_shadow", "sub_shadow")
        self._add_switch(shadow, "shadow_enabled", "sw_shadow", "sub_sw_shadow")
        self._add_spin(shadow, "shadow_offset", "spin_offset", "sub_offset")
        self._add_spin(shadow, "shadow_spread", "spin_spread", "sub_spread")
        self._add_spin(shadow, "shadow_blur", "spin_blur", "sub_blur")
        self._add_spin(shadow, "shadow_alpha", "spin_alpha", "sub_alpha")
        self._add_spin(shadow, "shadow_alpha_idle", "spin_alpha_idle", "sub_alpha_idle")
        box.append(shadow)
        return scroll

    def _header_page(self) -> Gtk.Widget:
        scroll, box = self._scrolled()
        self._color_group(box, "grp_header_colors", (
            ("headerbar_bg", "lbl_bg", "sub_active_win"),
            ("headerbar_fg", "lbl_hbar_fg", ""),
            ("headerbar_backdrop_bg", "lbl_hbar_bg_idle", "sub_idle_win"),
            ("headerbar_backdrop_fg", "lbl_hbar_fg_idle", ""),
            ("headerbar_line", "lbl_hbar_line", "sub_hbar_line"),
        ))
        box.append(self._image_group("header", "grp_header_image", "grp_header_image_desc", content=False))
        bar = self._group("grp_hbar", "grp_hbar_desc")
        self._add_spin(bar, "headerbar_height", "spin_hbar_h", "sub_px")
        self._add_spin(bar, "headerbar_pad_x", "spin_pad_x", "sub_pad_x")
        self._add_spin(bar, "headerbar_pad_y", "spin_pad_y", "sub_pad_y")
        self._add_spin(bar, "headerbar_radius", "spin_hbar_radius", "sub_hbar_radius")
        self._add_spin(bar, "headerbar_line", "spin_line", "sub_line_w")
        self._add_spin(bar, "title_size", "spin_title_size", "sub_title_size")
        self._add_switch(bar, "title_bold", "sw_title_bold", "sub_title_bold")
        self._add_spin(bar, "controls_size", "spin_controls", "sub_controls")
        self._add_spin(bar, "controls_gap", "spin_gap", "sub_gap")
        self._add_switch(bar, "headerbar_shadow", "sw_hbar_shadow", "sub_hbar_shadow")
        self._add_color(bar, "headerbar_shadow_color", "lbl_hbar_shadow", "sub_hbar_shadow_color")
        self._add_spin(bar, "headerbar_shadow_blur", "spin_hbar_blur", "sub_px")
        self._add_spin(bar, "headerbar_shadow_alpha", "spin_hbar_alpha", "sub_hbar_alpha")
        box.append(bar)
        return scroll

    def _sidebar_page(self) -> Gtk.Widget:
        scroll, box = self._scrolled()
        self._color_group(box, "grp_sidebar", (
            ("sidebar_bg", "lbl_bg", "sub_second_side"),
            ("sidebar_fg", "lbl_text", ""),
        ))
        box.append(self._image_group("sidebar", "grp_sidebar_image", "grp_sidebar_image_desc", content=False))
        return scroll

    def _place_page(self, title_key: str, rows: tuple[tuple[str, str, str], ...]) -> Gtk.Widget:
        scroll, box = self._scrolled()
        self._color_group(box, title_key, rows)
        return scroll

    def _fonts_page(self) -> Gtk.Widget:
        scroll, box = self._scrolled()
        group = self._group("grp_fonts", "grp_fonts_desc")
        for key, title_key, sub_key in (
            ("interface", "font_ui", "font_ui_sub"),
            ("monospace", "font_mono", "font_mono_sub"),
            ("title", "font_title", "font_title_sub"),
        ):
            row = Adw.ComboRow(title=t(title_key), subtitle=t(sub_key))
            row.set_enable_search(True)
            self._remember_row(row, title_key, sub_key)
            row.connect("notify::selected", self._on_font_family, key)
            self._font_rows[key] = row
            group.add(row)
        self._add_font_spin(group, "interface_size", "font_ui_size", "font_size_sub")
        self._add_font_spin(group, "monospace_size", "font_mono_size", "font_size_sub")
        box.append(group)
        self._reload_font_models()
        return scroll

    def _icons_page(self) -> Gtk.Widget:
        scroll, box = self._scrolled()
        group = self._group("page_icons", "grp_icons_desc")
        self._add_theme_row(group, "icons", "row_icons", "row_icons_sub")
        self._add_theme_row(group, "cursor", "row_cursor", "row_cursor_sub")
        box.append(group)
        self._reload_theme_models()
        return scroll

    def _options_page(self) -> Gtk.Widget:
        scroll, box = self._scrolled()
        language_group = self._group("page_options", "language_desc")
        self._language = Adw.ComboRow(title=t("language"))
        self._remember_row(self._language, "language", None)
        lang_model = Gtk.StringList()
        for _code, name in LANGUAGES:
            lang_model.append(name)
        self._language.set_model(lang_model)
        current = next((i for i, (code, _name) in enumerate(LANGUAGES) if code == get_language()), 0)
        self._lang_lock = True
        self._language.set_selected(current)
        self._lang_lock = False
        self._language.connect("notify::selected", self._on_language)
        language_group.add(self._language)
        box.append(language_group)
        return scroll

    def _color_group(
        self,
        box: Gtk.Box,
        title_key: str,
        rows: tuple[tuple[str, str, str], ...],
    ) -> None:
        group = self._group(title_key, None)
        for key, label_key, subtitle_key in rows:
            button = ColorButton()
            button.connect("notify::rgba", self._on_edit)
            self._color_buttons[key] = button
            row = Adw.ActionRow(title=t(label_key), subtitle=t(subtitle_key) if subtitle_key else None)
            self._remember_row(row, label_key, subtitle_key or None)
            row.add_suffix(button)
            group.add(row)
        box.append(group)

    def _add_color(self, group: Adw.PreferencesGroup, key: str, label_key: str, subtitle_key: str) -> None:
        button = ColorButton()
        button.connect("notify::rgba", self._on_edit)
        self._color_buttons[key] = button
        row = Adw.ActionRow(title=t(label_key), subtitle=t(subtitle_key) if subtitle_key else None)
        self._remember_row(row, label_key, subtitle_key or None)
        row.add_suffix(button)
        group.add(row)

    def _group(self, title_key: str, desc_key: str | None) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title=t(title_key),
            description=t(desc_key) if desc_key else None,
        )
        self._i18n.append(("group", group, (title_key, desc_key)))
        return group

    def _remember_row(self, row: Adw.PreferencesRow, title_key: str, sub_key: str | None) -> None:
        self._i18n.append(("row", row, (title_key, sub_key)))

    def _remember_button(self, button: Gtk.Button, key: str) -> None:
        self._i18n.append(("button", button, (key,)))

    def _add_spin(self, group: Adw.PreferencesGroup, key: str, title_key: str, sub_key: str) -> None:
        low, high = LIMITS[key]
        row = Adw.SpinRow.new_with_range(low, high, 1)
        row.set_title(t(title_key))
        row.set_subtitle(t(sub_key))
        self._remember_row(row, title_key, sub_key)
        row.connect("notify::value", self._on_edit)
        self._spins[key] = row
        group.add(row)

    def _add_switch(self, group: Adw.PreferencesGroup, key: str, title_key: str, sub_key: str) -> None:
        row = Adw.SwitchRow(title=t(title_key), subtitle=t(sub_key))
        self._remember_row(row, title_key, sub_key)
        row.connect("notify::active", self._on_edit)
        self._flags[key] = row
        group.add(row)

    def _add_font_spin(self, group: Adw.PreferencesGroup, key: str, title_key: str, sub_key: str) -> None:
        low, high = LIMITS[key]
        row = Adw.SpinRow.new_with_range(low, high, 1)
        row.set_title(t(title_key))
        row.set_subtitle(t(sub_key))
        self._remember_row(row, title_key, sub_key)
        row.connect("notify::value", self._on_edit)
        self._font_spins[key] = row
        group.add(row)

    def _image_group(
        self,
        slot: str,
        title_key: str,
        desc_key: str,
        *,
        content: bool,
    ) -> Adw.PreferencesGroup:
        group = self._group(title_key, desc_key)
        label = Gtk.Label(label=t("no_image"), xalign=0, wrap=True)
        label.add_css_class("dim-label")
        label.set_margin_start(12)
        label.set_margin_end(12)
        group.add(label)
        buttons = Gtk.Box(spacing=8, homogeneous=True)
        buttons.set_margin_top(6)
        pick = Gtk.Button(label=t("btn_pick_image"))
        self._remember_button(pick, "btn_pick_image")
        pick.connect("clicked", lambda *_args, name=slot: self._choose_image(name))
        clear = Gtk.Button(label=t("btn_clear_image"))
        self._remember_button(clear, "btn_clear_image")
        clear.connect("clicked", lambda *_args, name=slot: self._clear_image(name))
        buttons.append(pick)
        buttons.append(clear)
        group.add(buttons)
        fit = Adw.ComboRow(title=t("row_fit"))
        self._remember_row(fit, "row_fit", None)
        fit.connect("notify::selected", self._on_edit)
        group.add(fit)
        on_content = None
        if content:
            on_content = Adw.SwitchRow(
                title=t("row_image_content"),
                subtitle=t("row_image_content_sub"),
            )
            self._remember_row(on_content, "row_image_content", "row_image_content_sub")
            on_content.set_active(True)
            on_content.connect("notify::active", self._on_edit)
            group.add(on_content)
        self._image_slots[slot] = {"path": "", "label": label, "fit": fit, "content": on_content}
        self._reload_fit_row(fit, 0)
        return group

    def _choose_image(self, slot: str) -> None:
        dialog = Gtk.FileDialog(title=t("file_title"))
        image_filter = Gtk.FileFilter()
        image_filter.set_name(t("file_filter"))
        for mime in ("image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp"):
            image_filter.add_mime_type(mime)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(image_filter)
        dialog.set_filters(filters)
        dialog.open(self, None, lambda chooser, result, name=slot: self._image_chosen(chooser, result, name))

    def _image_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult, slot: str) -> None:
        try:
            chosen = dialog.open_finish(result)
        except GLib.Error:
            return
        if chosen is None:
            return
        path = chosen.get_path()
        if not path:
            self._show_toast(t("toast_image_no_path"))
            return
        try:
            stored = remember_image(path)
        except OSError as error:
            self._show_toast(tf("toast_image_copy", error=error))
            return
        if not stored:
            self._show_toast(t("toast_image_read"))
            return
        self._image_slots[slot]["path"] = stored
        self._show_image_names()
        self._on_edit()

    def _clear_image(self, slot: str) -> None:
        self._image_slots[slot]["path"] = ""
        self._show_image_names()
        self._on_edit()

    def _show_image_names(self) -> None:
        for slot in self._image_slots.values():
            path = str(slot["path"] or "")
            slot["label"].set_text(Path(path).name if path else t("no_image"))

    def _add_theme_row(self, group: Adw.PreferencesGroup, key: str, title_key: str, sub_key: str) -> None:
        row = Adw.ComboRow(title=t(title_key), subtitle=t(sub_key))
        row.set_enable_search(True)
        self._remember_row(row, title_key, sub_key)
        row.connect("notify::selected", self._on_theme, key)
        self._theme_rows[key] = row
        group.add(row)

    def _reload_saved(self, select: str | None = None) -> None:
        self._saved_items = load_saved_palettes()
        model = Gtk.StringList()
        model.append("—")
        names = [str(item.get("name")) for item in self._saved_items]
        for name in names:
            model.append(name)
        self._saved_lock = True
        self._saved.set_model(model)
        index = names.index(select) + 1 if select in names else 0
        self._saved.set_selected(index)
        self._saved_lock = False

    def _save_palette(self, *_args: object) -> None:
        try:
            title = save_named_palette(self._palette_name.get_text(), self._style_config())
        except (OSError, ValueError) as error:
            self._show_toast(str(error))
            return
        self._reload_saved(title)
        self._show_toast(tf("toast_palette_saved", name=title))

    def _delete_palette(self, *_args: object) -> None:
        index = self._saved.get_selected()
        if index == 0 or index > len(self._saved_items):
            self._show_toast(t("toast_pick_saved"))
            return
        name = str(self._saved_items[index - 1].get("name"))
        try:
            delete_named_palette(name)
        except (OSError, ValueError) as error:
            self._show_toast(str(error))
            return
        self._reload_saved()
        self._show_toast(tf("toast_palette_deleted", name=name))

    def _on_saved(self, *_args: object) -> None:
        if self._loading or self._saved_lock:
            return
        index = self._saved.get_selected()
        if index == 0 or index > len(getattr(self, "_saved_items", [])):
            return
        item = self._saved_items[index - 1]
        name = str(item.get("name"))
        loaded = saved_palette(name)
        if loaded is None:
            return
        self._palette_name.set_text(name)
        raw_fonts = item.get("fonts")
        fonts = Fonts.from_dict(raw_fonts) if isinstance(raw_fonts, dict) else None
        self._loading = True
        self._fill(loaded.palette, loaded.geometry, "custom", loaded.backdrop, fonts)
        self._loading = False
        self._schedule()

    def _preview_page(self) -> Gtk.Widget:
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_margin_start(18)
        box.set_margin_end(18)
        scroll.set_child(box)

        note = Gtk.Label(wrap=True, xalign=0, label=t("preview_note"))
        self._i18n.append(("label", note, ("preview_note",)))
        box.append(note)

        group = self._group("grp_sample", None)
        entry = Adw.EntryRow(title=t("sample_entry"))
        self._remember_row(entry, "sample_entry", None)
        switch = Adw.SwitchRow(title=t("sample_switch"), active=True)
        self._remember_row(switch, "sample_switch", None)
        group.add(entry)
        group.add(switch)
        box.append(group)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_draw_value(True)
        scale.set_value(40)
        scale.set_hexpand(True)
        buttons = Gtk.Box(spacing=8)
        accent = Gtk.Button(label=t("sample_accent"), css_classes=["suggested-action"])
        plain = Gtk.Button(label=t("sample_plain"))
        remove_sample = Gtk.Button(label=t("sample_remove"), css_classes=["destructive-action"])
        self._remember_button(accent, "sample_accent")
        self._remember_button(plain, "sample_plain")
        self._remember_button(remove_sample, "sample_remove")
        buttons.append(accent)
        buttons.append(plain)
        buttons.append(remove_sample)
        sample = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sample.append(scale)
        sample.append(buttons)
        frame = Gtk.Frame(child=sample)
        frame.set_margin_top(6)
        sample.set_margin_top(12)
        sample.set_margin_bottom(12)
        sample.set_margin_start(12)
        sample.set_margin_end(12)
        box.append(frame)
        return scroll

    def _fill(
        self,
        palette: Palette,
        geometry: Geometry,
        preset_id: str,
        backdrop: Backdrop | None = None,
        fonts: Fonts | None = None,
        appearance: Appearance | None = None,
    ) -> None:
        items = presets()
        index = next((i for i, item in enumerate(items) if item.id == preset_id), len(items))
        self._preset_lock = True
        self._preset.set_selected(index)
        self._preset_lock = False
        for key, button in self._color_buttons.items():
            color = Gdk.RGBA()
            color.parse(palette[key])
            color.alpha = 1
            button.set_rgba(color)
        geo = geometry.clamped()
        for key, row in self._flags.items():
            row.set_active(bool(getattr(geo, key)))
        for key, row in self._spins.items():
            row.set_value(getattr(geo, key))
        picture = (backdrop or Backdrop()).clamped()
        self._set_image("window", picture.path, picture.fit)
        self._set_image("header", picture.header_path, picture.header_fit)
        self._set_image("sidebar", picture.sidebar_path, picture.sidebar_fit)
        content = self._image_slots["window"]["content"]
        if content is not None:
            content.set_active(picture.on_content)
        self._show_image_names()
        if fonts is not None:
            self._apply_fonts(fonts)
        if appearance is not None:
            self._apply_appearance(appearance)
        self._snapshot = self._fingerprint()

    def _set_image(self, slot: str, path: str, fit: str) -> None:
        self._image_slots[slot]["path"] = path
        index = IMAGE_FITS.index(fit) if fit in IMAGE_FITS else 0
        self._reload_fit_row(self._image_slots[slot]["fit"], index)

    def _collect(self) -> tuple[Palette, Geometry, Backdrop, Fonts, Appearance]:
        values: dict[str, str] = {}
        for key, button in self._color_buttons.items():
            rgba = button.get_rgba()
            values[key] = hex_from_channels(rgba.red, rgba.green, rgba.blue)
            parse_hex(values[key])
        palette = Palette(values)
        geometry = Geometry(
            radius=int(self._spins["radius"].get_value()),
            headerbar_height=int(self._spins["headerbar_height"].get_value()),
            headerbar_pad_x=int(self._spins["headerbar_pad_x"].get_value()),
            headerbar_pad_y=int(self._spins["headerbar_pad_y"].get_value()),
            headerbar_radius=int(self._spins["headerbar_radius"].get_value()),
            headerbar_line=int(self._spins["headerbar_line"].get_value()),
            controls_size=int(self._spins["controls_size"].get_value()),
            controls_gap=int(self._spins["controls_gap"].get_value()),
            title_size=int(self._spins["title_size"].get_value()),
            title_bold=bool(self._flags["title_bold"].get_active()),
            border_width=int(self._spins["border_width"].get_value()),
            shadow_enabled=bool(self._flags["shadow_enabled"].get_active()),
            shadow_offset=int(self._spins["shadow_offset"].get_value()),
            shadow_spread=int(self._spins["shadow_spread"].get_value()),
            shadow_blur=int(self._spins["shadow_blur"].get_value()),
            shadow_alpha=int(self._spins["shadow_alpha"].get_value()),
            shadow_alpha_idle=int(self._spins["shadow_alpha_idle"].get_value()),
            headerbar_shadow=bool(self._flags["headerbar_shadow"].get_active()),
            headerbar_shadow_blur=int(self._spins["headerbar_shadow_blur"].get_value()),
            headerbar_shadow_alpha=int(self._spins["headerbar_shadow_alpha"].get_value()),
        ).clamped()
        window_fit = self._fit_value("window")
        content = self._image_slots["window"]["content"]
        backdrop = Backdrop(
            path=str(self._image_slots["window"]["path"]),
            fit=window_fit,
            on_content=bool(content.get_active()) if content is not None else True,
            header_path=str(self._image_slots["header"]["path"]),
            header_fit=self._fit_value("header"),
            sidebar_path=str(self._image_slots["sidebar"]["path"]),
            sidebar_fit=self._fit_value("sidebar"),
        ).clamped()
        return palette, geometry, backdrop, self._collect_fonts(), self._collect_appearance()

    def _fit_value(self, slot: str) -> str:
        index = self._image_slots[slot]["fit"].get_selected()
        return IMAGE_FITS[index] if index < len(IMAGE_FITS) else "cover"

    def _collect_appearance(self) -> Appearance:
        return Appearance(
            icons=self._theme_value["icons"],
            cursor=self._theme_value["cursor"],
        ).clamped()

    def _collect_fonts(self) -> Fonts:
        return Fonts(
            interface=self._font_family["interface"],
            interface_size=int(self._font_spins["interface_size"].get_value()),
            monospace=self._font_family["monospace"],
            monospace_size=int(self._font_spins["monospace_size"].get_value()),
            title=self._font_family["title"],
        ).clamped()

    def _apply_fonts(self, fonts: Fonts) -> None:
        chosen = fonts.clamped()
        self._font_family["interface"] = chosen.interface
        self._font_family["monospace"] = chosen.monospace
        self._font_family["title"] = chosen.title
        self._reload_font_models()
        self._font_spins["interface_size"].set_value(chosen.interface_size)
        self._font_spins["monospace_size"].set_value(chosen.monospace_size)

    def _apply_appearance(self, appearance: Appearance) -> None:
        chosen = appearance.clamped()
        self._theme_value["icons"] = chosen.icons
        self._theme_value["cursor"] = chosen.cursor
        self._reload_theme_models()

    def _theme_catalog(self, key: str) -> list[tuple[str, str]]:
        catalog = self._icon_catalog if key == "icons" else self._cursor_catalog
        current = self._theme_value.get(key, "")
        if current and all(theme_id != current for theme_id, _label in catalog):
            return [(current, current), *catalog]
        return catalog

    def _on_theme(self, _row: Adw.ComboRow, _pspec: object, key: str) -> None:
        if self._loading or self._theme_lock:
            return
        index = self._theme_rows[key].get_selected()
        catalog = self._theme_catalog(key)
        self._theme_value[key] = "" if index == 0 or index > len(catalog) else catalog[index - 1][0]
        self._on_edit()

    def _reload_theme_models(self) -> None:
        for key, row in self._theme_rows.items():
            current = self._theme_value.get(key, "")
            catalog = self._theme_catalog(key)
            model = Gtk.StringList()
            model.append(t("theme_system"))
            for _theme_id, label in catalog:
                model.append(label)
            selected = 0
            for index, (theme_id, _label) in enumerate(catalog):
                if theme_id == current:
                    selected = index + 1
                    break
            self._theme_lock = True
            row.set_model(model)
            row.set_selected(selected)
            self._theme_lock = False

    def _on_font_family(self, _row: Adw.ComboRow, _pspec: object, key: str) -> None:
        if self._loading or self._font_lock:
            return
        index = self._font_rows[key].get_selected()
        choices = self._font_choices(self._font_family.get(key, ""))
        self._font_family[key] = "" if index == 0 or index > len(choices) else choices[index - 1]
        self._on_edit()

    def _font_choices(self, current: str) -> list[str]:
        choices = list(self._font_names)
        if current and current not in choices:
            choices.insert(0, current)
        return choices

    def _reload_font_models(self) -> None:
        for key, row in self._font_rows.items():
            current = self._font_family.get(key, "")
            choices = self._font_choices(current)
            model = Gtk.StringList()
            model.append(t("font_system"))
            for name in choices:
                model.append(name)
            self._font_lock = True
            row.set_model(model)
            row.set_selected(choices.index(current) + 1 if current in choices else 0)
            self._font_lock = False

    def _fingerprint(self) -> tuple:
        palette, geometry, backdrop, fonts, appearance = self._collect()
        return (
            tuple(sorted(palette.to_dict().items())),
            tuple(sorted(geometry.to_dict().items())),
            tuple(sorted(backdrop.to_dict().items())),
            tuple(sorted(fonts.to_dict().items())),
            tuple(sorted(appearance.to_dict().items())),
        )

    def _style_config(self) -> StyleConfig:
        palette, geometry, backdrop, fonts, appearance = self._collect()
        index = self._preset.get_selected()
        items = presets()
        preset_id = items[index].id if index < len(items) else "custom"
        return StyleConfig(
            preset_id,
            palette,
            geometry,
            backdrop,
            get_language(),
            fonts,
            appearance,
            self._appearance_backup,
        )

    def _on_preset(self, *_args: object) -> None:
        if self._loading or self._preset_lock:
            return
        index = self._preset.get_selected()
        items = presets()
        if index >= len(items):
            return
        preset = items[index]
        self._loading = True
        self._fill(preset.palette, preset.geometry, preset.id, Backdrop())
        self._loading = False
        self._schedule()

    def _on_edit(self, *_args: object) -> None:
        if self._loading or self._fit_lock:
            return
        fingerprint = self._fingerprint()
        if fingerprint == self._snapshot:
            return
        self._snapshot = fingerprint
        self._select_custom()
        self._schedule()

    def _select_custom(self) -> None:
        custom = len(presets())
        if self._preset.get_selected() == custom:
            return
        self._preset_lock = True
        self._preset.set_selected(custom)
        self._preset_lock = False

    def _schedule(self) -> None:
        self._preview()
        if self._write_id:
            GLib.source_remove(self._write_id)
        self._write_id = GLib.timeout_add(180, self._flush)

    def _preview(self) -> None:
        try:
            self._provider.load_from_string(self.current_gtk4_css())
        except Exception as error:  # GTK zgłasza błąd CSS jako wyjątek GLib
            self._show_toast(tf("toast_css_preview", error=error))
        self._preview_appearance()

    def _preview_appearance(self) -> None:
        settings = Gtk.Settings.get_default()
        if settings is None:
            return
        appearance = self._collect_appearance()
        icons = appearance.icons or self._startup_icons
        cursor = appearance.cursor or self._startup_cursor
        if icons:
            settings.set_property("gtk-icon-theme-name", icons)
        if cursor:
            settings.set_property("gtk-cursor-theme-name", cursor)

    def _flush(self) -> bool:
        self._write_id = 0
        self._persist()
        return False

    def _apply_now(self, *_args: object) -> None:
        if self._write_id:
            GLib.source_remove(self._write_id)
            self._write_id = 0
        self._preview()
        if self._persist():
            self._show_toast(t("toast_saved_css"))

    def _persist(self) -> bool:
        try:
            config = self._style_config()
            self._appearance_backup = apply_appearance(config.appearance, self._appearance_backup)
            config.appearance_backup = self._appearance_backup
            save_config(config)
            write_styles(config)
        except OSError as error:
            self._show_toast(tf("toast_save_failed", error=error))
            return False
        self._banner.set_revealed(True)
        return True

    def _confirm_reset(self, *_args: object) -> None:
        dialog = Adw.AlertDialog(
            heading=t("reset_title"),
            body=t("reset_body"),
        )
        dialog.add_response("cancel", t("cancel"))
        dialog.add_response("remove", t("sample_remove"))
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_reset_response)
        dialog.present(self)

    def _on_reset_response(self, _dialog: Adw.AlertDialog, response: str) -> None:
        if response != "remove":
            return
        if self._write_id:
            GLib.source_remove(self._write_id)
            self._write_id = 0
        try:
            reset_styles()
            apply_appearance(Appearance(), self._appearance_backup)
        except OSError as error:
            self._show_toast(tf("toast_reset_failed", error=error))
            return
        self._appearance_backup = {}
        self._loading = True
        self._apply_appearance(Appearance())
        self._loading = False
        self._snapshot = self._fingerprint()
        try:
            save_config(self._style_config())
        except OSError as error:
            self._show_toast(tf("toast_save_failed", error=error))
            return
        self._preview_appearance()
        self._provider.load_from_string("window {}")
        self._banner.set_revealed(False)
        self._show_toast(t("toast_reset_done"))

    def _on_close(self, *_args: object) -> bool:
        if self._write_id:
            GLib.source_remove(self._write_id)
            self._write_id = 0
            self._persist()
        return False

    def _show_toast(self, text: str) -> None:
        self._toast.add_toast(Adw.Toast(title=text, timeout=3))

    def _reload_preset_titles(self) -> None:
        index = self._preset.get_selected() if self._preset.get_model() is not None else 0
        model = Gtk.StringList()
        for preset in presets():
            model.append(t(preset.title))
        model.append(t("preset_custom"))
        self._preset_lock = True
        self._preset.set_model(model)
        if index < model.get_n_items():
            self._preset.set_selected(index)
        self._preset_lock = False

    def _reload_fit_row(self, row: Adw.ComboRow, index: int) -> None:
        model = Gtk.StringList()
        for key in ("fit_cover", "fit_contain", "fit_tile", "fit_center"):
            model.append(t(key))
        self._fit_lock = True
        row.set_model(model)
        if index < model.get_n_items():
            row.set_selected(index)
        self._fit_lock = False

    def _reload_fit_titles(self) -> None:
        for slot in self._image_slots.values():
            row = slot["fit"]
            index = row.get_selected() if row.get_model() is not None else 0
            self._reload_fit_row(row, index)

    def _apply_texts(self) -> None:
        for kind, widget, keys in self._i18n:
            if kind == "group":
                widget.set_title(t(keys[0]))
                widget.set_description(t(keys[1]) if keys[1] else None)
            elif kind == "row":
                widget.set_title(t(keys[0]))
                if keys[1]:
                    widget.set_subtitle(t(keys[1]))
            elif kind == "button":
                widget.set_label(t(keys[0]))
            elif kind == "label":
                widget.set_text(t(keys[0]))
            elif kind == "page":
                widget.set_title(t(keys[0]))
            elif kind == "banner":
                widget.set_title(t(keys[0]))
            elif kind == "section":
                widget.set_section_title(t(keys[0]))
        self._reload_preset_titles()
        self._reload_fit_titles()
        self._reload_font_models()
        self._reload_theme_models()
        self._show_image_names()
        self._sync_section_title()

    def _on_language(self, *_args: object) -> None:
        if self._loading or self._lang_lock:
            return
        index = self._language.get_selected()
        if index >= len(LANGUAGES):
            return
        set_language(LANGUAGES[index][0])
        self._apply_texts()
        try:
            save_config(self._style_config())
        except OSError as error:
            self._show_toast(tf("toast_save_failed", error=error))
