# Промпт для следующей сессии: верификация CI + интеграция с ботом

> Используй этот файл как стартовый контекст. Прочитай его полностью перед началом работы.

---

## Контекст проекта

Два репозитория:
- `d:\dev\playwright_autotests` — Playwright pytest фреймворк (тесты Gitea)
- `d:\dev\sdet-orchestrator` — Telegram-бот для запуска тестов

GitHub репозиторий тестов: `https://github.com/WiseAngel/gitea_autotests`
GitHub Pages (Allure): `https://wiseangel.github.io/gitea_autotests/allure/`
Gitea аккаунт для тестов: `nuage_autotest` на `gitea.com`

---

## Что уже сделано (предыдущая сессия 2026-05-25)

### playwright_autotests
- ✅ 32 теста: component (21 smoke) + integration (11 regression) + e2e (7)
- ✅ Маркеры: `smoke` / `regression` / `e2e` совпадают с суитами бота
- ✅ `pytest-json-report` установлен, `--json-report` во всех CI jobs
- ✅ `pytest-split` для sharding (`--splits=2 --group=N`)
- ✅ CI: lint + api-tests + ui-tests (chromium/firefox × 2 groups) + publish-allure
- ✅ GitHub Secrets: `GITEA_API_TOKEN`, `GITEA_USERNAME`, `GITEA_PASSWORD`
- ✅ GitHub Pages настроены на `gh-pages` ветку
- ✅ `authenticated_page` fixture (form-based login, auto-skip без credentials)
- ✅ Новые компоненты: Search, RepoCard, UserProfile, IssueList, IssueForm
- ✅ Integration тесты: labels lifecycle, milestones lifecycle, comments lifecycle
- ✅ Репо `nuage_autotest-qa-demo` создано на gitea.com (нужно для IssueForm теста)
- ✅ `[build-system]` добавлен в `pyproject.toml`

### Последний коммит
```
7fedcf4 fix: replace pytest-shard (broken) with pytest-split, add build-system to pyproject
```

---

## Задачи на эту сессию (по приоритету)

### Задача 1 — Проверить статус CI [ОБЯЗАТЕЛЬНО ПЕРВЫМ]

Открой GitHub Actions: `https://github.com/WiseAngel/gitea_autotests/actions`

Ожидаемые статусы после коммита `7fedcf4`:
- `lint` → должен быть зелёным
- `api-tests (group 1)` и `api-tests (group 2)` → зелёные или SKIP (если нет credentials)
- `ui-tests (chromium/firefox × group 1/2)` → зелёные или часть SKIP
- `publish-allure` → зелёный, Allure отчёт с реальными тестами

Если что-то красное — покажи лог ошибки, исправляй по месту.

---

### Задача 2 — Верификация UI-селекторов [ЕСЛИ CI ЗЕЛЁНЫЙ]

Три компонента нужно проверить на живом gitea.com через DevTools (F12 → Inspect):

| Компонент | URL для проверки | Текущий селектор | Возможная проблема |
|---|---|---|---|
| `GiteaUserProfileComponent` | `gitea.com/gitea` | `.user.profile` | Класс может отличаться |
| `GiteaIssueListComponent` | `gitea.com/gitea/go-sdk/issues` | `#issue-list` | ID может отличаться |
| `GiteaIssueFormComponent` | `gitea.com/nuage_autotest/nuage_autotest-qa-demo/issues/new` | `form#new-issue` | Нужна аутентификация |

Если селекторы неверные — исправить в `src/pages/gitea_components.py`.

---

### Задача 3 — Первый запуск тестов через бота [ОСНОВНАЯ ЦЕЛЬ]

#### 3.1 Настроить sdet-orchestrator

В `d:\dev\sdet-orchestrator\.env` добавить/проверить:
```env
PLAYWRIGHT_REPO_URL=https://github.com/WiseAngel/gitea_autotests.git
GITHUB_TOKEN=<GitHub PAT с scopes: repo + workflow>
```

Как получить GitHub PAT:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Scopes: `repo` (full) + `workflow`
3. Скопировать в `.env`

#### 3.2 Проверить что бот запущен

```bash
# Из d:\dev\sdet-orchestrator
curl http://localhost:8080/health
# → {"status": "ok"}

curl http://localhost:8080/readyz
# → {"status": "ready"}
```

#### 3.3 Запустить первый /run

В Telegram боту:
```
/run
→ [🎭 Playwright]
→ [🚀 ci_trigger]      # или subprocess — зависит от режима
→ [main]
→ [🧪 staging]
→ [💨 smoke]
→ [✅ Запустить]
```

Ожидаемый результат:
```
✅ Тесты завершены
Passed: ~13  (часть скипнется без browser)
Failed: 0
Skipped: ~8  (authenticated тесты без password)
```

#### 3.4 Проверить режим subprocess (если ci_trigger не работает)

```
/run → Playwright → subprocess → main → staging → smoke
```

При режиме `subprocess` бот клонирует репозиторий и запускает pytest локально в Docker-контейнере воркера.

---

### Задача 4 — TMS интеграция [ОПЦИОНАЛЬНО]

Рекомендованный сервис: **Qase** (бесплатный план, REST API, хороший UI)

Шаги:
1. Зарегистрироваться на `qase.io`, создать проект `GITEA`
2. Получить API key в Settings → API tokens
3. В `playwright_autotests/.env`:
   ```env
   TMS_API_URL=https://api.qase.io/v1
   TMS_TOKEN=<qase-api-key>
   ```
4. Поддерживать `@pytest.mark.tms_id("TC-...")` на уровне отдельных тестов
5. Доработать `scripts/tms_reporter.py` под Qase API (endpoint: `POST /result/{code}/{id}/bulk`)

---

## Файлы для быстрого старта

Перед работой прочитай:
```
d:\dev\playwright_autotests\.ai\memory\iterations\2026-05-25_21-51_ci-fixes-bot-integration-phases-A-D.md
d:\dev\playwright_autotests\.ai\memory\tech\2026-05-25_ci-and-bot-integration.md
d:\dev\playwright_autotests\pyproject.toml
d:\dev\playwright_autotests\.github\workflows\ci.yml
d:\dev\sdet-orchestrator\docs\DOCUMENTATION.md  (раздел 5.1 и 5.3)
```

---

## Критичные детали которые нельзя забыть

1. **pytest-shard сломан** — используем только `pytest-split` (`--splits=2 --group=N`)
2. **uv pip install** — обязательно с флагом `-e`: `uv pip install --system -e ".[dev]"`
3. **Allure merge** — искать папки `allure-results/`, не все `.json` файлы
4. **factory-boy mypy** — подавляется через `[[tool.mypy.overrides]]` в `pyproject.toml`, не `# type: ignore`
5. **authenticated_page** — требует `GITEA_PASSWORD`, не только `API_TOKEN`
6. **nuage_autotest-qa-demo** — репо создано на gitea.com, тест `test_new_issue_form_is_visible_after_login` должен пройти

---

## Маппинг маркеров (для бота)

```
/run → smoke      = pytest -m smoke      (21 тест, component слой)
/run → regression = pytest -m regression (11 тестов, integration + e2e)
/run → e2e        = pytest -m e2e        (7 тестов, e2e слой)
```

---

## Ожидаемое состояние после этой сессии

- [ ] CI полностью зелёный (все jobs)
- [ ] Allure отчёт показывает реальные тесты на GitHub Pages
- [ ] Первый `/run smoke` через бота завершился успешно
- [ ] Селекторы новых компонентов проверены/исправлены
- [ ] TMS маркеры добавлены/поддерживаются на уровне отдельных тестов
