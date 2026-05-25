"""
End-to-end API journeys for Gitea.
"""

from __future__ import annotations

import asyncio

import pytest

from src.api.clients import GiteaClient
from src.config.settings import settings
from src.testing.factories import GiteaIssueFactory, GiteaRepositoryFactory

pytestmark = [pytest.mark.e2e, pytest.mark.api]


def _require_api_credentials() -> None:
    """Skip tests when Gitea API credentials are not configured."""
    if not settings.api_token or not settings.gitea_username:
        pytest.skip("Requires Gitea API token and username")


async def _run_repo_flow() -> tuple[str, str, int]:
    """Create a repository, seed an issue, and verify API search/list flows."""
    _require_api_credentials()

    repo_name = GiteaRepositoryFactory.build()["name"]
    issue_title = GiteaIssueFactory.build()["title"]

    async with GiteaClient() as client:
        repo_response = await client.create_repo(repo_name, private=False, auto_init=True, description="End-to-end API repo")
        repo_response.raise_for_status()
        repo_data = repo_response.json()
        owner = repo_data.get("owner", {}).get("login") or settings.gitea_username

        my_repos_response = await client.list_my_repos()
        my_repos_response.raise_for_status()
        my_repos = my_repos_response.json()
        assert any(repo.get("name") == repo_name for repo in my_repos)

        search_response = await client.search_repos(repo_name)
        search_response.raise_for_status()
        search_results = search_response.json()
        assert any(item.get("name") == repo_name for item in search_results.get("data", []))

        issue_response = await client.create_issue(owner, repo_name, issue_title, body="Seeded by end-to-end API test")
        issue_response.raise_for_status()
        issue_data = issue_response.json()
        issue_number = int(issue_data["number"])

        repo_details_response = await client.get_repo(owner, repo_name)
        repo_details_response.raise_for_status()
        repo_details = repo_details_response.json()
        assert repo_details.get("name") == repo_name

        issue_lookup_response = await client.get(f"/repos/{owner}/{repo_name}/issues/{issue_number}")
        issue_lookup_response.raise_for_status()
        issue_lookup = issue_lookup_response.json()
        assert issue_lookup.get("title") == issue_title

        return owner, repo_name, issue_number


async def _delete_repo(owner: str, repo_name: str) -> None:
    """Delete a repository created during a test."""
    async with GiteaClient() as client:
        response = await client.delete_repo(owner, repo_name)
        response.raise_for_status()


def test_repository_issue_search_flow() -> None:
    """Verify a complete API-only repository flow."""
    owner, repo_name, _ = asyncio.run(_run_repo_flow())
    asyncio.run(_delete_repo(owner, repo_name))
