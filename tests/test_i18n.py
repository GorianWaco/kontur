import unittest

from kontur.colors import presets
from kontur.i18n import LANGUAGES, get_language, message_keys, set_language, t


class LanguageTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_language("pl")

    def test_every_string_has_six_languages(self) -> None:
        self.assertEqual(len(LANGUAGES), 6)
        self.assertGreater(len(message_keys()), 40)
        for code, _name in LANGUAGES:
            set_language(code)
            self.assertEqual(get_language(), code)
            for key in message_keys():
                self.assertNotEqual(t(key), key, f"{code} {key}")

    def test_unknown_language_falls_back(self) -> None:
        self.assertEqual(set_language("xx"), "pl")
        self.assertEqual(t("page_window"), "Okno")

    def test_five_dark_presets(self) -> None:
        ids = [item.id for item in presets()]
        for preset_id in ("night", "coal", "forest", "plum", "storm"):
            self.assertIn(preset_id, ids)
        dark = [item for item in presets() if item.id in ("night", "coal", "forest", "plum", "storm")]
        self.assertEqual(len(dark), 5)
        for item in dark:
            self.assertTrue(item.geometry.shadow_enabled)
            self.assertTrue(item.palette["window_bg"].startswith("#"))
            self.assertNotEqual(item.palette["window_fg"], item.palette["window_bg"])


if __name__ == "__main__":
    unittest.main()
