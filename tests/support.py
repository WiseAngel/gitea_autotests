"""Shared helpers for Gitea API-backed tests.

Consolidates the credential-check / HTTP-client / repo lifecycle helpers
that used to be copy-pasted across the e2e and integration test modules.
"""

from __future__ import annotations

import httpx
import pytest
from src.api.gitea import build_auth_headers, build_repo_payload
from src.config.settings import settings
from src.testing.factories import GiteaRepositoryFactory


def require_api_credentials() -> None:
    """Skip the current test when Gitea API credentials are not configured."""
    if not settings.api_token or not settings.gitea_username:
        pytest.skip("Requires Gitea API token and username")


def api_client() -> httpx.Client:
    """Create a sync HTTP client configured for authenticated Gitea API calls."""
    return httpx.Client(
        base_url=settings.effective_api_url,
        headers=build_auth_headers(settings.api_token),
        timeout=settings.timeout / 1000,
    )


def create_repo(client: httpx.Client, *, description: str | None = None) -> tuple[str, str]:
    """Create a throw-away public repository via the API.

    Args:
        client: Authenticated httpx client.
        description: Optional repository description.

    Returns:
        Tuple of (owner, repo_name) for the created repository.
    """
    repo_name: str = GiteaRepositoryFactory.build()["name"]
    resp = client.post(
        "/user/repos",
        json=build_repo_payload(repo_name, private=False, auto_init=True, description=description),
    )
    resp.raise_for_status()
    owner: str = resp.json().get("owner", {}).get("login") or settings.gitea_username
    return owner, repo_name


def delete_repo(client: httpx.Client, owner: str, repo_name: str) -> None:
    """Delete a repository created during a test, ignoring 404 responses.

    Args:
        client: Authenticated httpx client.
        owner: Repository owner login.
        repo_name: Repository name.
    """
    resp = client.delete(f"/repos/{owner}/{repo_name}")
    if resp.status_code not in (204, 404):
        resp.raise_for_status()
