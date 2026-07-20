# 🎭 Playwright QA Automation Framework

> Production-ready фреймворк для E2E-тестирования self-hosted Gitea на базе Playwright, pytest с интеграцией API/DB, Allure и CI/CD.

---

## 🚀 Быстрый старт

### Необходимые требования
- Python 3.11+
- Docker & Docker Compose (для локального Gitea, Postgres и Redis)
- Node.js (опционально, для генерации Allure-отчёта локально)

### Установка

```bash
# 1. Клонируйте репозиторий и перейдите в него
git clone <repo-url> playwright-qa
cd playwright-qa

# 2. Установите uv (если ещё не установлен)
pip install uv

# 3. Создайте виртуальное окружение
uv venv

# 4. Активируйте окружение
# Для PowerShell:
.\.venv\Scripts\Activate.ps1
# Для CMD:
# .venv\Scripts\activate.bat
# Для Bash/Zsh:
# source .venv/bin/activate

# 5. Установите зависимости (включая dev-зависимости)
uv pip install -e ".[dev]"

# 6. Установите браузеры Playwright
playwright install chromium firefox

# 7. Скопируйте пример конфигурации
cp .env.example .env
# Или в PowerShell, если cp не работает:
# Copy-Item .env.example .env
```

### Запуск тестов

```bash
# Все тесты
pytest

# Только component/integration/e2e слои
pytest -m component
pytest -m integration
pytest -m e2e

# Примеры более точных селекторов
pytest -m "component and ui"
pytest -m "integration and api"
pytest -m "integration and ui"
pytest -m "e2e and api"
pytest -m "e2e and ui"

# Только smoke-тесты
pytest -m smoke

# В режиме с UI (headed mode)
pytest --headless=false

# Параллельный запуск (локально)
pytest -n auto

# Генерация Allure отчёта
pytest --alluredir=allure-results
allure serve allure-results
```

---

## 🏗 Архитектура

```
┌───────────────────────────────┐    ┌──────────────┐    ┌─────────────┐
│ Test Files                    │───▶│   Pytest     │───▶│ Playwright  │
│ component / integration / e2e │    │  Fixtures    │    │  Browser    │
└───────────────────────────────┘    └──────────────┘    └─────────────┘
                   │                         │                    │
                   ▼                         ▼                    ▼
            ┌──────────┐              ┌──────────┐         ┌──────────┐
            │ API      │              │ Database │         │  Test    │
            │ Clients  │              │ Engine   │         │  Data    │
            └──────────┘              └──────────┘         └──────────┘
```

### Зачем нужен DB-слой

DB-слой используется для изоляции тестовых данных и безопасной подготовки фикстур:
- `DatabaseEngine` создаёт async SQLAlchemy engine
- `db_session` даёт транзакцию с auto-rollback
- тесты могут создавать временные данные, не загрязняя окружение
- это особенно важно для integration/e2e сценариев, где нужны стабильные предусловия

**Стек:**
- **Core:** Python 3.11+, pytest + pytest-playwright
- **Config:** pydantic-settings + .env (строгая валидация)
- **API Client:** httpx (async)
- **Database:** SQLAlchemy 2.x + asyncpg
- **Test Data:** factory_boy + faker
- **Logging:** structlog (JSON в CI)
- **Reporting:** Allure + Playwright Trace Viewer

---

## 📁 Структура проекта

