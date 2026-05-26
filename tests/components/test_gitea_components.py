"""
Component-level UI checks for Gitea pages.
"""

from __future__ import annotations

import re

import pytest
from qase.pytest import qase
from playwright.sync_api import Page, expect
from src.config.settings import settings
from src.pages.gitea_components import GiteaLoginFormComponent

pytestmark = [
    pytest.mark.component,
    pytest.mark.ui,
    pytest.mark.smoke,
]


_SEED_OWNER = settings.gitea_username or "testadmin"
_SEED_REPO = "go-sdk"


@qase.id(1)
def test_public_homepage_exposes_sign_in_link(page: Page) -> None:
    """Verify the Gitea instance home page exposes a sign-in path."""
    page.goto(settings.base_url)
    expect(page).to_have_url(re.compile(rf"{re.escape(settings.base_url)}/?.*"))
    expect(page.get_by_role("link", name=re.compile(r"Sign (in|up)", re.I))).to_be_visible()


@qase.id(2)
def test_login_form_fields_are_visible(page: Page) -> None:
    """Verify the login form exposes the expected fields."""
    page.goto(f"{settings.base_url}/user/login")

    login_form = GiteaLoginFormComponent(page)
    login_form.expect_visible()
    login_form.expect_fields_visible()


@qase.id(3)
def test_login_form_accepts_credentials_input(page: Page) -> None:
    """Verify the login form accepts user input."""
    page.goto(f"{settings.base_url}/user/login")

    login_form = GiteaLoginFormComponent(page)
    login_form.fill_credentials("qa-user", "qa-password")

    expect(login_form.username_input).to_have_value("qa-user")
    expect(login_form.password_input).to_have_value("qa-password")
