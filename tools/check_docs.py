"""Check guide links, navigation, figure order and unchanged media. No network access."""
import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIGURE = re.compile(r'<figure class="doc-figure".*?</figure>', re.S)
IMAGE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
CAPTION = re.compile(r'<figcaption>(.*?)</figcaption>', re.S)
HOME_TITLE = 'Руководство пользователя по системе "Государственная информационная система обеспечения градостроительной деятельности"'
HOME_PURPOSE = 'Система предназначена для сбора, учёта, хранения и размещения градостроительных сведений, документов и материалов. Система используется органами исполнительной власти и местного самоуправления при ведении реестров и предоставлении государственных и муниципальных услуг.'


def check_home(source):
    errors = []
    if re.findall(r"^# (.+)$", source, re.M) != [HOME_TITLE]:
        errors.append("Homepage must use the exact official guide title")
    description = re.search(r'<div class="gisogd-home__description"[^>]*>(.*?)</div>', source, re.S)
    if not description or len(re.sub(r"\s+", " ", description[1]).strip()) < 150:
        errors.append("Homepage must explain the system purpose and guide scope")
    if not description or HOME_PURPOSE not in description[1]:
        errors.append("Homepage must preserve the user-approved purpose paragraph")
    divider = re.search(r'<hr class="gisogd-home-divider"\s*/?>', source)
    catalogue = source.find('<div class="gisogd-catalog">')
    if not description or not divider or not (description.end() < divider.start() < catalogue):
        errors.append("Blue divider must separate the description from the catalogue")
    for required in ('href="start-here/"', 'href="quickstart/"', 'href="gisogd/requests/"', 'href="gisogd/document-placement/"', 'href="operations/map/"', 'href="introduction/#15"', 'href="reference/"'):
        if required not in source:
            errors.append(f"Homepage instruction/context missing: {required}")
    for group in ("applications", "registries", "operations", "map", "getting-started", "training"):
        if f'<h2 id="{group}">' not in source:
            errors.append(f"Homepage catalogue group missing: {group}")
    columns = [re.findall(r'<h2 id="([^"]+)">', column)
               for column in source.split('<div class="gisogd-catalog__column">')[1:]]
    if columns != [["getting-started", "operations", "training"], ["registries"], ["applications", "map"]]:
        errors.append("Group orientation, operations and training on the left; applications and map on the right")
    registries = re.search(r'<nav class="gisogd-catalog-links" aria-label="Реестры документов">(.*?)</nav>', source, re.S)
    if not registries or 'href="gisogd/overview/"' not in registries[1] or "gisogd-catalog-section__reference" in source:
        errors.append("Registry overview must be a regular catalogue link, not a separated footer")
    for number in range(1, 19):
        target = "section-13/" if number == 13 else f"section-{number}/"
        if f'href="gisogd/registries/{target}"' not in source:
            errors.append(f"Homepage registry link missing: {number}")
    if "gisogd-home-nav" in source:
        errors.append("Do not restore the redundant homepage jump-link row")
    if any(token in source for token in ("gisogd-button", "gisogd-task-card", "gisogd-start-strip", "gisogd-eyebrow")):
        errors.append("Homepage must remain a technical catalogue, not a promotional landing page")
    return errors


def check_editorial_tone(sources):
    # Match presentation copy, not real UI names such as «Популярные разделы».
    promotional = re.compile(r"добро пожаловать|выберите свою задачу|освойте основные действия|нужен определённый реестр|изучаете систему\?|портфолио", re.I)
    return [f"Promotional wording in {name}" for name, source in sources.items() if promotional.search(source)]


def nav_pages(nav):
    for entry in nav:
        for value in entry.values():
            if isinstance(value, str):
                yield value
            else:
                yield from nav_pages(value)


def figures(root, pages):
    result = []
    for name in pages:
        path = root / "docs" / name
        source = path.read_text(encoding="utf-8")
        for block in FIGURE.finditer(source):
            alt, href = IMAGE.search(block[0]).groups()
            caption = CAPTION.search(block[0])[1].strip()
            number = int(re.match(r"Рисунок (\d+) —", caption)[1])
            asset = (path.parent / href).resolve()
            result.append({
                "id": f"GIS-FIG-{number:03}", "number": number, "page": name,
                "asset": asset.relative_to(root / "docs").as_posix(),
                "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
                "caption": caption, "alt": alt, "ui_version": None,
            })
    return result


def validate_figures(actual, expected):
    errors = []
    sequence = list(range(1, len(expected) + 1))
    if not expected or [row["number"] for row in expected] != sequence or [row["number"] for row in actual] != sequence:
        errors.append("Figures must occur exactly once, in the approved sequential navigation order")
    if actual != expected:
        errors.append("Figure page, caption, image, hash or applicability differs from the approved manifest")
    if any(row["caption"] != row["alt"] for row in actual):
        errors.append("Figure alt text must match its caption")
    return errors


