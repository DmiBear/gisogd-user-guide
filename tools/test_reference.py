"""Content/navigation regression checks, not GISOGD runtime acceptance tests."""
import hashlib
import json
import re
import unittest

from check_docs import ROOT, nav_pages
import yaml


def read(name):
    return (ROOT / "docs" / name).read_text(encoding="utf-8")


class ReferenceChecks(unittest.TestCase):
    def test_reference_pages_are_in_navigation(self):
        config = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
        actual = {name for name in nav_pages(config["nav"]) if name.startswith("reference/")}
        self.assertEqual(actual, {
            "reference/index.md", "reference/conventions.md", "reference/import.md",
            "reference/files-and-signature.md", "reference/application-statuses.md",
        })
        self.assertIn('href="introduction/#15"', read("index.md"))
        self.assertIn("../introduction.md#15", read("reference/index.md"))

    def test_all_14_tabs_link_to_their_own_instructions(self):
        section = read("gisogd/registries/section-13/index.md").split("{ #case-tabs }", 1)[1].split("Расшифровка", 1)[0]
        links = re.findall(r"^- \[([^]]+)\]\(([^)]+)\)", section, re.M)
        self.assertEqual(links, [
            ("Основное", "#54131"),
            ("Документы ГИСОГД", "../../document-placement.md#532"),
            ("Схема расположения земельного участка на кадастровом плане территории (СРЗУ)", "land-and-construction.md#54132"),
            ("Кадастровая выписка о земельном участке (КВЗУ)", "land-and-construction.md#54133"),
            ("Градостроительный план земельного участка (ГПЗУ)", "land-and-construction.md#54134"),
            ("Объекты капитального строительства", "land-and-construction.md#54135"),
            ("Разрешение на строительство", "permits.md#54136"),
            ("Разрешение на ввод объекта в эксплуатацию", "permits.md#54137"),
            ("Разрешение на отклонение от предельных параметров", "permits.md#54138"),
            ("Уведомление", "notifications.md#54139"),
            ("Публичные сервитуты", "additional.md#541310"),
            ("Технические условия", "additional.md#541311"),
            ("Приложения", "../../requests.md#523"),
            ("Связанные объекты", "../section-7.md#5473"),
        ])

    def test_glossary_definitions_are_unchanged(self):
        section = read("introduction.md").split("## 1.5", 1)[1]
        rows = [[re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cell).strip())
                 for cell in line.split("|")[1:-1]]
                for line in section.splitlines() if line.startswith("| ") and not line.startswith("| **")]
        self.assertEqual(len(rows), 53)
        digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        # Approved source table, before adding anchors; excludes formatting only.
        self.assertEqual(digest, "37ec5bfe67e190c6bce8761a09975777550813ee01b04764e2cb4e671a0e6a3e")

    def test_each_term_has_a_unique_anchor(self):
        anchors = re.findall(r'<span id="(term-[a-z-]+)">', read("introduction.md"))
        self.assertEqual(len(anchors), 53)
        self.assertEqual(len(set(anchors)), 53)
        self.assertTrue({"term-srzu", "term-kvzu", "term-gpzu", "term-oks", "term-zouit", "term-ep"}.issubset(anchors))

    def test_status_lists_are_distinct_and_exact(self):
        source = read("reference/application-statuses.md")
        journal = source.split("## Отбор по статусу в журнале", 1)[1].split("## Отбор по отправителю", 1)[0]
        card = source.split("## Изменение статуса в карточке заявления", 1)[1]
        self.assertEqual(re.findall(r"^- «([^»]+)»", journal, re.M), ["Все", "Новое", "Зарегистрировано", "В работе", "Исполнено", "Отказано"])
        self.assertEqual(re.findall(r"^- «([^»]+)»", card, re.M), ["Новое", "Зарегистрировано", "В работе", "Черновик", "Отправлено в ведомство", "Услуга оказана", "Отказ"])
        self.assertIn("условие отбора, а не статус отдельной заявки", journal)
        self.assertIn("не задают последовательность переходов", card)

    def test_sender_filter_is_not_a_workflow(self):
        section = read("reference/application-statuses.md").split("## Отбор по отправителю", 1)[1].split("## Изменение", 1)[0]
        paragraph = section.strip().split("\n\n", 1)[0]
        self.assertEqual(re.findall(r"«([^»]+)»", paragraph), ["Все", "Лично", "Почтовое отделение", "Электронная почта", "МФЦ", "ЕСМЭВ", "ПГУ", "Иные"])
        self.assertIn("не к этапу её обработки", section)

    def test_import_formats_keep_their_command_scope(self):
        source = read("reference/import.md")
        map_part, registry_part = source.split("## Загрузка материалов в карточке документа", 1)
        self.assertIn("MIF, DXF или TAB", map_part)
        self.assertIn("Импорт → WKT", map_part)
        self.assertNotIn("GML", map_part)
        self.assertNotIn("EPSG:3857", map_part)
        epsg_rows = [line for line in registry_part.splitlines() if line.startswith("|") and "EPSG:3857" in line]
        self.assertEqual(len(epsg_rows), 1)
        self.assertIn("Загрузить контуры функциональных зон", epsg_rows[0])
        self.assertIn("не является общим требованием", registry_part)
        self.assertIn("все ранее загруженные векторные данные текущего документа", registry_part)

    def test_reference_icons_do_not_duplicate_numbered_figures(self):
        for name in ("index", "conventions", "import", "files-and-signature", "application-statuses"):
            self.assertNotIn('class="doc-figure"', read(f"reference/{name}.md"))
        icons = re.findall(r"!\[([^]]+)\]\(([^)]+)\)\{ \.ui-icon \}", read("reference/conventions.md"))
        self.assertEqual(len(icons), 10)
        self.assertTrue(all(alt and "/images/ui/" in href for alt, href in icons))

    def test_file_preview_and_signature_scope(self):
        source = read("reference/files-and-signature.md")
        self.assertIn("PDF, JPG, PNG", source)
        self.assertIn("Выгрузка файла и просмотр вне системы", source)
        self.assertIn("Поля заполняются автоматически при загрузке подписанного файла", source)
        self.assertIn("Архив ЭП", source)
        self.assertIn("не заменяет инструкцию по подписанию файла или проверке действительности подписи", source)


if __name__ == "__main__":
    unittest.main()
