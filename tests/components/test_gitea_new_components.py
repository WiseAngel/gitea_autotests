"""
Component-level UI checks for new Gitea page components.

Covers: SearchComponent, RepoCardComponent, UserProfileComponent,
IssueListComponent, IssueFormComponent.

Public-facing assertions run without credentials.
Authenticated assertions use the ``authenticated_page`` fixture and
skip automatically when credentials are absent.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect
from src.config.settings import settings
from src.pages.gitea_components import (
    GiteaIssueFormComponent,
    GiteaIssueListComponent,
    GiteaRepoCardComponent,
    GiteaSearchComponent,
    GiteaUserProfileComponent,
)

pytestmark = [pytest.mark.component, pytest.mark.ui, pytest.mark.smoke]

# ---------------------------------------------------------------------------
# SearchComponent
# ---------------------------------------------------------------------------


def test_explore_repos_search_input_is_visible(page: Page) -> None:
    """Verify the explore repos search form is rendered on the public page."""
    page.goto(f"{settings.base_url}/explore/repos")

    search = GiteaSearchComponent(page)
    search.expect_input_visible()


def test_explore_repos_search_returns_results(page: Page) -> None:
    """Verify that submitting the search form navigates to a filtered list."""
    page.goto(f"{settings.base_url}/explore/repos")

    search = GiteaSearchComponent(page)
    search.search("gitea")

    expect(page).to_have_url(re.compile(r".*/explore/repos\?.*q=gitea"))
    expect(page.locator("body")).not_to_be_empty()


# ---------------------------------------------------------------------------
# RepoCardComponent
# ---------------------------------------------------------------------------


def test_gitea_go_sdk_card_is_visible_on_explore(page: Page) -> None:
    """Verify a known public repository card appears in explore results."""
    page.goto(f"{settings.base_url}/explore/repos?q=go-sdk&limit=10")

    card = GiteaRepoCardComponent(page, "gitea/go-sdk")
    card.expect_visible()


# ---------------------------------------------------------------------------
# UserProfileComponent
# ---------------------------------------------------------------------------


def test_public_user_profile_is_rendered(page: Page) -> None:
    """Verify the user profile layout renders for a known public Gitea user."""
    page.goto(f"{settings.base_url}/gitea")

    profile = GiteaUserProfileComponent(page)
    profile.expect_avatar_visible()


# ---------------------------------------------------------------------------
# IssueListComponent  (requires public repo with open issues)
# ---------------------------------------------------------------------------


def test_issue_list_renders_on_public_repo(page: Page) -> None:
    """Verify the issue list component is rendered on a public repository."""
    page.goto(f"{settings.base_url}/gitea/go-sdk/issues")

    issue_list = GiteaIssueListComponent(page)
    issue_list.expect_visible()


# ---------------------------------------------------------------------------
# IssueFormComponent  (requires authenticated session)
# ---------------------------------------------------------------------------


def test_new_issue_form_is_visible_after_login(authenticated_page: Page) -> None:
    """Verify the new-issue form renders for an authenticated user."""
    authenticated_page.goto(
        f"{settings.base_url}/{settings.gitea_username}/{settings.gitea_username}-qa-demo/issues/new"
    )

    # If the test repo doesn't exist the page will redirect to login or 404.
    # We only assert the form component structure when we land on the right page.
    if authenticated_page.url.endswith("/issues/new"):
        form = GiteaIssueFormComponent(authenticated_page)
        form.expect_form_visible()
    else:
        pytest.skip("Demo repo not available; skipping issue form check")
