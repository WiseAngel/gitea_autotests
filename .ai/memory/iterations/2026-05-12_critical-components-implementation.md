# [ПАМЯТЬ] Сессия: Критические компоненты фреймворка

## Дата сессии
2026-05-12 13:22
Сессия разработки критических компонентов для эталонного шаблона автотестов.

## Цель сессии
Завершить разработку критических компонентов для создания эталонного шаблона автотестов:
1. CI/CD пайплайн для автоматического запуска тестов
2. Централизованное логирование
3. Интеграционные тесты с реальным API
4. Компонентные тесты UI элементов
5. Обновление документации структуры проекта

## Выполненные действия

### 1. CI/CD Pipeline (GitHub Actions)

**Файл:** `.github/workflows/ci.yml`

**Возможности:**
- Автоматический запуск при push/PR в main/master
- Установка uv, создание venv, установка зависимостей
- Установка браузеров Playwright и системных зависимостей
- Запуск linting (ruff) и type checking (mypy)
- Параллельный запуск smoke, component, integration тестов
- Загрузка артефактов: playwright-report, скриншоты при失败

**Структура workflow:**
```yaml
- Checkout → Python setup → uv install → venv → dependencies
- Playwright install → install-deps → .env.example → .env
- ruff check → mypy → pytest (smoke/components/integration)
- Upload artifacts (report + screenshots on failure)
```

### 2. Централизованное логирование

**Файлы:** `src/utils/logger.py`, `src/utils/__init__.py`

**Функционал:**
- `setup_logger()` — настройка логгера с уровнем, файлом, форматом
- `get_logger(name)` — получение логгера по имени
- `default_logger` — глобальный логгер по умолчанию
- Поддержка консольного и файлового вывода
- Формат: `YYYY-MM-DD HH:MM:SS | LEVEL | name:line | message`

**Использование в тестах:**
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Запуск теста")
logger.debug(f"Данные: {data}")
logger.error("Ошибка выполнения")
```

### 3. Интеграционные тесты (API + DB)

**Файл:** `tests/integration/test_integration.py`

**Публичный API:** JSONPlaceholder (https://jsonplaceholder.typicode.com)

**Тесты:**
| Тест | Описание |
|------|----------|
| `test_get_posts_from_api` | Получение списка постов с лимитом |
| `test_get_single_post` | Получение одного поста по ID |
| `test_create_post_via_api` | Создание поста через POST |
| `test_database_connection_mock` | Mock-проверка подключения к БД |
| `test_integration_api_and_logging` | Комплексный: пользователи + посты + логи |

**Пример интеграции API + Логирование:**
```python
def test_integration_api_and_logging(self, api_client):
    logger.info("Запуск комплексного интеграционного теста")
    
    users_response = api_client.get("/users", params={"_limit": 3})
    users = users_response.json()
    logger.info(f"Получено пользователей: {len(users)}")
    
    for user in users:
        posts_response = api_client.get(f"/posts?userId={user['id']}")
        logger.debug(f"Пользователь {user['id']} имеет {len(posts)} постов")
```

### 4. Компонентные тесты UI

**Файл:** `tests/components/test_components.py`

**Демо-сайт:** https://demo.playwright.dev/todomvc

**Компоненты:**
| Компонент | Тесты |
|-----------|-------|
| **Button** | Существование, кликабельность |
| **Form/Input** | Существование поля, ввод текста, отправка формы |
| **Navigation** | Ссылки фильтров, фильтрация задач |
| **Checkbox** | Переключение состояния |

**Почему компоненты в директории tests/components?**
- **Изоляция:** Тестируются отдельные UI-элементы, не полные сценарии
- **Переиспользование:** Компоненты используются в разных E2E тестах
- **Быстрая обратная связь:** Component tests выполняются быстрее E2E
- **Слои тестирования:**
  - `tests/components/` — изолированные элементы (кнопки, формы)
  - `tests/e2e/` — полные бизнес-сценарии (login → purchase → logout)
  - `tests/integration/` — взаимодействие с API/БД

### 5. Обновление pyproject.toml

**Добавлено:**
```toml
[tool.pytest.ini_options.env]
BASE_URL = "https://demo.playwright.dev/todomvc"
API_BASE_URL = "https://jsonplaceholder.typicode.com"
BROWSER = "chromium"
HEADLESS = "true"
TIMEOUT = "30000"
```

### 6. Обновление .gitignore

**Добавлены исключения:**
```
# Playwright artifacts
playwright-report/
test-results/
blob-report/
```

### 7. Обновление README.md

**Изменения в структуре проекта:**
- Детализирована структура `src/` с описанием поддиректорий
- Добавлена директория `tests/integration/`
- Указаны конкретные файлы тестов
- Обновлена ссылка на CI workflow (`ci.yml` вместо `e2e.yml`)

## Итоговый статус

| Показатель | До | После |
|------------|----|----|
| CI/CD pipeline | ❌ Отсутствует | ✅ GitHub Actions |
| Логирование | ❌ Разрозненное | ✅ Централизованное |
| Интеграционные тесты | ❌ Нет примеров | ✅ 5 тестов с API |
| Компонентные тесты | ❌ Пустая директория | ✅ 8 тестов компонентов |
| Документация структуры | ⚠️ Общая | ✅ Детальная с описаниями |

## Файлы, подвергшиеся изменениям
1. `.github/workflows/ci.yml` (создан) - CI/CD pipeline
2. `src/utils/logger.py` (создан) - Модуль логирования
3. `src/utils/__init__.py` (создан) - Экспорт утилит
4. `tests/integration/test_integration.py` (создан) - Интеграционные тесты
5. `tests/components/test_components.py` (создан) - Компонентные тесты
6. `pyproject.toml` (изменён) - Переменные окружения по умолчанию
7. `.gitignore` (изменён) - Исключения артефактов Playwright
8. `README.md` (изменён) - Обновлена структура проекта

## Рекомендации для будущих сессий

### Почему разделение тестов на 3 типа?

1. **Component Tests (`tests/components/`)**
   - Проверяют изолированные UI-элементы
   - Быстрые (< 1 мин)
   - Запускаются первыми в CI
   - Пример: кнопка существует, форма принимает ввод

2. **E2E Tests (`tests/e2e/`)**
   - Проверяют полные бизнес-сценарии
   - Медленные (5-10 мин)
   - Требуют стабильного окружения
   - Пример: регистрация → добавление товара → оплата

3. **Integration Tests (`tests/integration/`)**
   - Проверяют взаимодействие с внешними системами
   - API, базы данных, очереди сообщений
   - Мокаются или используют тестовые стенды
   - Пример: создание пользователя через API → проверка в БД

### Почему логирование вынесено в utils?

- **Единый стандарт:** Все модули используют одинаковый формат
- **Гибкость:** Легко изменить уровень логирования для всего проекта
- **CI-совместимость:** JSON формат для парсинга в CI/CD
- **Тестируемость:** Можно подменить логгер в тестах

---

- Следить за соответствием структуры проекта документации
- При добавлении новых переменных окружения проверять их наличие в модели Settings
- Перед коммитом запускать ruff check . --fix и ruff format . локально
- Добавить real DB тесты: поднять PostgreSQL в Docker для интеграционных тестов
- Настроить Allure в CI: добавить шаг генерации и деплоя отчётов
- Добавить визуальное регрессионное тестирование: Playwright screenshot comparison
