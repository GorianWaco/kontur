import re
import tempfile
import unittest
from pathlib import Path

from kontur.colors import Appearance, Backdrop, Fonts, Geometry, Palette, contrast_fg, parse_hex, presets
from kontur.cssgen import css_image_url, remove_block, render_gtk3, render_gtk4, upsert_block

REQUIRED = (
    "--window-bg-color",
    "--window-fg-color",
    "--headerbar-bg-color",
    "--headerbar-fg-color",
    "--accent-color",
    "--accent-bg-color",
    "--card-bg-color",
    "--dialog-bg-color",
    "--sidebar-bg-color",
    "--view-bg-color",
    "--popover-bg-color",
    "--window-radius",
    "--border-color",
    "--border-opacity: 1",
)


def assert_sane(css: str) -> None:
    lower = css.lower()
    if "hsla" in lower or "color-mix" in lower or "transparent" in lower:
        raise AssertionError(css)
    for match in re.finditer(r"(?<![\w-])opacity\s*:\s*([^;]+)", css):
        if match.group(1).strip() != "1":
            raise AssertionError(match.group(0))
    if css.count("{") != css.count("}"):
        raise AssertionError("nawiasy")
    if "--window-bg-color: #" not in css and "@define-color theme_bg_color #" not in css:
        raise AssertionError("brak kryjącego koloru tła")


