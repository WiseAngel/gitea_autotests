"""
Integration tests for Gitea API endpoints.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from qase.pytest import qase
from src.api.gitea import build_auth_headers, build_issue_payload, build_repo_payload
from src.config.settings import settings
from src.testing.factories import GiteaIssueFactory, GiteaRepositoryFactory

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
    pytest.mark.regression,
]


def _require_api_credentials() -> None:
    """Skip tests when Gitea API credentials are not configured."""
    if not settings.api_token or not settings.gitea_username:
        pytest.skip("Requires Gitea API token and username")


def _api_client() -> httpx.Client:
    """Create a sync HTTP client for Gitea API calls."""
    return httpx.Client(
        base_url=settings.effective_api_url,
        headers=build_auth_headers(settings.api_token),
        timeout=settings.timeout / 1000,
    )


def _fetch_api_version() -> dict[str, Any]:
    """Fetch the Gitea version payload."""
    response = httpx.get(f"{settings.effective_api_url}/version", timeout=settings.timeout / 1000)
    response.raise_for_status()
    return response.json()


def _create_repo_and_issue() -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    """Create a public repo and a seed issue for cleanup-friendly tests."""
    _require_api_credentials()

    repo_name = GiteaRepositoryFactory.build()["name"]
    issue_title = GiteaIssueFactory.build()["title"]

    with _api_client() as client:
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


def _delete_repo(owner: str, repo_name: str) -> None:
    """Delete a repository created during a test."""
    with _api_client() as client:
        response = client.delete(f"/repos/{owner}/{repo_name}")
        response.raise_for_status()


@qase.id(26)
def test_public_version_endpoint_is_available() -> None:
    """Verify the public API version endpoint responds."""
    version_data = _fetch_api_version()

    assert "version" in version_data
    assert version_data["version"]


@qase.id(27)
def test_authenticated_user_endpoint_returns_profile() -> None:
    """Verify the authenticated user endpoint returns a profile."""
    _require_api_credentials()

    with _api_client() as client:
        response = client.get("/user")
        response.raise_for_status()
        user_data = response.json()

    assert user_data
    assert user_data.get("login") or user_data.get("username") or user_data.get("email")


@qase.id(28)
def test_authenticated_repo_lifecycle() -> None:
    """Verify repository creation and cleanup through the API."""
    owner, repo_name, repo_data, _ = _create_repo_and_issue()

    assert repo_data.get("name") == repo_name
    assert repo_data.get("private") is False

    _delete_repo(owner, repo_name)


@qase.id(29)
def test_authenticated_issue_creation() -> None:
    """Verify issue creation in a seeded repository."""
    owner, repo_name, _, issue_data = _create_repo_and_issue()

    assert issue_data.get("title")
    assert issue_data.get("number")
    assert issue_data.get("repository_url") or issue_data.get("url")

    _delete_repo(owner, repo_name)
