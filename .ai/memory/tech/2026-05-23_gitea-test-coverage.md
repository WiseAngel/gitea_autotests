# Решение: Gitea test coverage baseline

**Дата**: 2026-05-23
**Категория**: tech
**Статус**: Принято

## Контекст
Фреймворк раньше был завязан на TodoMVC и JSONPlaceholder demo-тесты. Требовалось перевести покрытие на `gitea.com` и разделить его на `component`, `integration`, `e2e` с UI/API-ветками.

## Решение
1. `BASE_URL` по умолчанию указывает на `https://gitea.com`.
2. `api_base_url` для Gitea строится как `/api/v1`.
3. Авторизация API использует заголовок `Authorization: token <token>`.
4. UI-фикстуры не получают API token в headers, чтобы не смешивать browser-auth и API-auth.
5. Demo-тесты из `tests/components/test_components.py`, `tests/e2e/test_smoke.py` и `tests/integration/test_integration.py` заменены Gitea-ориентированным покрытием.
6. Таксономия слоёв зафиксирована как `component`, `integration`, `e2e`; отдельный `unit` слой не выделяется, его покрытие входит в `component` как быстрые локальные проверки.
7. Во всех прикладных слоях (`component`, `integration`, `e2e`) должны существовать оба типа тестов: UI и API, где это применимо к сценарию.
8. Браузерная матрица для локального и CI-запуска должна включать `chromium` и `firefox`.
9. Для бесплатной TMS-first интеграции рекомендуется `Qase` для portfolio-демо и `Kiwi TCMS` для self-hosted пути.

## Альтернативы
- Bearer auth для API: отклонено, потому что Gitea PAT ожидает `token` scheme.
- Оставить demo-тесты и добавить Gitea рядом: отклонено, потому что задача требовала замены покрытия.

## Последствия
- ✅ Плюсы: единый таргет для Gitea, реальные API/UI сценарии, разделение по слоям.
- ⚠️ Минусы: authenticated тесты требуют настроенных `GITEA_USERNAME`, `GITEA_PASSWORD` и `API_TOKEN`.
- 🔧 Технический долг: при необходимости можно вынести Gitea helper-клиент в отдельный production module.

## Связанные файлы
- `src/config/settings.py`
- `src/api/clients.py`
- `src/api/gitea.py`
- `tests/conftest.py`
- `src/testing/pytest_support.py`
- `src/testing/factories.py`
- `tests/components/test_gitea_components.py`
- `tests/integration/test_gitea_api.py`
- `tests/integration/test_gitea_ui.py`
- `tests/e2e/test_gitea_ui.py`
- `tests/e2e/test_gitea_api.py`
- `tests/components/test_gitea_helpers.py`

## История изменений
- 2026-05-23: создано
