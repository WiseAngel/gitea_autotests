# Contributing Guide

Правила и конвенции для разработки автотестов в этом фреймворке. Обязательны для любого PR.

---

## Стек

| Слой | Выбор |
|------|-------|
| Core | Python 3.11+ + pytest + pytest-playwright |
| Config | pydantic-settings + `.env` (строгая валидация) |
| API Client | httpx (async) |
| Database | SQLAlchemy 2.x + asyncpg |
| Test Data | factory_boy + faker |
| Logging | structlog (JSON в CI) |
| Linting | ruff + mypy --strict + pre-commit |
| Reporting | Allure + Playwright Trace Viewer |
| CI/CD | GitHub Actions (matrix sharding) |

---

## Обязательные правила

1. **Типизация** — type hints для всех функций и методов (`mypy --strict`).
2. **Docstrings** — у каждого теста и публичного метода: что проверяется/делает, в свободной форме или Google-style (Args/Returns/Raises для нетривиальных сигнатур).
3. **`expect()` вместо `assert`** — для UI-проверок использовать только `expect()` из Playwright (авто-retry). Там, где `assert` неизбежен (API/данные, unit-тесты) — обязательно с сообщением об ошибке: `assert x == y, "почему это должно быть равно"`.
4. **Без `time.sleep()`** — использовать встроенные авто-ожидания Playwright.
5. **Без `os.getenv()`** — использовать `settings` из `src.config.settings`.
6. **Без глобального состояния** — browser/context/page управляются только через фикстуры.
7. **Компонентный подход** — UI-компоненты наследуются от `BaseComponent`, не Page Object.
8. **Данные через API** — тестовые данные создаются через API/factory_boy, не через UI.
9. **AAA-паттерн** — каждый тест структурирован как Arrange / Act / Assert, без скрытой логики в фикстурах, которая маскирует Act.
10. **Независимость тестов** — тест не должен зависеть от порядка запуска или состояния, оставленного другим тестом.

## Запрещено

- `time.sleep()` — использовать Playwright auto-wait.
- `driver.find_element` — Selenium-антипаттерн, здесь не используется.
- Глобальные переменные — только фикстуры.
- Смешивание API/UI логики внутри одного компонента.
- Хардкод тестовых данных — параметризация или `factory_boy`.
- `assert` без сообщения об ошибке.
- `pytest-xdist` (`-n auto`) в CI — вызывает OOM на бесплатных раннерах, использовать `pytest-split`.

---

## CI/CD правила

- **Matrix sharding**: `pytest-split` (`--splits`/`--group`), не `pytest-xdist`.
- **Fail-fast**: `false` для независимого выполнения шардов.
- **Retry**: `--reruns 2 --reruns-delay 3` для нестабильных тестов.
- **Секреты**: только через GitHub Secrets, никогда в коде.

---

## Маркировка тестов

```python
@pytest.mark.component  # / integration / e2e
@pytest.mark.ui          # / api
@pytest.mark.smoke
def test_something(): ...
```

Один тест — один слой (`component`/`integration`/`e2e`) и один тип (`ui`/`api`).

Тесты, у которых есть соответствующий test case в Qase, дополнительно маркируются `@qase.id(N)` (`from qase.pytest import qase`) — подробности настройки и работы интеграции см. в [README → «Интеграция с Qase»](./README.md#-отчётность).