class CssTests(unittest.TestCase):
    def test_presets_are_opaque(self) -> None:
        for preset in presets():
            gtk4 = render_gtk4(preset.palette, preset.geometry)
            gtk3 = render_gtk3(preset.palette, preset.geometry)
            assert_sane(gtk4)
            assert_sane(gtk3)
            for name in REQUIRED:
                self.assertIn(name, gtk4)
            self.assertIn("@define-color theme_bg_color", gtk3)
            self.assertIn(f"--window-radius: {preset.geometry.radius}px", gtk4)
            self.assertIn(f"min-height: {preset.geometry.headerbar_height}px", gtk4)

    def test_shadow_off_is_only_a_ring(self) -> None:
        preset = presets()[0]
        css = render_gtk4(preset.palette, Geometry(shadow_enabled=False, border_width=3))
        self.assertIn("0 0 0 3px #3584E4", css)
        self.assertNotIn("4px 4px", css)

    def test_shadow_has_blur_and_both_alphas(self) -> None:
        preset = presets()[0]
        css = render_gtk4(
            preset.palette,
            Geometry(
                shadow_enabled=True,
                shadow_offset=5,
                shadow_spread=2,
                shadow_blur=8,
                shadow_alpha=50,
                shadow_alpha_idle=20,
                border_width=1,
            ),
        )
        self.assertIn("5px 5px 8px 2px rgb(0 0 0 / 0.50)", css)
        self.assertIn("5px 5px 8px 2px rgb(0 0 0 / 0.20)", css)
        self.assertIn("0 0 0 1px #3584E4", css)

    def test_rejects_alpha(self) -> None:
        with self.assertRaises(ValueError):
            parse_hex("#11223380")
        self.assertEqual(parse_hex("#abc"), "#AABBCC")
        self.assertEqual(parse_hex("#112233FF"), "#112233")

    def test_contrast(self) -> None:
        self.assertEqual(contrast_fg("#FFFFFF"), "#000000")
        self.assertEqual(contrast_fg("#000000"), "#FFFFFF")

    def test_block_keeps_foreign_css(self) -> None:
        original = "/* własne */\nbutton { color: #FF0000; }\n"
        once = upsert_block(original, "window { color: #00FF00; }")
        self.assertIn("color: #FF0000", once)
        self.assertIn("kontur:begin", once)
        twice = upsert_block(once, "window { color: #0000FF; }")
        self.assertIn("color: #FF0000", twice)
        self.assertIn("#0000FF", twice)
        self.assertNotIn("#00FF00", twice)
        self.assertEqual(twice.count("kontur:begin"), 1)
        cleared = remove_block(twice)
        self.assertIn("color: #FF0000", cleared)
        self.assertNotIn("kontur:begin", cleared)

    def test_old_geometry_still_loads(self) -> None:
        geo = Geometry.from_dict({"headerbar_padding": 9, "radius": 3, "shadow_enabled": True})
        self.assertEqual(geo.headerbar_pad_x, 9)
        self.assertEqual(geo.headerbar_pad_y, 9)
        self.assertEqual(geo.headerbar_radius, 3)
        self.assertEqual(geo.shadow_blur, 16)

    def test_background_image_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            picture = Path(tmp) / "tło okna.png"
            picture.write_bytes(b"\x89PNG\r\n")
            css = render_gtk4(
                presets()[0].palette,
                Geometry(),
                Backdrop(path=str(picture), fit="tile", on_content=True),
            )
            self.assertIn("background-repeat: repeat", css)
            self.assertIn(css_image_url(str(picture)) or "", css)
            self.assertIn("window .view", css)

    def test_header_and_sidebar_images(self) -> None:
        preset = presets()[0]
        with tempfile.TemporaryDirectory() as tmp:
            picture = Path(tmp) / "pasek.png"
            picture.write_bytes(b"\x89PNG\r\n")
            css = render_gtk4(
                preset.palette,
                Geometry(),
                Backdrop(header_path=str(picture), header_fit="contain", sidebar_path=str(picture), sidebar_fit="tile"),
            )
            address = css_image_url(str(picture)) or ""
            self.assertGreaterEqual(css.count(address), 2)
            self.assertIn("background-size: contain", css)
            self.assertIn("background-repeat: repeat", css)
        plain = render_gtk4(preset.palette, Geometry())
        self.assertIn("background-image: none", plain)

    def test_header_shadow_uses_its_own_color(self) -> None:
        values = presets()[0].palette.to_dict()
        values["headerbar_shadow_color"] = "#112233"
        css = render_gtk4(
            Palette(values),
            Geometry(headerbar_shadow=True, headerbar_shadow_blur=6, headerbar_shadow_alpha=50),
        )
        self.assertIn("rgb(17 34 51 / 0.50)", css)

    def test_old_palette_keeps_line_as_header_shadow(self) -> None:
        palette = Palette.from_dict({"headerbar_line": "#ABCDEF"}, presets()[0].palette)
        self.assertEqual(palette["headerbar_shadow_color"], "#ABCDEF")
        kept = Palette.from_dict(
            {"headerbar_line": "#ABCDEF", "headerbar_shadow_color": "#010203"},
            presets()[0].palette,
        )
        self.assertEqual(kept["headerbar_shadow_color"], "#010203")

    def test_fonts_are_optional_and_quoted(self) -> None:
        preset = presets()[0]
        plain = render_gtk4(preset.palette, preset.geometry)
        self.assertNotIn("font-family", plain)
        fonts = Fonts(
            interface="Inter",
            interface_size=15,
            monospace="Adwaita Mono",
            monospace_size=13,
            title="Cantarell",
        )
        css4 = render_gtk4(preset.palette, preset.geometry, fonts=fonts)
        css3 = render_gtk3(preset.palette, preset.geometry, fonts=fonts)
        for css in (css4, css3):
            assert_sane(css)
            self.assertIn('font-family: "Inter", sans-serif', css)
            self.assertIn("font-size: 15px", css)
            self.assertIn('font-family: "Adwaita Mono", monospace', css)
            self.assertIn("font-size: 13px", css)
            self.assertIn('font-family: "Cantarell", sans-serif', css)
        injected = Fonts.from_dict({"interface": 'Inter"; color: red'})
        self.assertEqual(injected.interface, "")
        poisoned = render_gtk4(preset.palette, preset.geometry, fonts=injected)
        self.assertNotIn("color: red", poisoned)
        self.assertNotIn("font-family", poisoned)

    def test_palette_rejects_short_map(self) -> None:
        with self.assertRaises(KeyError):
            Palette({"window_bg": "#FFFFFF"})


if __name__ == "__main__":
    unittest.main()
