"""
Integration tests for Gitea API endpoints.
"""

from __future__ import annotations

from typing import Any

import allure
import httpx
import pytest
from qase.pytest import qase
from src.api.gitea import build_issue_payload, build_repo_payload
from src.config.settings import settings
from src.testing.factories import GiteaIssueFactory, GiteaRepositoryFactory
from tests.support import api_client, delete_repo, require_api_credentials

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
    pytest.mark.regression,
]


def _fetch_api_version() -> dict[str, Any]:
    """Fetch the Gitea version payload."""
    response = httpx.get(f"{settings.effective_api_url}/version", timeout=settings.timeout / 1000)
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    return data


def _create_repo_and_issue() -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    """Create a public repo and a seed issue for cleanup-friendly tests."""
    require_api_credentials()

    repo_name = GiteaRepositoryFactory.build()["name"]
    issue_title = GiteaIssueFactory.build()["title"]

    with api_client() as client:
        repo_response = client.post(
            "/user/repos",
            json=build_repo_payload(
                repo_name,
                private=False,
                auto_init=True,
                description="QA test repo",
            ),
        )
        repo_response.raise_for_status()
        repo_data = repo_response.json()

        owner = repo_data.get("owner", {}).get("login") or settings.gitea_username
        issue_response = client.post(
            f"/repos/{owner}/{repo_name}/issues",
            json=build_issue_payload(issue_title, body="Created by automation"),
        )
        issue_response.raise_for_status()
        issue_data = issue_response.json()

        return owner, repo_name, repo_data, issue_data


@qase.id(26)
@allure.title("Public /version endpoint responds without authentication")
def test_public_version_endpoint_is_available() -> None:
    """Verify the public API version endpoint responds."""
    version_data = _fetch_api_version()

    assert "version" in version_data, "Version payload must contain a 'version' key"
    assert version_data["version"], "Version value must not be empty"


@qase.id(27)
@allure.title("Authenticated /user endpoint returns the current user's profile")
def test_authenticated_user_endpoint_returns_profile() -> None:
    """Verify the authenticated user endpoint returns a profile."""
    require_api_credentials()

    with allure.step("Fetch the authenticated user profile"), api_client() as client:
        response = client.get("/user")
        response.raise_for_status()
        user_data = response.json()

    with allure.step("Verify the profile payload identifies the user"):
        assert user_data, "User payload must not be empty"
        assert user_data.get("login") or user_data.get("username") or user_data.get("email"), (
            "User payload must include a login, username, or email"
        )


@qase.id(28)
@allure.title("Repository can be created and then deleted through the API")
def test_authenticated_repo_lifecycle() -> None:
    """Verify repository creation and cleanup through the API."""
    owner, repo_name, repo_data, _ = _create_repo_and_issue()

    with allure.step("Verify repository was created as requested"):
        assert repo_data.get("name") == repo_name, "Created repository name must match the requested name"
        assert repo_data.get("private") is False, "Repository must be created as public"

    with allure.step("Delete the repository"), api_client() as client:
        delete_repo(client, owner, repo_name)


@qase.id(29)
@allure.title("Issue can be created in a freshly seeded repository")
def test_authenticated_issue_creation() -> None:
    """Verify issue creation in a seeded repository."""
    owner, repo_name, _, issue_data = _create_repo_and_issue()

    with allure.step("Verify the issue payload is well-formed"):
        assert issue_data.get("title"), "Created issue must have a title"
        assert issue_data.get("number"), "Created issue must have a number"
        assert issue_data.get("repository_url") or issue_data.get("url"), (
            "Created issue must reference its repository or self url"
        )

    with allure.step("Delete the repository"), api_client() as client:
        delete_repo(client, owner, repo_name)
