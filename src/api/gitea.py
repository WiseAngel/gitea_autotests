"""
Gitea-specific API helpers.

Provides pure utility helpers for URL normalization, payload construction,
and deterministic resource-name generation used by tests and API clients.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4


def normalize_base_url(url: str) -> str:
    """Normalize a base URL by trimming trailing slashes.

    Args:
        url: Raw URL value.

    Returns:
        Normalized URL without a trailing slash.
    """
    return url.rstrip("/")


def build_api_base_url(base_url: str, api_base_url: str | None = None) -> str:
    """Build the effective Gitea API base URL.

    Args:
        base_url: Public Gitea URL.
        api_base_url: Optional explicit API URL.

    Returns:
        Normalized API URL.
    """
    if api_base_url:
        return normalize_base_url(api_base_url)
    return f"{normalize_base_url(base_url)}/api/v1"


def build_auth_headers(token: str, token_type: str = "token") -> dict[str, str]:
    """Build Gitea authorization headers.

    Args:
        token: Personal access token value.
        token_type: Authorization scheme used by Gitea.

    Returns:
        Headers suitable for Gitea API requests.
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"{token_type} {token}"
    return headers


def normalize_slug(value: str) -> str:
    """Convert arbitrary text to a stable slug.

    Args:
        value: Input value.

    Returns:
        Slugified string using lowercase ASCII characters.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return slug.strip("-")


def build_unique_name(prefix: str, test_name: str, entropy: str | None = None) -> str:
    """Build a unique resource name for test data.

    Args:
        prefix: Name prefix such as ``repo`` or ``issue``.
        test_name: Logical test name used for readability.
        entropy: Optional deterministic suffix for tests.

    Returns:
        Unique name safe to use as a Gitea repository or issue identifier.
    """
    suffix = entropy or uuid4().hex[:8]
    slug = normalize_slug(test_name)
    return f"{prefix}-{slug}-{suffix}"


def build_repo_web_url(base_url: str, owner: str, repo: str) -> str:
    """Build a public repository URL.

    Args:
        base_url: Public Gitea URL.
        owner: Repository owner.
        repo: Repository name.

    Returns:
        Canonical repository URL.
    """
    return f"{normalize_base_url(base_url)}/{owner}/{repo}"


def build_repo_payload(
    name: str,
    *,
    private: bool = False,
    auto_init: bool = True,
    description: str | None = None,
    readme: str | bool | None = "Default",
    default_branch: str | None = None,
) -> dict[str, Any]:
    """Build payload for repository creation.

    Args:
        name: Repository name.
        private: Whether the repository should be private.
        auto_init: Whether to initialize the repository with a README.
        description: Optional repository description.
        readme: README template name or flag used by the Gitea API.
        default_branch: Optional default branch name.

    Returns:
        JSON-serializable payload for ``POST /api/v1/user/repos``.
    """
    payload: dict[str, Any] = {
        "name": name,
        "private": private,
        "auto_init": auto_init,
    }
    if readme is not None:
        payload["readme"] = "Default" if readme is True else readme
    if description is not None:
        payload["description"] = description
    if default_branch is not None:
        payload["default_branch"] = default_branch
    return payload


def build_issue_payload(
    title: str,
    *,
    body: str | None = None,
    labels: list[int] | None = None,
    assignees: list[str] | None = None,
    milestone: int | None = None,
    ref: str | None = None,
    closed: bool | None = None,
) -> dict[str, Any]:
    """Build payload for issue creation.

    Args:
        title: Issue title.
        body: Optional issue body.
        labels: Optional label IDs.
        assignees: Optional assignee usernames.
        milestone: Optional milestone ID.
        ref: Optional branch or commit reference.
        closed: Optional initial closed state.

    Returns:
        JSON-serializable payload for ``POST /api/v1/repos/{owner}/{repo}/issues``.
    """
    payload: dict[str, Any] = {"title": title}
    if body is not None:
        payload["body"] = body
    if labels is not None:
        payload["labels"] = labels
    if assignees is not None:
        payload["assignees"] = assignees
    if milestone is not None:
        payload["milestone"] = milestone
    if ref is not None:
        payload["ref"] = ref
    if closed is not None:
        payload["closed"] = closed
    return payload
