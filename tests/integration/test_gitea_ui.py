"""
Integration tests that combine Gitea API setup with browser verification.
"""

from __future__ import annotations

from typing import Any

import httpx

import pytest
from playwright.sync_api import Page, expect
from src.api.gitea import (
    build_auth_headers,
    build_issue_payload,
    build_repo_payload,
    build_unique_name,
)
from src.config.settings import settings

pytestmark = [pytest.mark.integration, pytest.mark.ui, pytest.mark.regression]


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


def _seed_public_repo_with_issue(resource_seed: str) -> tuple[str, str, str, int]:
    """Create a public repository and one issue for browser verification."""
    _require_api_credentials()

    repo_name = build_unique_name("repo", resource_seed)
    issue_title = build_unique_name("issue", resource_seed)

    with _api_client() as client:
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


def _delete_repo(owner: str, repo_name: str) -> None:
    """Delete a repository created for an integration test."""
    with _api_client() as client:
        response = client.delete(f"/repos/{owner}/{repo_name}")
        response.raise_for_status()


def test_seeded_public_repository_is_visible(page: Page, gitea_resource_name: str) -> None:
    """Verify a repo created by the API is visible in the browser."""
    owner, repo_name, issue_title, issue_number = _seed_public_repo_with_issue(gitea_resource_name)

    try:
        page.goto(f"{settings.base_url}/{owner}/{repo_name}")
        expect(page.locator("body")).to_contain_text(repo_name)

        page.goto(f"{settings.base_url}/{owner}/{repo_name}/issues/{issue_number}")
        expect(page.locator("body")).to_contain_text(issue_title)
    finally:
        _delete_repo(owner, repo_name)
