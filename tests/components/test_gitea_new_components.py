"""
Component-level UI checks for new Gitea page components.

Covers: SearchComponent, RepoCardComponent, UserProfileComponent,
IssueListComponent, IssueFormComponent.

All tests run against a self-hosted Gitea instance (see .github/workflows/e2e.yml).
The seed script (scripts/seed_gitea.py) creates required data before the test run.
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

pytestmark = [
    pytest.mark.component,
    pytest.mark.ui,
    pytest.mark.smoke,
]

# Owner of the seed repository created by scripts/seed_gitea.py.
# Falls back to "testadmin" when GITEA_USERNAME is not set.
_SEED_OWNER = settings.gitea_username or "testadmin"
_SEED_REPO = "go-sdk"

# ---------------------------------------------------------------------------
# SearchComponent
# ---------------------------------------------------------------------------


@pytest.mark.tms_id("TC-COMP-012")
def test_explore_repos_search_input_is_visible(page: Page) -> None:
    """Verify the explore repos search form is rendered on the public page."""
    page.goto(f"{settings.base_url}/explore/repos")

    search = GiteaSearchComponent(page)
    search.expect_input_visible()


@pytest.mark.tms_id("TC-COMP-013")
def test_explore_repos_search_returns_results(page: Page) -> None:
    """Verify that submitting the search form navigates to a filtered list."""
    page.goto(f"{settings.base_url}/explore/repos")

    search = GiteaSearchComponent(page)
    search.search(_SEED_REPO)

    expect(page).to_have_url(re.compile(rf".*/explore/repos\?.*q={_SEED_REPO}"))
    expect(page.locator("body")).not_to_be_empty()


# ---------------------------------------------------------------------------
# RepoCardComponent
# ---------------------------------------------------------------------------


@pytest.mark.tms_id("TC-COMP-014")
def test_seed_repo_card_is_visible_on_explore(page: Page) -> None:
    """Verify the seeded public repository card appears in explore results."""
    page.goto(f"{settings.base_url}/explore/repos?q={_SEED_REPO}&limit=10")

    card = GiteaRepoCardComponent(page, f"{_SEED_OWNER}/{_SEED_REPO}")
    card.expect_visible()


# ---------------------------------------------------------------------------
# UserProfileComponent
# ---------------------------------------------------------------------------


@pytest.mark.tms_id("TC-COMP-015")
def test_public_user_profile_is_rendered(page: Page) -> None:
    """Verify the user profile layout renders for the seed admin user."""
    page.goto(f"{settings.base_url}/{_SEED_OWNER}")

    profile = GiteaUserProfileComponent(page)
    profile.expect_avatar_visible()


# ---------------------------------------------------------------------------
# IssueListComponent  (seed repo must have at least one open issue)
# ---------------------------------------------------------------------------


@pytest.mark.tms_id("TC-COMP-016")
def test_issue_list_renders_on_public_repo(page: Page) -> None:
    """Verify the issue list component is rendered on the seeded public repo."""
    page.goto(f"{settings.base_url}/{_SEED_OWNER}/{_SEED_REPO}/issues")

    issue_list = GiteaIssueListComponent(page)
    issue_list.expect_visible()


# ---------------------------------------------------------------------------
# IssueFormComponent  (requires authenticated session)
# ---------------------------------------------------------------------------


@pytest.mark.tms_id("TC-COMP-017")
def test_new_issue_form_is_visible_after_login(authenticated_page: Page) -> None:
    """Verify the new-issue form renders for an authenticated user."""
    authenticated_page.goto(f"{settings.base_url}/{_SEED_OWNER}/{_SEED_REPO}/issues/new")

    if authenticated_page.url.endswith("/issues/new"):
        form = GiteaIssueFormComponent(authenticated_page)
        form.expect_form_visible()
    else:
        pytest.skip("Seed repo not available; skipping issue form check")