def first_mentions(sources):
    seen = set()
    ordered = []
    for source in sources:
        for match in re.finditer(r"рисун\w*\s+(\d+)", FIGURE.sub("", source), re.I):
            number = int(match[1])
            if number not in seen:
                seen.add(number)
                ordered.append(number)
    return ordered


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicates = set()
        self.links = []
        self.images = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        anchor = attrs.get("id")
        if anchor:
            if anchor in self.ids:
                self.duplicates.add(anchor)
            self.ids.add(anchor)
        for key in ("href", "src"):
            if attrs.get(key) and tag != "iframe":
                self.links.append(attrs[key])
        if tag == "img":
            self.images.append(attrs)


def check_built(site):
    pages = {p.resolve(): Page(p.read_text(encoding="utf-8")) for p in site.rglob("*.html")}
    errors = []
    references = 0
    for path, page in pages.items():
        if page.duplicates:
            errors.append(f"Duplicate IDs in {path.relative_to(site)}: {page.duplicates}")
        for href in page.links:
            url = urlsplit(href)
            if url.scheme or url.netloc or href == "#":
                continue
            references += 1
            local = unquote(url.path)
            target = (site / local.lstrip("/") if local.startswith("/") else path.parent / local).resolve() if local else path
            if target.is_dir():
                target /= "index.html"
            if not target.is_file():
                errors.append(f"Missing target: {path.relative_to(site)} -> {href}")
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f"Missing anchor: {path.relative_to(site)} -> {href}")
    return errors, len(pages), references, pages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    site = args.site_dir.resolve()
    config = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    pages = list(nav_pages(config["nav"]))
    errors = []
    if len(pages) != len(set(pages)):
        errors.append("Navigation contains duplicate pages")
    sources = {p.relative_to(ROOT / "docs").as_posix() for p in (ROOT / "docs").rglob("*.md")}
    if sources != set(pages):
        errors.append(f"Navigation mismatch: {sources.symmetric_difference(pages)}")
    manifest = json.loads((ROOT / "evidence/media-manifest.json").read_text(encoding="utf-8"))
    actual = figures(ROOT, pages)
    errors += validate_figures(actual, manifest["figures"])
    source_texts = [(ROOT / "docs" / name).read_text(encoding="utf-8") for name in pages]
    if first_mentions(source_texts) != list(range(1, len(manifest["figures"]) + 1)):
        errors.append("First textual figure references must follow the approved reading order")
    # Confirm each figure is introduced in its own instruction before it appears.
    for name in pages:
        source = (ROOT / "docs" / name).read_text(encoding="utf-8")
        if "\ufffd" in source:
            errors.append(f"Replacement character in {name}")
        if any(re.search(r"(?:раздел[а-я]*|пункт[а-я]*)\s+\d+(?:\.\d+)+", line, re.I) for line in source.splitlines() if not line.startswith("#")):
            errors.append(f"Unnamed numbered cross-reference in {name}")
        levels = [len(match[1]) for match in re.finditer(r"^(#{1,6}) ", source, re.M)]
        if levels and (levels[0] != 1 or any(b > a + 1 for a, b in zip(levels, levels[1:]))):
            errors.append(f"Skipped heading level in {name}")
        for block in FIGURE.finditer(source):
            number = int(re.match(r"Рисунок (\d+) —", CAPTION.search(block[0])[1])[1])
            preceding = FIGURE.sub("", source[:block.start()])
            if not re.search(rf"рисун\w*\s+{number}(?!\d)", preceding, re.I):
                errors.append(f"Figure {number} has no preceding reference in {name}")
    metadata = json.loads((ROOT / "evidence/documentation.json").read_text(encoding="utf-8"))
    if metadata.get("ui_version") is not None or metadata.get("runtime_verified") is not False:
        errors.append("Do not claim an unverified application version or runtime check")
    if not site.is_dir():
        errors.append(f"Build output is missing: {site}")
        compiled, references, built = 0, 0, {}
    else:
        found, compiled, references, built = check_built(site)
        errors += found
        for old in json.loads((ROOT / "evidence/legacy-anchors.json").read_text(encoding="utf-8")):
            path = (site / old["page"]).resolve()
            if path not in built or not set(old["anchors"]).issubset(built[path].ids):
                errors.append(f"Legacy bookmarks lost: {old['page']}")
    errors += check_home((ROOT / "docs/index.md").read_text(encoding="utf-8"))
    errors += check_editorial_tone(dict(zip(pages, source_texts)))
    if errors:
        print("\n".join(errors))
        return 1
    print(f"PASS: {len(pages)} navigation pages; {compiled} HTML pages; {references} local links/assets; {len(actual)} ordered figures and media hashes; legacy bookmarks; applicability and homepage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
