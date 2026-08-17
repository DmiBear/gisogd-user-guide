#!/usr/bin/env bash
#
# Сборка статического сайта MkDocs в папку _site (задана в mkdocs.yml: site_dir).
#
# - при отсутствии mkdocs в системе создаётся виртуальное окружение .venv
#   и устанавливаются зависимости из requirements.txt.
#
set -euo pipefail

# --- Подготовка окружения ---------------------------------------------------
if ! command -v mkdocs >/dev/null 2>&1; then
    echo "MkDocs не найден в системе — создаём виртуальное окружение .venv"
    if [ ! -d .venv ]; then
        python3 -m venv .venv
    fi
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
fi

# --- Сборка -----------------------------------------------------------------
# Значение site_dir (_site) уже задано в mkdocs.yml.
echo "Сборка сайта ..."
mkdocs build --strict

echo "Готово. Статический сайт находится в папке _site/"
