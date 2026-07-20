"""
End-to-end API journeys for Gitea.
"""

from __future__ import annotations

import allure
import pytest
from qase.pytest import qase
from src.api.gitea import build_issue_payload, build_repo_payload
from src.config.settings import settings
from src.testing.factories import GiteaIssueFactory, GiteaRepositoryFactory
from tests.support import api_client, delete_repo, require_api_credentials

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.api,
    pytest.mark.regression,
]


def _run_repo_flow() -> tuple[str, str, int]:
    """Create a repository, seed an issue, and verify API search/list flows."""
    require_api_credentials()

    repo_name = GiteaRepositoryFactory.build()["name"]
    issue_title = GiteaIssueFactory.build()["title"]

    with api_client() as client:
        with allure.step("Create repository via API"):
            repo_response = client.post(
                "/user/repos",
                json=build_repo_payload(
                    repo_name,
                    private=False,
                    auto_init=True,
                    description="End-to-end API repo",
                ),
            )
            repo_response.raise_for_status()
            repo_data = repo_response.json()
            owner = repo_data.get("owner", {}).get("login") or settings.gitea_username

        with allure.step("Verify repository appears in the user's repo list and search results"):
            my_repos_response = client.get("/user/repos")
            my_repos_response.raise_for_status()
            my_repos = my_repos_response.json()
            assert any(repo.get("name") == repo_name for repo in my_repos), (
                "Created repository must be listed under /user/repos"
            )

            search_response = client.get("/repos/search", params={"q": repo_name})
            search_response.raise_for_status()
            search_results = search_response.json()
            assert any(item.get("name") == repo_name for item in search_results.get("data", [])), (
                "Created repository must be discoverable via /repos/search"
            )

        with allure.step("Create an issue in the repository"):
            issue_response = client.post(
                f"/repos/{owner}/{repo_name}/issues",
                json=build_issue_payload(issue_title, body="Seeded by end-to-end API test"),
            )
            issue_response.raise_for_status()
            issue_data = issue_response.json()
            issue_number = int(issue_data["number"])

        with allure.step("Verify repository and issue details round-trip correctly"):
            repo_details_response = client.get(f"/repos/{owner}/{repo_name}")
            repo_details_response.raise_for_status()
            repo_details = repo_details_response.json()
            assert repo_details.get("name") == repo_name, "Repository details lookup must return the created repo"

            issue_lookup_response = client.get(f"/repos/{owner}/{repo_name}/issues/{issue_number}")
            issue_lookup_response.raise_for_status()
            issue_lookup = issue_lookup_response.json()
            assert issue_lookup.get("title") == issue_title, "Issue lookup must return the title used at creation"

        return owner, repo_name, issue_number


@qase.id(20)
@allure.title("Full API-only flow: create repo, seed issue, verify search/list/detail endpoints, then clean up")
def test_repository_issue_search_flow() -> None:
    """Verify a complete API-only repository flow."""
    owner, repo_name, _ = _run_repo_flow()
    with allure.step("Delete the repository created by the test"), api_client() as client:
        delete_repo(client, owner, repo_name)
