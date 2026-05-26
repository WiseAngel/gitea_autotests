"""
End-to-end UI journeys for Gitea.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect
from qase.pytest import qase
from src.config.settings import settings
from src.pages.gitea_components import GiteaLoginFormComponent

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.ui,
    pytest.mark.regression,
]


def _require_ui_credentials() -> None:
    """Skip tests when Gitea UI credentials are not configured."""
    if not settings.gitea_username or not settings.gitea_password:
        pytest.skip("Requires Gitea UI username and password")


@qase.id(18)
def test_public_homepage_links_to_login(page: Page) -> None:
    """Verify the public homepage exposes a sign-in link."""
    page.goto(settings.base_url)

    # On self-hosted Gitea the root page is the explore/dashboard page,
    # not the about.gitea.com marketing site.
    expect(page).to_have_url(re.compile(rf"{re.escape(settings.base_url)}/?.*"))
    expect(page.get_by_role("link", name=re.compile(r"Sign (in|up)", re.I))).to_be_visible()


@qase.id(19)
def test_authenticated_user_can_sign_in(page: Page) -> None:
    """Verify an authenticated user can sign in and reach the dashboard."""
    _require_ui_credentials()

    page.goto(f"{settings.base_url}/user/login")

    login_form = GiteaLoginFormComponent(page)
    login_form.fill_credentials(settings.gitea_username, settings.gitea_password)
    login_form.submit()

    # After successful login Gitea redirects to the user dashboard.
    expect(page).to_have_url(re.compile(rf"{re.escape(settings.base_url)}(/|/issues|/dashboard)?$"))
    expect(page.locator("body")).not_to_be_empty()
