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
/workspace/                      # 🔝 КОРНЕВАЯ ДИРЕКТОРИЯ ПРОЕКТА
├── .ai/                         # 🧠 Кросс-AI память (читают все ассистенты)
│   └── memory/
│       ├── README.md            # Инструкция по работе с памятью
│       ├── business/            # Бизнес-решения (ниша, цены, экономика)
│       │   └── .gitkeep
│       ├── tech/                # Технические решения (стек, БД, API) + [Память]
│       │   ├── .gitkeep
│       │   └── 2026-05-12_playwright-qa-framework-setup.md  # ⭐ ПАМЯТЬ: Настройка фреймворка
│       ├── design/              # UI/UX-решения, дизайн-токены
│       │   └── .gitkeep
│       └── iterations/          # Лог итераций
│           └── .gitkeep
├── .cursor/                     # Cursor-специфичные настройки
│   └── prompts/                 # Шаблоны промптов для AI
│       ├── README.md
│       └── new-chat-template.md
├── .github/workflows/           # 🔄 CI pipeline
│   └── ci.yml                   # GitHub Actions workflow
├── scripts/tms_reporter.py      # 📤 JUnit → TMS sync
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
├── artifacts/                   # Рабочая площадка (артефакты разработки)
│   ├── README.md
│   ├── decisions/               # ADR
│   ├── flows/                   # User flows
│   ├── mockups/                 # Wireframes
│   ├── pages/                   # HTML-прототипы
│   └── thinking/                # Размышления, манифесты
├── AGENTS.md                    # 🤖 AI rules
├── Dockerfile                   # 🐳 Container
├── pyproject.toml               # 📦 Dependencies
├── .cursorrules                 # Правила для ИИ-генерации
├── .cursorrules.txt             # (дубль для совместимости)
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
- **Matrix Sharding:** Разделение тестов на 2 runner'а (оптимизация для free tier)
- **Caching:** pip зависимости + браузеры Playwright
- **Retry Logic:** `--reruns 2 --reruns-delay 3` для flaky тестов
- **Artifacts:** Скриншоты, traces, Allure результаты
- **TMS Sync:** Авто-отправка результатов во внешнюю TMS через REST API

### Jobs workflow
1. **test:** Параллельные шарды с `fail-fast: false`
2. **report:** Генерация HTML отчёта Allure
3. **tms-sync:** Отправка результатов в TMS (TestRail/Qase/etc.)

---

## 📊 Отчётность

### Allure Report
```bash
# Локально
allure serve allure-results

# CI: Деплой на GitHub Pages
```

### Playwright Trace Viewer
```bash
# Просмотр traces из упавших тестов
playwright show-trace trace.zip
```

### TMS Integration
Маркировка тестов TMS ID:
```python
@pytest.mark.tms_id("TC-123")
def test_login():
    ...
```

TMS-репортер:
- читает JUnit XML из CI
- извлекает `tms_id` из pytest-маркеров на уровне отдельных тестов
- отправляет результаты в TMS через REST API

Для portfolio/demo-сценария рекомендуем [Qase](https://qase.io/).

Текущий принцип разметки:
- один тест = один `tms_id`
- file-level разметка больше не используется
- IDs должны оставаться стабильными при рефакторинге файла

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
| `DB_HOST` | Хост базы данных | `localhost` |
| `DB_PORT` | Порт базы данных | `5432` |
| `DB_NAME` | Имя базы данных | `qa_test` |
| `DB_USER` | Пользователь БД | `qa` |
| `DB_PASSWORD` | Пароль БД | `qa_pass` |
| `API_TOKEN` | Токен аутентификации API | — |
| `TMS_API_URL` | URL API TMS | — |
| `TMS_TOKEN` | Токен аутентификации TMS | — |

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

- [AGENTS.md](./AGENTS.md) — Правила для AI-ассистентов
- [.cursorrules](./.cursorrules) — Ограничения для AI-генерации кода

---

## 📄 Лицензия

MIT License
