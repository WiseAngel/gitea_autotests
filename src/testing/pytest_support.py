"""
Pytest configuration and fixtures for Playwright tests.

Provides browser context isolation, DB transaction rollback, logging setup,
and reusable UI expectation helpers.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest
import structlog
from playwright.sync_api import BrowserContext, Page, expect

from src.api.gitea import build_auth_headers, build_unique_name
from src.config.settings import settings
from src.db.engine import DatabaseEngine


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command-line options.

    Args:
        parser: Pytest option parser.
    """
    parser.addoption(
        "--headless",
        action="store_true",
        default=None,
        help="Run browsers in headless mode",
    )


@pytest.fixture(scope="session")
def browser_type_launch_args(request: pytest.FixtureRequest) -> dict[str, bool]:
    """Override browser launch args to support ``--headless``.

    Args:
        request: Pytest fixture request.

    Returns:
        Browser launch arguments.
    """
    headless = request.config.getoption("--headless")
    if headless is not None:
        return {"headless": headless}
    return {"headless": settings.headless}


structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def _skip_if_local_base_url_unavailable() -> None:
    """Skip UI tests when a local base URL is not running.

    The default `BASE_URL` in local development is sometimes pointed at a
    local Gitea instance. When that server is not available, Playwright would
    otherwise fail with a connection error before the test body can run.
    """
    parsed = urlparse(settings.base_url)
    is_localhost = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not is_localhost:
        return

    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(settings.base_url)
            if response.status_code < 500:
                return
    except httpx.HTTPError:
        pytest.skip(f"Local base URL is unavailable: {settings.base_url}")


def _is_local_base_url() -> bool:
    """Return whether the configured base URL points to localhost."""
    parsed = urlparse(settings.base_url)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a session-scoped event loop for async fixtures.

    Returns:
        Session event loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine() -> AsyncGenerator[DatabaseEngine, None]:
    """Create a connected database engine for the test session.

    Yields:
        Connected database engine.
    """
    db = DatabaseEngine()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def db_session(db_engine: DatabaseEngine) -> AsyncGenerator[Any, None]:
    """Create a transaction-scoped DB session with auto-rollback.

    Args:
        db_engine: Shared database engine fixture.

    Yields:
        Database session managed in a rollback-only transaction.
    """
    # db_engine.session() returns an async context manager, not an AsyncGenerator.
    # We manage entry/exit explicitly to satisfy mypy.
    session = await db_engine.session().__aenter__()  # type: ignore[attr-defined]
    try:
        yield session
        await session.rollback()
    except Exception:
        await session.rollback()
        raise
    finally:
        await db_engine.session().__aexit__(None, None, None)  # type: ignore[attr-defined]


@pytest.fixture
def context(context: BrowserContext) -> BrowserContext:
    """Customize the browser context for test runs.

    Args:
        context: Playwright browser context.

    Returns:
        Configured browser context.
    """
    context.set_default_timeout(settings.timeout)
    return context


