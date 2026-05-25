"""
End-to-end UI journeys for Gitea.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect
from src.config.settings import settings
from src.pages.gitea_components import GiteaLoginFormComponent

pytestmark = [pytest.mark.e2e, pytest.mark.ui, pytest.mark.regression]


def _require_ui_credentials() -> None:
    """Skip tests when Gitea UI credentials are not configured."""
    if not settings.gitea_username or not settings.gitea_password:
        pytest.skip("Requires Gitea UI username and password")


def test_public_homepage_links_to_login(page: Page) -> None:
    """Verify the public homepage exposes a sign-in path."""
    page.goto(settings.base_url)

    expect(page).to_have_url(re.compile(r"https://about\.gitea\.com/"))
    expect(page.get_by_role("link", name=re.compile(r"Sign in", re.I))).to_be_visible()


def test_authenticated_user_can_sign_in(page: Page) -> None:
    """Verify an authenticated user can sign in and open a private area."""
    _require_ui_credentials()

    page.goto(f"{settings.base_url}/user/login?redirect_to=%2Fuser%2Fsettings")

    login_form = GiteaLoginFormComponent(page)
    login_form.fill_credentials(settings.gitea_username, settings.gitea_password)
    login_form.submit()

    expect(page).to_have_url(re.compile(r".*/user/settings"))
    expect(page.locator("body")).to_contain_text("Settings")
