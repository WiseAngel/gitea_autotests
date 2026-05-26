"""
Authenticated smoke suite for nuage_autotest account on gitea.com.

These tests verify that the full authenticated user flow works end-to-end:
sign-in, settings page access, repository dashboard visibility, and
basic profile rendering.

All tests skip gracefully when GITEA_USERNAME / GITEA_PASSWORD / API_TOKEN
are not configured.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect
from src.config.settings import settings

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.ui,
    pytest.mark.smoke,
]


@pytest.mark.tms_id("TC-E2E-004")
def test_authenticated_user_reaches_dashboard(authenticated_page: Page) -> None:
    """Verify a logged-in user can reach their personal dashboard."""
    authenticated_page.goto(settings.base_url)

    # Authenticated home redirects to /user/dashboard or the feed root.
    expect(authenticated_page).to_have_url(re.compile(rf"{re.escape(settings.base_url)}(/|/user/dashboard|\?.*)?$"))
    expect(authenticated_page.locator("body")).not_to_be_empty()


@pytest.mark.tms_id("TC-E2E-005")
def test_authenticated_user_settings_page_accessible(authenticated_page: Page) -> None:
    """Verify the settings page is accessible for an authenticated user."""
    authenticated_page.goto(f"{settings.base_url}/user/settings")

    expect(authenticated_page).to_have_url(re.compile(r".*/user/settings"))
    expect(authenticated_page.locator("body")).to_contain_text("Settings")


@pytest.mark.tms_id("TC-E2E-006")
def test_authenticated_user_repos_list_accessible(authenticated_page: Page) -> None:
    """Verify the authenticated user can see their repository list."""
    authenticated_page.goto(f"{settings.base_url}/user/settings/repos")

    expect(authenticated_page).to_have_url(re.compile(r".*/user/settings/repos"))
    expect(authenticated_page.locator("body")).not_to_be_empty()


@pytest.mark.tms_id("TC-E2E-007")
def test_authenticated_public_profile_visible(authenticated_page: Page) -> None:
    """Verify the user's public profile page is rendered correctly."""
    username = settings.gitea_username
    authenticated_page.goto(f"{settings.base_url}/{username}")

    expect(authenticated_page).to_have_url(re.compile(rf".*/{re.escape(username)}"))
    # Profile page should contain the username somewhere visible.
    expect(authenticated_page.locator("body")).to_contain_text(username)