@pytest.fixture
def page(page: Page, request: pytest.FixtureRequest) -> Generator[Page, None, None]:
    """Enhance the Playwright page with failure diagnostics.

    Args:
        page: Playwright page instance.
        request: Pytest request object.

    Yields:
        Page instance.
    """
    yield page

    node: Any = request.node
    if hasattr(node, "rep_call") and node.rep_call.failed:
        screenshot_name = f"screenshots/{request.node.name}.png"
        page.screenshot(path=screenshot_name)
        logger.error("Test failed", screenshot=screenshot_name)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]) -> Any:
    """Capture test outcome for use in fixtures.

    Args:
        item: Test item.
        call: Call information.

    Returns:
        Pytest hook result.
    """
    outcome = yield
    report = outcome.get_result()

    node: Any = item
    if report.when == "call":
        node.rep_call = report
    elif report.when == "setup":
        node.rep_setup = report
    elif report.when == "teardown":
        node.rep_teardown = report


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip UI tests early when a local base URL is unavailable.

    Args:
        config: Pytest configuration object.
        items: Collected test items.
    """
    del config

    if not _is_local_base_url():
        return

    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(settings.base_url)
            if response.status_code < 500:
                return
    except httpx.HTTPError:
        skip_marker = pytest.mark.skip(reason=f"Local base URL is unavailable: {settings.base_url}")
        for item in items:
            if "ui" in item.keywords:
                item.add_marker(skip_marker)


class ComponentExpectations:
    """Reusable ``expect()`` wrappers for UI components."""

    @staticmethod
    def element_visible(page: Page, selector: str, timeout: float | None = None) -> None:
        """Assert that an element is visible."""
        expect(page.locator(selector)).to_be_visible(timeout=timeout)

    @staticmethod
    def element_hidden(page: Page, selector: str, timeout: float | None = None) -> None:
        """Assert that an element is hidden."""
        expect(page.locator(selector)).to_be_hidden(timeout=timeout)

    @staticmethod
    def has_text(page: Page, selector: str, text: str, timeout: float | None = None) -> None:
        """Assert that an element has exact text."""
        expect(page.locator(selector)).to_have_text(text, timeout=timeout)

    @staticmethod
    def contains_text(page: Page, selector: str, text: str, timeout: float | None = None) -> None:
        """Assert that an element contains text."""
        expect(page.locator(selector)).to_contain_text(text, timeout=timeout)

    @staticmethod
    def enabled(page: Page, selector: str, timeout: float | None = None) -> None:
        """Assert that an element is enabled."""
        expect(page.locator(selector)).to_be_enabled(timeout=timeout)

    @staticmethod
    def disabled(page: Page, selector: str, timeout: float | None = None) -> None:
        """Assert that an element is disabled."""
        expect(page.locator(selector)).to_be_disabled(timeout=timeout)


@pytest.fixture
def ui() -> type[ComponentExpectations]:
    """Provide reusable UI expectation helpers.

    Returns:
        UI expectation helper class.
    """
    return ComponentExpectations


@pytest.fixture
def authenticated_page(context: BrowserContext) -> Page:
    """Provide a Page already authenticated via Gitea API token injection.

    Skips automatically when credentials are not configured.
    Uses form-based login so that the test body receives a browser page
    that is already signed in.

    Args:
        context: Playwright browser context fixture.

    Returns:
        Authenticated Playwright page.

    Raises:
        pytest.skip.Exception: When API token or username are not set.
    """
    if not settings.api_token or not settings.gitea_username:
        pytest.skip("Requires GITEA_USERNAME and API_TOKEN")

    _skip_if_local_base_url_unavailable()

    login_url = f"{settings.base_url}/user/login"
    api_url = settings.effective_api_url

    with httpx.Client(
        base_url=api_url,
        headers=build_auth_headers(settings.api_token),
        timeout=settings.timeout / 1000,
        follow_redirects=True,
    ) as api:
        resp = api.get("/user")
        if resp.status_code != 200:
            pytest.skip(f"API token rejected: {resp.status_code}")

    page = context.new_page()
    page.goto(login_url)
    page.locator('input[name="user_name"]').fill(settings.gitea_username)
    page.locator('input[name="password"]').fill(settings.gitea_password or settings.api_token)
    page.locator("button.ui.primary.button").click()
    page.wait_for_url(f"{settings.base_url}/**", timeout=settings.timeout)

    return page


@pytest.fixture(scope="session")
def test_run_started_at() -> str:
    """Return a stable run identifier for generated test data."""
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")


@pytest.fixture
def gitea_resource_name(request: pytest.FixtureRequest) -> str:
    """Build a unique Gitea resource name for the current test.

    Args:
        request: Pytest request object.

    Returns:
        Unique resource name.
    """
    return build_unique_name("qa", request.node.name)