```
playwright-qa/
├── .github/workflows/           # 🔄 CI pipeline
│   └── ci.yml                   # GitHub Actions workflow
├── scripts/seed_gitea.py        # 🌱 Тестовые данные для CI
├── src/                         # 🔌 Исходный код (clients, utils, pages)
│   ├── api/                     # API клиенты
│   │   └── clients.py           # HTTPX async client
│   ├── db/                      # Database engine
│   │   └── engine.py            # SQLAlchemy engine
│   ├── config/                  # Конфигурация
│   │   └── settings.py          # Pydantic settings
│   ├── utils/                   # Утилиты
│   │   └── logger.py            # Централизованное логирование
│   └── pages/                   # 🧩 Page Object компоненты
│       └── base_component.py    # Базовый класс для всех компонентов
├── tests/                       # 🧪 Тесты
│   ├── components/              # 🧩 Component layer (UI + lightweight helpers)
│   │   ├── test_gitea_components.py
│   │   └── test_gitea_helpers.py
│   ├── e2e/                     # 🎬 E2E сценарии (UI + API)
│   │   ├── test_gitea_ui.py
│   │   └── test_gitea_api.py
│   ├── integration/             # 🔗 Integration сценарии (UI + API)
│   │   ├── test_gitea_api.py
│   │   └── test_gitea_ui.py
│   └── conftest.py              # 📦 Глобальные фикстуры (тонкий re-export)
├── CONTRIBUTING.md              # 📐 Конвенции и правила разработки
├── Dockerfile                   # 🐳 Container
├── pyproject.toml               # 📦 Dependencies
└── .env.example                 # 🔑 Config template
```

---

## 🧪 Паттерны тестирования

### Component-Based POM

```python
from src.pages.base_component import BaseComponent

class HeaderComponent(BaseComponent):
    def __init__(self, page):
        super().__init__(page, "header")
    
    @property
    def logo(self):
        return self._child(".logo")
    
    def click_logo(self):
        self.logo.click()

# Использование в тесте
def test_navigation(page):
    header = HeaderComponent(page)
    header.expect_visible()
    header.click_logo()
```

### API Pre-conditions

```python
from src.api.clients import APIClient
from src.testing.factories import GiteaRepositoryFactory

@pytest.mark.asyncio
async def test_user_flow(page):
    # Создание пользователя через API
    repo_data = GiteaRepositoryFactory.build()
    
    async with APIClient() as api:
        response = await api.post("/user/repos", json=repo_data)
        repo_name = response.json()["name"]
    
    # Продолжение UI теста с созданным пользователем
    page.goto(f"/{settings.gitea_username}/{repo_name}")
```

### DB Transaction Isolation

```python
async def test_with_db(db_session):
    async with db_session as session:
        # Все изменения автоматически откатываются после теста
        result = await session.execute(query)
```

---

## 🔄 CI/CD Pipeline

### Возможности GitHub Actions
- **Matrix Sharding:** Разделение тестов на несколько runner'ов через `pytest-split` (оптимизация для free tier)
- **Caching:** pip/uv зависимости + браузеры Playwright
- **Retry Logic:** `--reruns 2 --reruns-delay 3` для flaky тестов
- **Artifacts:** Скриншоты, traces, Allure-результаты
- **Qase TestOps:** результаты каждого прогона автоматически отправляются в Qase через `qase-pytest`

### Jobs workflow
1. **lint:** ruff + mypy перед запуском тестов
2. **test (api/ui/component):** параллельные шарды с `fail-fast: false`, каждый шард сам репортит в Qase
3. **report:** генерация HTML-отчёта Allure из объединённых `allure-results`

---

## 📊 Отчётность

### Allure Report

```bash
# Локально
allure serve allure-results
```

В CI отчёт после каждого прогона на `main` публикуется на GitHub Pages:
**https://wiseangel.github.io/gitea_autotests/allure/**

### Playwright Trace Viewer
```bash
# Просмотр traces из упавших тестов
playwright show-trace trace.zip
```

### Интеграция с Qase (TMS)

