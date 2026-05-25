"""
Integration tests for Gitea labels, milestones, and issue comments.

Each test creates its own resources via the API, asserts the expected
state, then cleans up unconditionally in a finally block.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from src.api.gitea import build_auth_headers, build_repo_payload
from src.config.settings import settings
from src.testing.factories import (
    GiteaIssueFactory,
    GiteaLabelFactory,
    GiteaMilestoneFactory,
    GiteaRepositoryFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.api, pytest.mark.regression]


def _require_credentials() -> None:
    """Skip when API token or username are absent."""
    if not settings.api_token or not settings.gitea_username:
        pytest.skip("Requires GITEA_USERNAME and API_TOKEN")


def _client() -> httpx.Client:
    """Return a configured sync httpx client."""
    return httpx.Client(
        base_url=settings.effective_api_url,
        headers=build_auth_headers(settings.api_token),
        timeout=settings.timeout / 1000,
    )


def _create_repo(client: httpx.Client) -> tuple[str, str]:
    """Create a throw-away public repository.

    Args:
        client: Authenticated httpx client.

    Returns:
        Tuple of (owner, repo_name).
    """
    repo_name: str = GiteaRepositoryFactory.build()["name"]
    resp = client.post(
        "/user/repos",
        json=build_repo_payload(repo_name, private=False, auto_init=True),
    )
    resp.raise_for_status()
    owner: str = resp.json().get("owner", {}).get("login") or settings.gitea_username
    return owner, repo_name


def _delete_repo(client: httpx.Client, owner: str, repo: str) -> None:
    """Delete a repository, ignoring 404 responses.

    Args:
        client: Authenticated httpx client.
        owner: Repository owner login.
        repo: Repository name.
    """
    resp = client.delete(f"/repos/{owner}/{repo}")
    if resp.status_code not in (204, 404):
        resp.raise_for_status()


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def test_label_lifecycle() -> None:
    """Verify label creation, retrieval, and deletion on a repository."""
    _require_credentials()

    with _client() as client:
        owner, repo = _create_repo(client)
        try:
            label_payload: dict[str, Any] = GiteaLabelFactory.build()
            label_payload["color"] = f"#{label_payload['color'][:6]}"

            create_resp = client.post(
                f"/repos/{owner}/{repo}/labels",
                json={"name": label_payload["name"], "color": label_payload["color"]},
            )
            create_resp.raise_for_status()
            label_data = create_resp.json()
            label_id: int = int(label_data["id"])

            assert label_data["name"] == label_payload["name"]
            assert label_data["color"].lower() == label_payload["color"].lower()

            list_resp = client.get(f"/repos/{owner}/{repo}/labels")
            list_resp.raise_for_status()
            labels = list_resp.json()
            assert any(lbl["id"] == label_id for lbl in labels)

            del_resp = client.delete(f"/repos/{owner}/{repo}/labels/{label_id}")
            assert del_resp.status_code == 204

            after_resp = client.get(f"/repos/{owner}/{repo}/labels")
            after_resp.raise_for_status()
            assert not any(lbl["id"] == label_id for lbl in after_resp.json())
        finally:
            _delete_repo(client, owner, repo)


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------


def test_milestone_lifecycle() -> None:
    """Verify milestone creation, retrieval, and deletion on a repository."""
    _require_credentials()

    with _client() as client:
        owner, repo = _create_repo(client)
        try:
            ms_build: dict[str, Any] = GiteaMilestoneFactory.build()
            deadline_str: str = ms_build["deadline"].strftime("%Y-%m-%dT%H:%M:%SZ")

            create_resp = client.post(
                f"/repos/{owner}/{repo}/milestones",
                json={"title": ms_build["title"], "description": ms_build["description"], "due_on": deadline_str},
            )
            create_resp.raise_for_status()
            ms_data = create_resp.json()
            ms_id: int = int(ms_data["id"])

            assert ms_data["title"] == ms_build["title"]

            get_resp = client.get(f"/repos/{owner}/{repo}/milestones/{ms_id}")
            get_resp.raise_for_status()
            assert get_resp.json()["id"] == ms_id

            del_resp = client.delete(f"/repos/{owner}/{repo}/milestones/{ms_id}")
            assert del_resp.status_code == 204
        finally:
            _delete_repo(client, owner, repo)


# ---------------------------------------------------------------------------
# Issue comments
# ---------------------------------------------------------------------------


def test_issue_comment_lifecycle() -> None:
    """Verify comment creation, listing, editing, and deletion on an issue."""
    _require_credentials()

    with _client() as client:
        owner, repo = _create_repo(client)
        try:
            issue_payload: dict[str, Any] = GiteaIssueFactory.build()
            issue_resp = client.post(
                f"/repos/{owner}/{repo}/issues",
                json={"title": issue_payload["title"], "body": issue_payload["body"]},
            )
            issue_resp.raise_for_status()
            issue_number: int = int(issue_resp.json()["number"])

            comment_body = "Automated integration comment"
            comment_resp = client.post(
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                json={"body": comment_body},
            )
            comment_resp.raise_for_status()
            comment_data = comment_resp.json()
            comment_id: int = int(comment_data["id"])

            assert comment_data["body"] == comment_body

            list_resp = client.get(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")
            list_resp.raise_for_status()
            assert any(c["id"] == comment_id for c in list_resp.json())

            updated_body = "Updated integration comment"
            edit_resp = client.patch(
                f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
                json={"body": updated_body},
            )
            edit_resp.raise_for_status()
            assert edit_resp.json()["body"] == updated_body

            del_resp = client.delete(f"/repos/{owner}/{repo}/issues/comments/{comment_id}")
            assert del_resp.status_code == 204
        finally:
            _delete_repo(client, owner, repo)
