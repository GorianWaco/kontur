import tempfile
import unittest
from pathlib import Path

from kontur.apply import (
    StyleConfig,
    delete_named_palette,
    remember_image,
    reset_overrides,
    reset_styles,
    save_named_palette,
    saved_palette,
    styles_installed,
    write_styles,
)
from kontur.colors import Appearance, Backdrop, Fonts, presets
from kontur.cssgen import BEGIN
from kontur.themes import apply_appearance, render_settings


class ApplyTests(unittest.TestCase):
    def test_write_and_reset_roundtrip(self) -> None:
        preset = presets()[0]
        config = StyleConfig(preset.id, preset.palette, preset.geometry)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gtk4 = root / "gtk-4.0" / "gtk.css"
            gtk3 = root / "gtk-3.0" / "gtk.css"
            gtk4.parent.mkdir(parents=True)
            gtk3.parent.mkdir(parents=True)
            gtk4.write_text("/* zostaw */\nlabel { color: #010101; }\n", encoding="utf-8")
            write_styles(config, gtk4, gtk3)
            text4 = gtk4.read_text(encoding="utf-8")
            text3 = gtk3.read_text(encoding="utf-8")
            self.assertIn("/* zostaw */", text4)
            self.assertIn(BEGIN, text4)
            self.assertIn("@define-color", text3)
            self.assertTrue((gtk4.parent / "gtk.css.kontur-bak").is_file())
            write_styles(config, gtk4, gtk3)
            self.assertEqual(gtk4.read_text(encoding="utf-8").count(BEGIN), 1)
            self.assertTrue(styles_installed(gtk4, gtk3))
            reset_styles(gtk4, gtk3)
            left = gtk4.read_text(encoding="utf-8")
            self.assertIn("/* zostaw */", left)
            self.assertNotIn(BEGIN, left)
            self.assertNotIn(BEGIN, gtk3.read_text(encoding="utf-8"))

    def test_saved_palette_roundtrip(self) -> None:
        preset = presets()[3]
        config = StyleConfig(
            "custom",
            preset.palette,
            preset.geometry,
            Backdrop(path="/tmp/nie-ma.png", fit="contain", on_content=False),
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "palettes.json"
            picture = Path(folder) / "a.png"
            picture.write_bytes(b"png")
            stored = remember_image(str(picture), Path(folder) / "backgrounds")
            self.assertTrue(Path(stored).is_file())
            save_named_palette("Nocna", config, path)
            save_named_palette("Nocna", config, path)
            loaded = saved_palette("Nocna", path)
            assert loaded is not None
            self.assertEqual(loaded.geometry.shadow_blur, preset.geometry.shadow_blur)
            self.assertFalse(loaded.backdrop.on_content)
            self.assertTrue(delete_named_palette("Nocna", path))
            self.assertIsNone(saved_palette("Nocna", path))

    def test_fonts_survive_config_roundtrip(self) -> None:
        preset = presets()[0]
        fonts = Fonts(interface="Inter", interface_size=14, title="Cantarell")
        config = StyleConfig(preset.id, preset.palette, preset.geometry, fonts=fonts)
        loaded = StyleConfig.from_dict(config.to_dict())
        self.assertEqual(loaded.fonts.interface, "Inter")
        self.assertEqual(loaded.fonts.interface_size, 14)
        self.assertEqual(loaded.fonts.title, "Cantarell")
        legacy = StyleConfig.from_dict(
            {"preset": preset.id, "palette": preset.palette.to_dict(), "geometry": {}}
        )
        self.assertEqual(legacy.fonts.interface, "")
        self.assertEqual(legacy.fonts.interface_size, 0)

    def test_settings_file_keeps_foreign_keys(self) -> None:
        original = "[Settings]\ngtk-application-prefer-dark-theme=1\n\n[Other]\nfoo=1\n"
        updated = render_settings(original, {"gtk-icon-theme-name": "Adwaita", "gtk-cursor-theme-name": "Adwaita"})
        self.assertIn("gtk-application-prefer-dark-theme=1", updated)
        self.assertIn("foo=1", updated)
        self.assertIn("gtk-icon-theme-name=Adwaita", updated)
        cleared = render_settings(updated, {"gtk-icon-theme-name": None, "gtk-cursor-theme-name": None})
        self.assertNotIn("gtk-icon-theme-name", cleared)
        self.assertNotIn("gtk-cursor-theme-name", cleared)
        self.assertIn("[Other]", cleared)
        self.assertEqual(Appearance.from_dict({"icons": "Adwaita\n[Settings]"}).icons, "")

    def test_appearance_restores_previous_theme(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gtk4 = root / "gtk-4.0" / "settings.ini"
            gtk3 = root / "gtk-3.0" / "settings.ini"
            gtk4.parent.mkdir(parents=True)
            gtk3.parent.mkdir(parents=True)
            gtk4.write_text(
                "[Settings]\ngtk-icon-theme-name=Yaru\ngtk-cursor-theme-name=Yaru\n",
                encoding="utf-8",
            )
            backup = apply_appearance(Appearance(icons="Adwaita", cursor="Adwaita"), {}, gtk3, gtk4)
            self.assertIn("gtk-icon-theme-name=Adwaita", gtk4.read_text(encoding="utf-8"))
            self.assertEqual(backup["gtk4"]["gtk-icon-theme-name"], "Yaru")
            self.assertIn("gtk-icon-theme-name=Adwaita", gtk3.read_text(encoding="utf-8"))
            apply_appearance(Appearance(), backup, gtk3, gtk4)
            restored = gtk4.read_text(encoding="utf-8")
            self.assertIn("gtk-icon-theme-name=Yaru", restored)
            self.assertNotIn("Adwaita", gtk3.read_text(encoding="utf-8"))

    def test_reset_overrides_clears_theme_without_touching_foreign_css(self) -> None:
        preset = presets()[0]
        config = StyleConfig(
            preset.id,
            preset.palette,
            preset.geometry,
            appearance=Appearance(icons="Adwaita"),
        )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gtk4 = root / "gtk-4.0" / "gtk.css"
            gtk3 = root / "gtk-3.0" / "gtk.css"
            settings4 = root / "gtk-4.0" / "settings.ini"
            settings3 = root / "gtk-3.0" / "settings.ini"
            config_file = root / "config.json"
            gtk4.parent.mkdir(parents=True)
            gtk3.parent.mkdir(parents=True)
            gtk4.write_text("/* zostaw */\n", encoding="utf-8")
            write_styles(config, gtk4, gtk3)
            backup = apply_appearance(config.appearance, {}, settings3, settings4)
            config.appearance_backup = backup
            from kontur.apply import save_config

            save_config(config, config_file)
            reset_overrides(gtk4, gtk3, settings4, settings3, config_file)
            self.assertIn("/* zostaw */", gtk4.read_text(encoding="utf-8"))
            self.assertNotIn(BEGIN, gtk4.read_text(encoding="utf-8"))
            self.assertNotIn("Adwaita", settings4.read_text(encoding="utf-8"))
            loaded = StyleConfig.from_dict(__import__("json").loads(config_file.read_text(encoding="utf-8")))
            self.assertEqual(loaded.appearance.icons, "")


if __name__ == "__main__":
    unittest.main()
