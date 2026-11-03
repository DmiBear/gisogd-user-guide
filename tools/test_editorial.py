"""Reader-facing copy and explicit editorial requirements; no runtime claims."""
import re
import unittest

import yaml

from check_docs import ROOT


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class EditorialChecks(unittest.TestCase):
    def test_reader_orientation_explains_system_site_and_tasks(self):
        intro = read("docs/start-here.md").split("## Последовательность изучения", 1)[0]
        for required in (
            "Государственной информационной системы обеспечения градостроительной деятельности",
            "органами исполнительной власти и местного самоуправления",
            "централизованное хранение", "электронное руководство пользователя",
            "найти заявку или документ", "заполнить карточку", "установить связь между записями",
        ):
            self.assertIn(required, intro)

    def test_about_has_no_reader_facing_revision_date_or_training_section(self):
        source = read("docs/about.md")
        self.assertNotIn("ГИСОГД", source)
        self.assertNotIn("## Программа обучения", source)
        self.assertIn("{ #applicability }", source)
        self.assertNotIn("Номер сборки", source)
        notice = source.split("## Обращение к администраторам системы { #applicability }", 1)[1].split("## Автор", 1)[0].strip()
        self.assertEqual(notice, "Если у вас возникли вопросы по работе в Системе или технические сложности, обратитесь к администраторам системы.")
        self.assertIn('[«Обращение к администраторам системы»](about.md#applicability)', read("docs/help.md"))
        for path in (ROOT / "docs").rglob("*.md"):
            self.assertIsNone(re.search(r"дата (?:последней )?редакции|дата последнего обновления", path.read_text(encoding="utf-8"), re.I), path.name)

    def test_training_uses_full_system_name(self):
        self.assertEqual(read("docs/training/index.md").splitlines()[0],
                         "# Программа обучения работе в Государственной информационной системе обеспечения градостроительной деятельности")

    def test_beta_note_does_not_change_training_scope(self):
        source = read("docs/training/index.md")
        self.assertIn('<p class="training-status" role="note"><small>Бета-версия. Находится в разработке.</small></p>', source)
        self.assertIn("10 вебинаров", source)
        self.assertIn("22 академических часа", source)
        self.assertIn("в пределах назначенных ролей и полномочий", source)

    def test_system_composition_label_is_consistent(self):
        config = yaml.safe_load(read("mkdocs.yml"))
        self.assertIn("Состав системы", {key for row in config["nav"] for key in row})
        self.assertEqual(read("docs/gisogd/index.md").splitlines()[0], "# Состав системы")
        for name in ("README.md", "docs/training/webinars-1-5.md"):
            self.assertIn("Состав системы", read(name))
            self.assertNotIn("Состав ГИСОГД", read(name))
        # A website navigation label is not the name of the real application tab.
        self.assertIn("«Документы ГИСОГД»", read("docs/gisogd/document-placement.md"))


if __name__ == "__main__":
    unittest.main()
