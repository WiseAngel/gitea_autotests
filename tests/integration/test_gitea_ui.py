"""
Integration tests that combine Gitea API setup with browser verification.
"""

from __future__ import annotations

from typing import Any

import allure
import pytest
from playwright.sync_api import Page, expect
from qase.pytest import qase
from src.api.gitea import (
    build_issue_payload,
    build_repo_payload,
    build_unique_name,
)
from src.config.settings import settings
from tests.support import api_client, delete_repo, require_api_credentials

pytestmark = [
    pytest.mark.integration,
    pytest.mark.ui,
    pytest.mark.regression,
]


def _seed_public_repo_with_issue(resource_seed: str) -> tuple[str, str, str, int]:
    """Create a public repository and one issue for browser verification."""
    require_api_credentials()

    repo_name = build_unique_name("repo", resource_seed)
    issue_title = build_unique_name("issue", resource_seed)

    with api_client() as client:
        repo_response = client.post(
            "/user/repos",
            json=build_repo_payload(
                repo_name,
                private=False,
                auto_init=True,
                description="UI integration repo",
            ),
        )
        repo_response.raise_for_status()
        repo_data: dict[str, Any] = repo_response.json()
        owner = repo_data.get("owner", {}).get("login") or settings.gitea_username

        issue_response = client.post(
            f"/repos/{owner}/{repo_name}/issues",
            json=build_issue_payload(issue_title, body="Seeded for browser verification"),
        )
        issue_response.raise_for_status()
        issue_data: dict[str, Any] = issue_response.json()

        return owner, repo_name, issue_title, int(issue_data["number"])


@qase.id(25)
@allure.title("Repository and issue created via the API are visible in the browser")
def test_seeded_public_repository_is_visible(page: Page, gitea_resource_name: str) -> None:
    """Verify a repo created by the API is visible in the browser."""
    with allure.step("Seed a public repository and issue via the API"):
        owner, repo_name, issue_title, issue_number = _seed_public_repo_with_issue(gitea_resource_name)

    try:
        with allure.step("Open the repository page and verify its name is visible"):
            page.goto(f"{settings.base_url}/{owner}/{repo_name}")
            expect(page.locator("body")).to_contain_text(repo_name)

        with allure.step("Open the issue page and verify its title is visible"):
            page.goto(f"{settings.base_url}/{owner}/{repo_name}/issues/{issue_number}")
            expect(page.locator("body")).to_contain_text(issue_title)
    finally:
        with allure.step("Delete the repository created by the test"), api_client() as client:
            delete_repo(client, owner, repo_name)
