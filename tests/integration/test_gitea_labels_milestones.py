"""
Integration tests for Gitea labels, milestones, and issue comments.

Each test creates its own resources via the API, asserts the expected
state, then cleans up unconditionally in a finally block.
"""

from __future__ import annotations

from typing import Any

import allure
import pytest
from qase.pytest import qase
from src.testing.factories import (
    GiteaIssueFactory,
    GiteaLabelFactory,
    GiteaMilestoneFactory,
)
from tests.support import api_client, create_repo, delete_repo, require_api_credentials

pytestmark = [
    pytest.mark.integration,
    pytest.mark.api,
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


@qase.id(30)
@allure.title("Label can be created, listed, and deleted on a repository")
def test_label_lifecycle() -> None:
    """Verify label creation, retrieval, and deletion on a repository."""
    require_api_credentials()

    with api_client() as client:
        owner, repo = create_repo(client)
        try:
            with allure.step("Create a label"):
                label_payload: dict[str, Any] = GiteaLabelFactory.build()
                label_payload["color"] = f"#{label_payload['color'][:6]}"

                create_resp = client.post(
                    f"/repos/{owner}/{repo}/labels",
                    json={"name": label_payload["name"], "color": label_payload["color"]},
                )
                create_resp.raise_for_status()
                label_data = create_resp.json()
                label_id: int = int(label_data["id"])

                assert label_data["name"] == label_payload["name"], "Created label name must match the request"
                assert label_data["color"].lower().lstrip("#") == label_payload["color"].lower().lstrip("#"), (
                    "Created label color must match the request"
                )

            with allure.step("Verify the label appears in the repository's label list"):
                list_resp = client.get(f"/repos/{owner}/{repo}/labels")
                list_resp.raise_for_status()
                labels = list_resp.json()
                assert any(lbl["id"] == label_id for lbl in labels), "Created label must appear in the label list"

            with allure.step("Delete the label and verify it is gone"):
                del_resp = client.delete(f"/repos/{owner}/{repo}/labels/{label_id}")
                assert del_resp.status_code == 204, "Label delete must respond with 204 No Content"

                after_resp = client.get(f"/repos/{owner}/{repo}/labels")
                after_resp.raise_for_status()
                assert not any(lbl["id"] == label_id for lbl in after_resp.json()), (
                    "Deleted label must no longer appear in the label list"
                )
        finally:
            delete_repo(client, owner, repo)


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------


@qase.id(31)
@allure.title("Milestone can be created, retrieved, and deleted on a repository")
def test_milestone_lifecycle() -> None:
    """Verify milestone creation, retrieval, and deletion on a repository."""
    require_api_credentials()

    with api_client() as client:
        owner, repo = create_repo(client)
        try:
            with allure.step("Create a milestone"):
                ms_build: dict[str, Any] = GiteaMilestoneFactory.build()
                deadline_str: str = ms_build["deadline"].strftime("%Y-%m-%dT%H:%M:%SZ")

                create_resp = client.post(
                    f"/repos/{owner}/{repo}/milestones",
                    json={
                        "title": ms_build["title"],
                        "description": ms_build["description"],
                        "due_on": deadline_str,
                    },
                )
                create_resp.raise_for_status()
                ms_data = create_resp.json()
                ms_id: int = int(ms_data["id"])

                assert ms_data["title"] == ms_build["title"], "Created milestone title must match the request"

            with allure.step("Retrieve the milestone by id"):
                get_resp = client.get(f"/repos/{owner}/{repo}/milestones/{ms_id}")
                get_resp.raise_for_status()
                assert get_resp.json()["id"] == ms_id, "Milestone lookup must return the created milestone"

            with allure.step("Delete the milestone"):
                del_resp = client.delete(f"/repos/{owner}/{repo}/milestones/{ms_id}")
                assert del_resp.status_code == 204, "Milestone delete must respond with 204 No Content"
        finally:
            delete_repo(client, owner, repo)


# ---------------------------------------------------------------------------
# Issue comments
# ---------------------------------------------------------------------------


@qase.id(32)
@allure.title("Issue comment can be created, listed, edited, and deleted")
def test_issue_comment_lifecycle() -> None:
    """Verify comment creation, listing, editing, and deletion on an issue."""
    require_api_credentials()

    with api_client() as client:
        owner, repo = create_repo(client)
        try:
            with allure.step("Create an issue"):
                issue_payload: dict[str, Any] = GiteaIssueFactory.build()
                issue_resp = client.post(
                    f"/repos/{owner}/{repo}/issues",
                    json={"title": issue_payload["title"], "body": issue_payload["body"]},
                )
                issue_resp.raise_for_status()
                issue_number: int = int(issue_resp.json()["number"])

            with allure.step("Create a comment on the issue"):
                comment_body = "Automated integration comment"
                comment_resp = client.post(
                    f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    json={"body": comment_body},
                )
                comment_resp.raise_for_status()
                comment_data = comment_resp.json()
                comment_id: int = int(comment_data["id"])

                assert comment_data["body"] == comment_body, "Created comment body must match the request"

            with allure.step("Verify the comment appears in the issue's comment list"):
                list_resp = client.get(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")
                list_resp.raise_for_status()
                assert any(c["id"] == comment_id for c in list_resp.json()), (
                    "Created comment must appear in the comment list"
                )

            with allure.step("Edit the comment"):
                updated_body = "Updated integration comment"
                edit_resp = client.patch(
                    f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
                    json={"body": updated_body},
                )
                edit_resp.raise_for_status()
                assert edit_resp.json()["body"] == updated_body, "Edited comment body must reflect the update"

            with allure.step("Delete the comment"):
                del_resp = client.delete(f"/repos/{owner}/{repo}/issues/comments/{comment_id}")
                assert del_resp.status_code == 204, "Comment delete must respond with 204 No Content"
        finally:
            delete_repo(client, owner, repo)
