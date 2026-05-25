# [ПАМЯТЬ] Сессия: CI self-hosted Gitea — полный цикл отладки

## Дата сессии
2026-05-25 22:00–23:10 (UTC+3)
Сессия по отладке CI пайплайнов и переводу тестов с gitea.com на self-hosted Gitea в Docker.

---

## Цель сессии
1. Проверить и исправить изменения в `pytest_support.py` и `conftest.py`
2. Перевести все тесты на self-hosted Gitea (убрать зависимость от gitea.com и Anubis)
3. Добиться зелёного CI без skip-ов

---

## Выполненные действия

### 1. Исправление conftest.py — дублирование хука
- **Проблема**: `pytest_collection_modifyitems` была определена и в `conftest.py`, и в `pytest_support.py` (импортируется через `import *`). Локальное объявление перекрывало импортированное и содержало более примитивную логику.
- **Решение**: `conftest.py` сведён к одной строке `from src.testing.pytest_support import *`.

### 2. Перевод на self-hosted Gitea — Anubis блокировка
- **Проблема**: `gitea.com` защищён Anubis (anti-bot proof-of-work) — блокирует headless-браузеры на `/explore/repos`, `/gitea`, `/gitea/go-sdk/issues`.
- **Решение**: Добавлен Gitea Docker service в GitHub Actions (`services: gitea: image: gitea/gitea:latest`) с health-check на `/api/healthz`.
- `tests/components/test_gitea_new_components.py` — убраны `@skip_on_gitea_com` маркеры, URL адаптированы под `testadmin/go-sdk`.
- Написан `scripts/seed_gitea.py` — создаёт репозиторий и issue перед тестами.

### 3. Обновление всех трёх workflow
- `ci.yml` — основной (push/PR): lint → api-tests (2 шарда) → ui-tests (2 браузера × 2 шарда) → Allure на GitHub Pages
- `e2e.yml` — ночная E2E регрессия (02:00 UTC): component-tests + e2e-ui с Docker Gitea
- `e2e-tests.yml` — ночная API регрессия (04:00 UTC)
- Везде: `--splits/--group` вместо несуществующего `--shard=K/N`
- Везде: Gitea Docker service без несуществующих `GITEA_ADMIN_*` env vars

### 4. Исправление тестов под self-hosted стенд
- `test_gitea_components.py`: убран хардкод `about.gitea.com`, адаптированы URL
- `test_gitea_ui.py` (`test_public_homepage_links_to_login`): убран редирект на `about.gitea.com`
- `test_gitea_ui.py` (`test_authenticated_user_can_sign_in`): self-hosted после логина идёт на dashboard, не на `/user/settings`
- `test_gitea_authenticated_smoke.py`: убран хардкод `https://gitea\.com/` в URL паттерне
- `integration/test_gitea_ui.py`: заменён `asyncio.run()` на `async def` + `await` (нельзя вызывать из running event loop)

### 5. Создание admin и токена через Gitea CLI
- **Проблема 1**: `GITEA_ADMIN_USER/PASSWORD` env vars не существуют в образе `gitea/gitea` — admin не создавался автоматически.
- **Проблема 2**: После `gitea admin user create` Basic Auth возвращал 401 — Gitea не принимает пароль немедленно.
- **Решение**: В каждом job добавлен шаг `Create Gitea admin user and generate token` (id: seed):
  ```bash
  GITEA_CTR=$(docker ps -q --filter ancestor=gitea/gitea:latest)
  docker exec $GITEA_CTR gitea admin user create --username testadmin ...
  TOKEN=$(docker exec $GITEA_CTR gitea admin user generate-access-token \
    --username testadmin --token-name ci-token --raw)
  echo "api_token=$TOKEN" >> $GITHUB_OUTPUT
  ```
- Токен передаётся через `${{ steps.seed.outputs.api_token }}` во все последующие steps.
- `seed_gitea.py` переработан: читает `API_TOKEN` из env, предпочитает token auth над Basic Auth.

### 6. Исправление ruff I001
- `pytest_support.py`: `from typing import Any` перемещён перед `from urllib.parse import urlparse`
- `test_gitea_new_components.py`: форматирование блока импортов

---

## Итоговый статус
- ✅ `ruff check` и `ruff format --check` проходят чисто
- ✅ Все тесты собираются без ошибок (`--collect-only`)
- ✅ Все workflow используют self-hosted Gitea без зависимости от gitea.com
- ✅ `API_TOKEN` генерируется через CLI и доходит до тестов
- ⏳ CI не прогонялся после последнего коммита — нужна проверка следующего запуска

## Файлы, подвергшиеся изменениям
1. `tests/conftest.py` (изменён) — сведён к одному `import *`
2. `src/testing/pytest_support.py` (изменён) — фикс порядка импортов (ruff I001)
3. `tests/components/test_gitea_new_components.py` (изменён) — убраны skip-маркеры, URL под self-hosted
4. `tests/components/test_gitea_components.py` (изменён) — убран хардкод gitea.com URL
5. `tests/e2e/test_gitea_ui.py` (изменён) — адаптация под self-hosted dashboard redirect
6. `tests/e2e/test_gitea_authenticated_smoke.py` (изменён) — убран хардкод `gitea\.com` в URL паттерне
7. `tests/integration/test_gitea_ui.py` (изменён) — `asyncio.run()` → `async def` + `await`
8. `scripts/seed_gitea.py` (создан) — seed-скрипт: ждёт Gitea, создаёт repo + issue, использует API_TOKEN
9. `.github/workflows/ci.yml` (изменён) — Gitea service + CLI admin creation + token generation
10. `.github/workflows/e2e.yml` (изменён) — аналогично, component-tests + e2e-ui jobs
11. `.github/workflows/e2e-tests.yml` (изменён) — аналогично, API regression job

---

## Ключевые технические выводы

### Gitea Docker image — что работает, что нет
- ❌ `GITEA_ADMIN_USER` / `GITEA_ADMIN_PASSWORD` env vars — **не существуют** в официальном образе
- ❌ Basic Auth сразу после `gitea admin user create` — возвращает 401
- ✅ `gitea admin user generate-access-token --raw` — выдаёт токен без HTTP round-trip
- ✅ `GITEA__security__INSTALL_LOCK: "true"` — пропускает веб-установщик

### pytest-split vs pytest-shard
- В проекте установлен `pytest-split` (синтаксис: `--splits=2 --group=1`)
- `pytest-shard` использует другой синтаксис `--shard-id=0 --num-shards=2` (индекс с 0)
- Не путать — оба установлены, но в workflow должен быть один стиль

---

## Рекомендации для будущих сессий
- Запустить CI вручную через `workflow_dispatch` после следующего push и проверить все jobs
- Если `generate-access-token` не работает в новой версии Gitea — альтернатива: использовать `/api/v1/users/{username}/tokens` с Basic Auth после небольшой задержки (`time.sleep(2)`)
- Рассмотреть добавление `pytest.mark.asyncio` для async тестов если появятся ошибки с event loop
- Проверить что `pages-build-deployment` отрабатывает после `publish-allure` job
