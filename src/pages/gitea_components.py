"""
Reusable UI components for Gitea pages.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from src.pages.base_component import BaseComponent


class GiteaNavbarComponent(BaseComponent):
    """Top navigation component for the public Gitea layout."""

    def __init__(self, page: Page) -> None:
        """Initialize the navbar component.

        Args:
            page: Playwright page instance.
        """
        super().__init__(page, "body")

    @property
    def sign_in_link(self) -> Locator:
        """Get the sign-in link."""
        return self.page.locator('a[href$="/user/login"]')

    @property
    def sign_out_link(self) -> Locator:
        """Get the sign-out link."""
        return self.page.locator('a[href$="/user/logout"]')

    def expect_sign_in_visible(self) -> None:
        """Assert that the sign-in link is visible."""
        expect(self.sign_in_link).to_be_visible()

    def click_sign_in(self) -> None:
        """Open the login page from the navbar."""
        self.sign_in_link.click()


class GiteaLoginFormComponent(BaseComponent):
    """Login form component on the Gitea authentication page."""

    def __init__(self, page: Page) -> None:
        """Initialize the login form component.

        Args:
            page: Playwright page instance.
        """
        super().__init__(page, "form.ui.form")

    @property
    def username_input(self) -> Locator:
        """Get the username input."""
        return self._child('input[name="user_name"]')

    @property
    def password_input(self) -> Locator:
        """Get the password input."""
        return self._child('input[name="password"]')

    @property
    def submit_button(self) -> Locator:
        """Get the submit button."""
        return self._child("button.ui.primary.button")

    def expect_fields_visible(self) -> None:
        """Assert that the login fields are visible."""
        expect(self.username_input).to_be_visible()
        expect(self.password_input).to_be_visible()
        expect(self.submit_button).to_be_visible()

    def fill_credentials(self, username: str, password: str) -> None:
        """Fill login form fields.

        Args:
            username: Gitea username.
            password: Gitea password.
        """
        self.username_input.fill(username)
        self.password_input.fill(password)

    def submit(self) -> None:
        """Submit the login form."""
        self.submit_button.click()
