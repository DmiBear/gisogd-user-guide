"""Check the publication boundary without deploying or accessing credentials."""

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://gisogd-user-guide.polakov1245.workers.dev/"
LEGACY = re.compile(r"github\s*pages|gh-deploy|gh-pages|https?://dmibear\.github\.io(?:/|$)", re.IGNORECASE)


def inspect_configuration(site, worker, workflow, sources, build_script):
    errors = []
    if site.get("site_url") != SITE_URL:
        errors.append("MkDocs site_url must use the current Cloudflare address")
    if site.get("site_dir") != "_site" or not site.get("strict"):
        errors.append("MkDocs must build strictly into _site")
    if worker.get("name") != "gisogd-user-guide":
        errors.append("Wrangler must target the existing Worker")
    assets = worker.get("assets", {})
    if assets.get("directory") != "./_site":
        errors.append("Wrangler must publish the MkDocs output directory")
    if assets.get("html_handling") != "auto-trailing-slash":
        errors.append("Wrangler must preserve directory-style documentation URLs")
    if assets.get("not_found_handling") != "404-page":
        errors.append("Missing routes must use the generated 404 page")
    triggers = workflow.get("on", {})
    if not {"push", "pull_request", "workflow_dispatch"}.issubset(triggers):
        errors.append("Check documentation on push, pull request and manual run")
    if workflow.get("permissions", {}).get("contents") != "read":
        errors.append("The checking workflow must not write to the repository")
    steps = workflow.get("jobs", {}).get("docs", {}).get("steps", [])
    commands = "\n".join(step.get("run", "") for step in steps)
    if "python -m mkdocs build --strict" not in commands:
        errors.append("The checking workflow must run a strict MkDocs build")
    if not any(step.get("uses", "").startswith("actions/upload-artifact@")
               and step.get("with", {}).get("path") == "_site/" for step in steps):
        errors.append("The checking workflow must retain the built site")
    if "wrangler deploy" in commands or "wrangler pages" in commands:
        errors.append("Publication belongs to Cloudflare, not the checking workflow")
    for name, text in sources.items():
        if LEGACY.search(text):
            errors.append(f"Obsolete publication instruction or URL: {name}")
    if build_script.startswith(b"\xef\xbb\xbf") or b"\r" in build_script:
        errors.append("build.sh must use LF without a UTF-8 BOM")
    return errors


def main():
    site = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    worker = json.loads((ROOT / "wrangler.jsonc").read_text(encoding="utf-8"))
    # BaseLoader keeps GitHub's 'on' key as a string instead of YAML 1.1 boolean.
    workflow_path = ROOT / ".github/workflows/check.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    paths = [ROOT / "README.md", ROOT / "DEVELOPMENT.md", ROOT / "mkdocs.yml", ROOT / "build.sh"]
    paths += list((ROOT / "docs").rglob("*.md"))
    paths += list((ROOT / ".github/workflows").glob("*.y*ml"))
    sources = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for p in paths}
    build_script = (ROOT / "build.sh").read_bytes()
    errors = inspect_configuration(site, worker, workflow, sources, build_script)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    # Negative cases prove that the migration checks catch actual regressions.
    bad_site = dict(site, site_url="https://old.example.invalid/")
    assert inspect_configuration(bad_site, worker, workflow, sources, build_script)
    bad_worker = dict(worker, assets=dict(worker["assets"], directory="./wrong-output"))
    assert inspect_configuration(site, bad_worker, workflow, sources, build_script)
    assert inspect_configuration(site, worker, workflow, {"old-workflow": "mkdocs gh-deploy --force"}, build_script)
    assert inspect_configuration(site, worker, workflow, {"old-url": "https://dmibear.github.io/gisogd-user-guide/"}, build_script)
    assert inspect_configuration(site, worker, workflow, sources, build_script.replace(b"\n", b"\r\n"))
    assert not inspect_configuration(site, worker, workflow, {"official-docs": "https://squidfunk.github.io/mkdocs-material/"}, build_script)
    print(f"PASS: Cloudflare publication configuration; {len(sources)} source files; 5 negative cases; official documentation links allowed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
