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
async def db_session(db_engine: DatabaseEngine) -> AsyncGenerator:
    """Create a transaction-scoped DB session with auto-rollback.

    Args:
        db_engine: Shared database engine fixture.

    Yields:
        Database session managed in a rollback-only transaction.
    """
    async with db_engine.session() as session:
        try:
            yield session
            await session.rollback()
        except Exception:
            await session.rollback()
            raise


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
def page(page: Page, request: pytest.FixtureRequest) -> Page:
    """Enhance the Playwright page with failure diagnostics.

    Args:
        page: Playwright page instance.
        request: Pytest request object.

    Returns:
        Page instance yielded to the test.
    """
    yield page

    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        screenshot_name = f"screenshots/{request.node.name}.png"
        page.screenshot(path=screenshot_name)
        logger.error("Test failed", screenshot=screenshot_name)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> Any:
    """Capture test outcome for use in fixtures.

    Args:
        item: Test item.
        call: Call information.

    Returns:
        Pytest hook result.
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        item.rep_call = report
    elif report.when == "setup":
        item.rep_setup = report
    elif report.when == "teardown":
        item.rep_teardown = report


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
    Injects a session cookie obtained from ``/user/settings`` flow so that
    the test body receives a browser page that is already signed in.

    Args:
        context: Playwright browser context fixture.

    Returns:
        Authenticated Playwright page.

    Raises:
        pytest.skip.Exception: When API token or username are not set.
    """
    if not settings.api_token or not settings.gitea_username:
        pytest.skip("Requires GITEA_USERNAME and API_TOKEN")

    # Obtain a Gitea web session by hitting the token-authenticated API and
    # injecting a ``_csrf``-less session cookie via the browser storage state.
    # Gitea supports HTTP Basic auth with a token as the password, which lets
    # us retrieve the user page and capture the necessary cookies via a
    # headless HTTP call, then replay them into the Playwright context.
    login_url = f"{settings.base_url}/user/login"
    api_url = settings.effective_api_url

    # Verify the token is valid before attempting UI injection.
    with httpx.Client(
        base_url=api_url,
        headers=build_auth_headers(settings.api_token),
        timeout=settings.timeout / 1000,
        follow_redirects=True,
    ) as api:
        resp = api.get("/user")
        if resp.status_code != 200:
            pytest.skip(f"API token rejected: {resp.status_code}")

    # Use Playwright form-based login so we get a full session cookie set.
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

