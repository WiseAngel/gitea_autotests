# Решение: CI portfolio-ready + sdet-orchestrator bot integration

**Дата**: 2026-05-25
**Категория**: tech
**Статус**: Принято и реализовано

## Контекст
Фреймворк переведён в portfolio-ready состояние: shard CI, Allure GitHub Pages, совместимость с Telegram-ботом `sdet-orchestrator` (запуск тестов через `/run smoke|regression|e2e`).

## Ключевые технические решения

### Sharding
- `pytest-split>=0.9.0` (не `pytest-shard` — сломан в v0.1.2)
- Синтаксис: `--splits=2 --group=N`
- Matrix в CI: `browser × group` (2 groups)

### Build system
- Добавлен `[build-system]` с `setuptools.build_meta` в `pyproject.toml`
- Без него `uv pip install -e .` не устанавливает основные зависимости

### Зависимости для установки в CI
- `uv pip install --system -e ".[dev]"` — `-e` флаг обязателен
- Без `-e` устанавливаются только dev extras (ruff, mypy, pre-commit)

### Allure в CI
- `simple-elf/allure-report-action` — не использовать (Docker build падает на GH runners)
- Правильный способ: `npm install -g allure-commandline` → `allure generate`
- Merge артефактов: `find ... -type d -name "allure-results"` (не `find ... -name "*.json"`)

### mypy и factory-boy
- `factory-boy` не имеет type stubs
- Решение через `pyproject.toml` overrides, не через `# type: ignore` в коде:
  ```toml
  [[tool.mypy.overrides]]
  module = "src.testing.factories"
  ignore_errors = true
  [[tool.mypy.overrides]]
  module = "factory.*"
  ignore_missing_imports = true
  ```

### Маркеры для бота
| Бот suite | pytest маркер | Тестов | Слои |
|-----------|--------------|--------|------|
| `smoke`   | `-m smoke`   | 21     | component |
| `regression` | `-m regression` | 11 | integration + e2e |
| `e2e`     | `-m e2e`     | 7      | e2e |

### Authenticated fixture
- `authenticated_page` в `pytest_support.py`
- Form-based login (не cookie injection) — надёжнее
- Требует `GITEA_USERNAME` + `GITEA_PASSWORD` (не только токен)
- Предварительная валидация токена через API перед UI логином

## Связанные файлы
- `pyproject.toml` — build-system, pytest-split, mypy overrides
- `src/testing/pytest_support.py` — authenticated_page fixture
- `src/pages/gitea_components.py` — 5 новых компонентов
- `.github/workflows/ci.yml` — shard matrix, Allure Pages
- `.github/workflows/e2e.yml` — e2e regression workflow

## История изменений
- 2026-05-25: создано
