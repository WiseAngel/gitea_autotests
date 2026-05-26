"""
Reusable UI components for Gitea pages.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from src.pages.base_component import BaseComponent


class GiteaSearchComponent(BaseComponent):
    """Search bar component present on most Gitea authenticated pages."""

    def __init__(self, page: Page) -> None:
        """Initialize search component.

        Args:
            page: Playwright page instance.
        """
        super().__init__(page, 'form[action="/explore/repos"]')

    @property
    def input(self) -> Locator:
        """Get the search input field."""
        return self._child('input[name="q"]')

    @property
    def submit_button(self) -> Locator:
        """Get the search submit button."""
        return self._child('button[type="submit"]')

    def search(self, query: str) -> None:
        """Fill the search input and submit.

        Args:
            query: Search query string.
        """
        self.input.fill(query)
        self.submit_button.click()

    def expect_input_visible(self) -> None:
        """Assert the search input is visible."""
        expect(self.input).to_be_visible()


class GiteaRepoCardComponent(BaseComponent):
    """Single repository card in the explore/repos listing."""

    def __init__(self, page: Page, repo_full_name: str) -> None:
        """Initialize a repo card anchored to a specific repository.

        Args:
            page: Playwright page instance.
            repo_full_name: ``owner/repo`` string used to locate the card link.
        """
        super().__init__(page, f'a[href="/{repo_full_name}"]')
        self._repo_full_name = repo_full_name

    def expect_visible(self, timeout: float | None = None) -> None:
        """Assert the repository card link is visible.

        Args:
            timeout: Optional timeout override in milliseconds.
        """
        expect(self.root_locator.first).to_be_visible(timeout=timeout)

    def click(self) -> None:
        """Navigate to the repository page."""
        self.root_locator.first.click()


class GiteaUserProfileComponent(BaseComponent):
    """User profile header shown on ``/{username}`` pages."""

    def __init__(self, page: Page) -> None:
        """Initialize user profile component.

        Args:
            page: Playwright page instance.
        """
        super().__init__(page, ".user.profile")

    @property
    def avatar(self) -> Locator:
        """Get the avatar image."""
        return self._child("img.ui.avatar")

    @property
    def username_heading(self) -> Locator:
        """Get the username heading element."""
        return self._child(".username")

    def expect_avatar_visible(self) -> None:
        """Assert the profile avatar is rendered."""
        expect(self.avatar).to_be_visible()

    def expect_username_visible(self) -> None:
        """Assert the username heading is rendered."""
        expect(self.username_heading).to_be_visible()


class GiteaIssueListComponent(BaseComponent):
    """Issue list table on ``/{owner}/{repo}/issues`` pages."""

    def __init__(self, page: Page) -> None:
        """Initialize the issue list component.

        Args:
            page: Playwright page instance.
        """
        super().__init__(page, "#issue-list")

    def issue_link(self, title: str) -> Locator:
        """Locate a specific issue by its title text.

        Args:
            title: Exact issue title string.

        Returns:
            Locator for the matching issue title link.
        """
        return self._child(f'a.title:text-is("{title}")')

    def expect_issue_visible(self, title: str) -> None:
        """Assert that an issue with the given title appears in the list.

        Args:
            title: Issue title to look for.
        """
        expect(self.issue_link(title)).to_be_visible()


class GiteaIssueFormComponent(BaseComponent):
    """New-issue form on ``/{owner}/{repo}/issues/new``."""

    def __init__(self, page: Page) -> None:
        """Initialize the issue creation form component.

        Args:
            page: Playwright page instance.
        """
        super().__init__(page, "form#new-issue")

    @property
    def title_input(self) -> Locator:
        """Get the issue title input."""
        return self._child('input[name="title"]')

    @property
    def body_editor(self) -> Locator:
        """Get the issue body textarea."""
        return self._child("textarea.edit_area")

    @property
    def submit_button(self) -> Locator:
        """Get the submit button."""
        return self._child('button:has-text("Create Issue")')

    def fill_title(self, title: str) -> None:
        """Fill the issue title field.

        Args:
            title: Issue title text.
        """
        self.title_input.fill(title)

    def fill_body(self, body: str) -> None:
        """Fill the issue body editor.

        Args:
            body: Issue body markdown text.
        """
        self.body_editor.fill(body)

    def submit(self) -> None:
        """Submit the new issue form."""
        self.submit_button.click()

    def expect_form_visible(self) -> None:
        """Assert the issue form is rendered."""
        expect(self.title_input).to_be_visible()
        expect(self.submit_button).to_be_visible()


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
