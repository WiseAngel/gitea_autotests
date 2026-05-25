"""
Integration tests for Gitea API endpoints.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.api.clients import GiteaClient
from src.config.settings import settings
from src.testing.factories import GiteaIssueFactory, GiteaRepositoryFactory

pytestmark = [pytest.mark.integration, pytest.mark.api]


def _require_api_credentials() -> None:
    """Skip tests when Gitea API credentials are not configured."""
    if not settings.api_token or not settings.gitea_username:
        pytest.skip("Requires Gitea API token and username")


async def _fetch_api_version() -> dict[str, Any]:
    """Fetch the Gitea version payload."""
    async with GiteaClient() as client:
        response = await client.get("/version")
        response.raise_for_status()
        return response.json()


async def _create_repo_and_issue() -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    """Create a public repo and a seed issue for cleanup-friendly tests."""
    _require_api_credentials()

    repo_name = GiteaRepositoryFactory.build()["name"]
    issue_title = GiteaIssueFactory.build()["title"]

    async with GiteaClient() as client:
        repo_response = await client.create_repo(repo_name, private=False, auto_init=True, description="QA test repo")
        repo_response.raise_for_status()
        repo_data = repo_response.json()

        owner = repo_data.get("owner", {}).get("login") or settings.gitea_username
        issue_response = await client.create_issue(owner, repo_name, issue_title, body="Created by automation")
        issue_response.raise_for_status()
        issue_data = issue_response.json()

        return owner, repo_name, repo_data, issue_data


async def _delete_repo(owner: str, repo_name: str) -> None:
    """Delete a repository created during a test."""
    async with GiteaClient() as client:
        response = await client.delete_repo(owner, repo_name)
        response.raise_for_status()


def test_public_version_endpoint_is_available() -> None:
    """Verify the public API version endpoint responds."""
    version_data = asyncio.run(_fetch_api_version())

    assert "version" in version_data
    assert version_data["version"]


def test_authenticated_user_endpoint_returns_profile() -> None:
    """Verify the authenticated user endpoint returns a profile."""
    _require_api_credentials()

    async def _get_user() -> dict[str, Any]:
        async with GiteaClient() as client:
            response = await client.get_authenticated_user()
            response.raise_for_status()
            return response.json()

    user_data = asyncio.run(_get_user())

    assert user_data
    assert user_data.get("login") or user_data.get("username") or user_data.get("email")


def test_authenticated_repo_lifecycle() -> None:
    """Verify repository creation and cleanup through the API."""
    owner, repo_name, repo_data, _ = asyncio.run(_create_repo_and_issue())

    assert repo_data.get("name") == repo_name
    assert repo_data.get("private") is False

    asyncio.run(_delete_repo(owner, repo_name))


def test_authenticated_issue_creation() -> None:
    """Verify issue creation in a seeded repository."""
    owner, repo_name, _, issue_data = asyncio.run(_create_repo_and_issue())

    assert issue_data.get("title")
    assert issue_data.get("number")
    assert issue_data.get("repository_url") or issue_data.get("url")

    asyncio.run(_delete_repo(owner, repo_name))