Репортинг в [Qase](https://qase.io/) реализован через официальный плагин [`qase-pytest`](https://github.com/qase-tms/qase-python) — отдельного скрипта-синхронизатора нет, плагин отправляет результаты напрямую во время прогона pytest.

**Как маркировать тест ID из Qase:**

```python
from qase.pytest import qase

@qase.id(20)
def test_repository_issue_search_flow() -> None:
    """Verify a complete API-only repository flow."""
    ...
```

- один тест = один `@qase.id(N)`, где `N` — числовой ID test case в проекте Qase;
- тест без `@qase.id` всё равно репортится в Qase (создаётся как ad-hoc результат), но не привязывается к существующему test case;
- ID должен оставаться стабильным при рефакторинге/переименовании файла — переезд теста не меняет его номер.

**Как это настроить локально:**

```bash
# Отправка в Qase TestOps (нужен реальный токен и project code)
export QASE_MODE=testops
export QASE_TESTOPS_PROJECT=GITEA
export QASE_TESTOPS_API_TOKEN=<your-qase-token>
export QASE_TESTOPS_RUN_TITLE="Local run"
pytest -m smoke

# Прогон без отправки в Qase (по умолчанию)
export QASE_MODE=off
pytest
```

**Как это настроено в CI:**

Каждый job с тестами (`ci.yml`, `e2e.yml`) передаёт плагину переменные окружения на шаге запуска pytest:

| Переменная | Значение | Смысл |
|---|---|---|
| `QASE_MODE` | `testops` | включает отправку результатов в Qase TestOps |
| `QASE_TESTOPS_PROJECT` | `GITEA` | код проекта в Qase |
| `QASE_TESTOPS_API_TOKEN` | `${{ secrets.TMS_TOKEN }}` | токен, хранится в GitHub Secrets, никогда не в коде |
| `QASE_TESTOPS_RUN_TITLE` | например `API tests shard 1` | заголовок конкретного run в Qase — по одному на job/shard |

Каждый CI-шард создаёт свой run в Qase (по названию из `QASE_TESTOPS_RUN_TITLE`) — это осознанный выбор ради независимости шардов; объединять раны в один нужно на стороне Qase (или через `QASE_TESTOPS_RUN_ID`, если хотите репортить все шарды в один и тот же run).

---

## ⚙️ Конфигурация

### Переменные окружения (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | URL Gitea | `https://gitea.com` |
| `API_BASE_URL` | URL API (опционально) | `https://gitea.com/api/v1` |
| `BROWSER` | Тип браузера | `chromium` |
| `HEADLESS` | Headless режим | `true` |
| `TIMEOUT` | Таймаут по умолчанию (мс) | `30000` |
| `SLOW_MO` | Замедление действий Playwright (мс), для отладки | `0` |
| `DB_HOST` | Хост базы данных | `localhost` |
| `DB_PORT` | Порт базы данных | `5432` |
| `DB_NAME` | Имя базы данных | `qa_test` |
| `DB_USER` | Пользователь БД | `qa` |
| `DB_PASSWORD` | Пароль БД | `qa_pass` |
| `API_TOKEN` | Токен аутентификации API | — |
| `GITEA_USERNAME` | Логин для UI-логина в Gitea | — |
| `GITEA_PASSWORD` | Пароль для UI-логина в Gitea | — |

Переменные для отправки результатов в Qase (см. [«Интеграция с Qase»](#-отчётность)) задаются отдельно, не через `.env` — используются напрямую в CI/локальном окружении: `QASE_MODE`, `QASE_TESTOPS_PROJECT`, `QASE_TESTOPS_API_TOKEN`, `QASE_TESTOPS_RUN_TITLE`.

---

## 🎯 Ключевые принципы

1. **No Global State:** Весь browser/context/page управляется через фикстуры
2. **No time.sleep():** Использовать Playwright auto-waits и expect()
3. **Component-Based:** Переиспользуемые UI компоненты, не page objects
4. **API First:** Тестовые данные через API, не UI
5. **Auto-Rollback:** DB транзакции откатываются после каждого теста
6. **No Hardcoding:** Все данные параметризированы или генерируются
7. **Strict Typing:** mypy --strict enforced
8. **CI Optimized:** Shard-based parallelism (без xdist в CI)

---

## 📈 Метрики

| Metric | Target |
|--------|--------|
| Время выполнения тестов | <10 мин (полный набор) |
| Flaky rate | <2% |
| Code coverage | >80% (business logic) |
| CI success rate | >95% |

---

## 🔗 Документация

- [CONTRIBUTING.md](./CONTRIBUTING.md) — конвенции и правила разработки тестов

---

## 📄 Лицензия

MIT License
