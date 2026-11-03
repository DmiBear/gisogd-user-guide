"""Negative regression cases for the guide checks."""
import tempfile
import unittest
from pathlib import Path

from check_docs import HOME_TITLE, ROOT, Page, check_built, check_editorial_tone, check_home, first_mentions, validate_figures


class GuideChecks(unittest.TestCase):
    def test_technical_catalogue(self):
        source = (ROOT / "docs/index.md").read_text(encoding="utf-8")
        self.assertEqual(check_home(source), [])

    def test_official_title_is_not_abbreviated(self):
        source = (ROOT / "docs/index.md").read_text(encoding="utf-8")
        self.assertTrue(check_home(source.replace(HOME_TITLE, "Руководство пользователя ГИСОГД")))

    def test_description_cannot_be_removed(self):
        source = (ROOT / "docs/index.md").read_text(encoding="utf-8")
        self.assertTrue(check_home(source.replace('class="gisogd-home__description"', 'class="missing-description"')))

    def test_missing_registry_link(self):
        source = (ROOT / "docs/index.md").read_text(encoding="utf-8")
        self.assertTrue(check_home(source.replace('href="gisogd/registries/section-8/"', 'href="wrong/"')))

    def test_catalogue_headings_are_still_required(self):
        source = (ROOT / "docs/index.md").read_text(encoding="utf-8")
        self.assertTrue(check_home(source.replace('<h2 id="applications">', '<h2 id="wrong">')))

    def test_redundant_homepage_jump_row_is_not_restored(self):
        source = (ROOT / "docs/index.md").read_text(encoding="utf-8")
        self.assertTrue(check_home(source + '<nav class="gisogd-home-nav"></nav>'))

    def test_landing_page_regression(self):
        source = (ROOT / "docs/index.md").read_text(encoding="utf-8")
        self.assertTrue(check_home(source + '<div class="gisogd-task-card"></div>'))

    def test_promotional_wording(self):
        self.assertTrue(check_editorial_tone({"sample": "Выберите свою задачу"}))

    def test_ui_names_are_not_marketing(self):
        self.assertEqual(check_editorial_tone({"sample": "На главном окне расположен блок «Популярные разделы»."}), [])

    def rows(self):
        return [{"number": n, "caption": str(n), "alt": str(n)} for n in range(1, 151)]

    def test_correct_order(self):
        rows = self.rows()
        self.assertEqual(validate_figures(rows, rows), [])

    def test_first_reference_order_and_repeated_reference(self):
        self.assertEqual(first_mentions(["Сначала рисунок 1, затем рисунок 2.", "Снова рисунок 1 и рисунок 3."]), [1, 2, 3])

    def test_first_reference_catches_early_jump(self):
        self.assertNotEqual(first_mentions(["Рисунок 2. Рисунок 1."]), [1, 2])

    def test_swapped_figures(self):
        rows = self.rows()
        changed = rows.copy()
        changed[2], changed[3] = changed[3], changed[2]
        self.assertTrue(validate_figures(changed, rows))

    def test_missing_figure(self):
        rows = self.rows()
        self.assertTrue(validate_figures(rows[:-1], rows))

    def test_changed_media(self):
        rows = self.rows()
        changed = [dict(row) for row in rows]
        changed[0]["sha256"] = "changed"
        self.assertTrue(validate_figures(changed, rows))

    def test_caption_mismatch(self):
        rows = self.rows()
        rows[0]["alt"] = "wrong"
        self.assertTrue(validate_figures(rows, rows))

    def test_duplicate_ids(self):
        self.assertEqual(Page('<h1 id="same">One</h1><p id="same">Two</p>').duplicates, {"same"})

    def test_link_anchor_and_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Temporary regression fixtures only; never touch project sources.
            (root / "index.html").write_text('<a href="missing/">Bad</a><a href="#gone">Bad</a><img src="missing.png">', encoding="utf-8")
            errors, *_ = check_built(root)
            self.assertEqual(len(errors), 3)

    def test_valid_local_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text('<h1 id="ok">Title</h1><a href="#ok">OK</a><a href="https://example.invalid/">External</a>', encoding="utf-8")
            self.assertEqual(check_built(root)[0], [])


if __name__ == "__main__":
    unittest.main()
