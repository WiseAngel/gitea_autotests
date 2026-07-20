"""
Component-layer tests for Gitea helper functions.

These checks cover lightweight helper logic that previously lived in a separate
unit layer, but now belongs to the component baseline.
"""

from __future__ import annotations

import allure
import pytest
from qase.pytest import qase
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


@qase.id(4)
@allure.title("Trailing slashes are trimmed from a base URL")
@allure.severity(allure.severity_level.CRITICAL)
def test_normalize_base_url_trims_trailing_slashes() -> None:
    """Normalize base URLs consistently."""
    assert normalize_base_url("https://gitea.com/") == "https://gitea.com", (
        "Trailing slash must be stripped from the base URL"
    )


@qase.id(5)
@allure.title("API base URL defaults to <base_url>/api/v1 when not overridden")
@allure.severity(allure.severity_level.CRITICAL)
def test_build_api_base_url_defaults_to_api_v1() -> None:
    """Derive the Gitea API root from the public URL."""
    assert build_api_base_url("https://gitea.com") == "https://gitea.com/api/v1", (
        "Default API URL must append /api/v1 to the base URL"
    )


@qase.id(6)
@allure.title("Auth headers use Gitea's 'token' authorization scheme")
@allure.severity(allure.severity_level.CRITICAL)
def test_build_auth_headers_uses_gitea_token_scheme() -> None:
    """Build authorization headers with the Gitea token scheme."""
    headers = build_auth_headers("secret-token")

    assert headers["Authorization"] == "token secret-token", "Authorization header must use the Gitea token scheme"
    assert headers["Content-Type"] == "application/json", "Content-Type header must be application/json"
    assert headers["Accept"] == "application/json", "Accept header must be application/json"


@qase.id(7)
@allure.title("Slugs strip special characters and normalize to lowercase-hyphenated text")
@allure.severity(allure.severity_level.CRITICAL)
def test_normalize_slug_removes_special_characters() -> None:
    """Convert free-form text into a stable slug."""
    assert normalize_slug("Repo Name / 2026!") == "repo-name-2026", (
        "Slug must be lowercased with special characters collapsed to hyphens"
    )


@qase.id(8)
@allure.title("Unique names are deterministic when explicit entropy is supplied")
@allure.severity(allure.severity_level.CRITICAL)
def test_build_unique_name_is_deterministic_with_entropy() -> None:
    """Build predictable names when entropy is provided."""
    assert build_unique_name("repo", "Test Name", entropy="abc123") == "repo-test-name-abc123", (
        "Name must combine prefix, slugified test name, and the supplied entropy"
    )


@qase.id(9)
@allure.title("Repository web URL is built from the public base URL, owner, and repo name")
@allure.severity(allure.severity_level.CRITICAL)
def test_build_repo_web_url_uses_public_base_url() -> None:
    """Build a public repository URL."""
    assert build_repo_web_url("https://gitea.com/", "alice", "demo") == "https://gitea.com/alice/demo", (
        "Repository URL must join the normalized base URL with owner/repo"
    )


@qase.id(10)
@allure.title("Repository creation payload includes all supplied fields")
@allure.severity(allure.severity_level.CRITICAL)
def test_build_repo_payload_contains_expected_fields() -> None:
    """Build repository creation payloads."""
    payload = build_repo_payload("demo", private=True, description="Demo repo", default_branch="main")

    assert payload["name"] == "demo", "Payload must carry the requested repository name"
    assert payload["private"] is True, "Payload must reflect the requested private flag"
    assert payload["description"] == "Demo repo", "Payload must carry the requested description"
    assert payload["default_branch"] == "main", "Payload must carry the requested default branch"
    assert payload["auto_init"] is True, "auto_init must default to True"
    assert payload["readme"] == "Default", "readme must default to 'Default' template"


@qase.id(11)
@allure.title("Issue creation payload includes all supplied fields")
@allure.severity(allure.severity_level.CRITICAL)
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

    assert payload["title"] == "Demo issue", "Payload must carry the requested title"
    assert payload["body"] == "Body", "Payload must carry the requested body"
    assert payload["labels"] == [1, 2], "Payload must carry the requested label ids"
    assert payload["assignees"] == ["alice"], "Payload must carry the requested assignees"
    assert payload["milestone"] == 3, "Payload must carry the requested milestone id"
    assert payload["ref"] == "main", "Payload must carry the requested ref"
    assert payload["closed"] is False, "Payload must carry the requested closed flag"
