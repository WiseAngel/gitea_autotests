"""
Component-layer tests for Gitea helper functions.

These checks cover lightweight helper logic that previously lived in a separate
unit layer, but now belongs to the component baseline.
"""

from __future__ import annotations

import pytest
from src.api.gitea import (
    build_api_base_url,
    build_auth_headers,
    build_issue_payload,
    build_repo_payload,
    build_repo_web_url,
    build_unique_name,
    normalize_base_url,
    normalize_slug,
)

pytestmark = [
    pytest.mark.component,
    pytest.mark.api,
    pytest.mark.smoke,
]


@pytest.mark.tms_id("TC-COMP-004")
def test_normalize_base_url_trims_trailing_slashes() -> None:
    """Normalize base URLs consistently."""
    assert normalize_base_url("https://gitea.com/") == "https://gitea.com"


@pytest.mark.tms_id("TC-COMP-005")
def test_build_api_base_url_defaults_to_api_v1() -> None:
    """Derive the Gitea API root from the public URL."""
    assert build_api_base_url("https://gitea.com") == "https://gitea.com/api/v1"


@pytest.mark.tms_id("TC-COMP-006")
def test_build_auth_headers_uses_gitea_token_scheme() -> None:
    """Build authorization headers with the Gitea token scheme."""
    headers = build_auth_headers("secret-token")

    assert headers["Authorization"] == "token secret-token"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"


@pytest.mark.tms_id("TC-COMP-007")
def test_normalize_slug_removes_special_characters() -> None:
    """Convert free-form text into a stable slug."""
    assert normalize_slug("Repo Name / 2026!") == "repo-name-2026"


@pytest.mark.tms_id("TC-COMP-008")
def test_build_unique_name_is_deterministic_with_entropy() -> None:
    """Build predictable names when entropy is provided."""
    assert build_unique_name("repo", "Test Name", entropy="abc123") == "repo-test-name-abc123"


@pytest.mark.tms_id("TC-COMP-009")
def test_build_repo_web_url_uses_public_base_url() -> None:
    """Build a public repository URL."""
    assert build_repo_web_url("https://gitea.com/", "alice", "demo") == "https://gitea.com/alice/demo"


@pytest.mark.tms_id("TC-COMP-010")
def test_build_repo_payload_contains_expected_fields() -> None:
    """Build repository creation payloads."""
    payload = build_repo_payload("demo", private=True, description="Demo repo", default_branch="main")

    assert payload["name"] == "demo"
    assert payload["private"] is True
    assert payload["description"] == "Demo repo"
    assert payload["default_branch"] == "main"
    assert payload["auto_init"] is True
    assert payload["readme"] == "Default"


@pytest.mark.tms_id("TC-COMP-011")
def test_build_issue_payload_contains_expected_fields() -> None:
    """Build issue creation payloads."""
    payload = build_issue_payload(
        "Demo issue",
        body="Body",
        labels=[1, 2],
        assignees=["alice"],
        milestone=3,
        ref="main",
        closed=False,
    )

    assert payload["title"] == "Demo issue"
    assert payload["body"] == "Body"
    assert payload["labels"] == [1, 2]
    assert payload["assignees"] == ["alice"]
    assert payload["milestone"] == 3
    assert payload["ref"] == "main"
    assert payload["closed"] is False
