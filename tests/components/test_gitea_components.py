"""
Component-level UI checks for Gitea pages.
"""

from __future__ import annotations

import re

import allure
import pytest
from playwright.sync_api import Page, expect
from qase.pytest import qase
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
@allure.title("Public homepage exposes a sign-in link")
@allure.severity(allure.severity_level.CRITICAL)
def test_public_homepage_exposes_sign_in_link(page: Page) -> None:
    """Verify the Gitea instance home page exposes a sign-in path."""
    with allure.step("Open the public homepage"):
        page.goto(settings.base_url)
    with allure.step("Verify sign-in link is visible"):
        expect(page).to_have_url(re.compile(rf"{re.escape(settings.base_url)}/?.*"))
        expect(page.get_by_role("link", name=re.compile(r"Sign (in|up)", re.I))).to_be_visible()


@qase.id(2)
@allure.title("Login form renders username, password, and submit fields")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_form_fields_are_visible(page: Page) -> None:
    """Verify the login form exposes the expected fields."""
    with allure.step("Open the login page"):
        page.goto(f"{settings.base_url}/user/login")

    with allure.step("Verify the login form and its fields are visible"):
        login_form = GiteaLoginFormComponent(page)
        login_form.expect_visible()
        login_form.expect_fields_visible()


@qase.id(3)
@allure.title("Login form accepts typed username and password input")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_form_accepts_credentials_input(page: Page) -> None:
    """Verify the login form accepts user input."""
    with allure.step("Open the login page"):
        page.goto(f"{settings.base_url}/user/login")

    with allure.step("Fill in credentials"):
        login_form = GiteaLoginFormComponent(page)
        login_form.fill_credentials("qa-user", "qa-password")

    with allure.step("Verify the fields retain the typed values"):
        expect(login_form.username_input).to_have_value("qa-user")
        expect(login_form.password_input).to_have_value("qa-password")
