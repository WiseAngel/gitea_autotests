"""
Gitea self-hosted instance seed script for CI.

Creates a public repository with issues so that component and E2E tests
have stable data to assert against.

Usage:
    python scripts/seed_gitea.py

Environment variables (all optional, have defaults matching the CI workflow):
    BASE_URL        Gitea base URL              (default: http://localhost:3000)
    GITEA_USERNAME  Admin username              (default: testadmin)
    GITEA_PASSWORD  Admin password              (default: testadmin123)
"""

from __future__ import annotations

import os
import sys
import time

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000").rstrip("/")
ADMIN_USER = os.environ.get("GITEA_USERNAME", "testadmin")
ADMIN_PASS = os.environ.get("GITEA_PASSWORD", "testadmin123")
ADMIN_EMAIL = f"{ADMIN_USER}@example.com"
API_URL = f"{BASE_URL}/api/v1"

SEED_REPO = "go-sdk"
SEED_ISSUE_TITLE = "Seed issue for CI"


def wait_for_gitea(timeout: int = 90) -> None:
    """Poll until Gitea is accepting HTTP requests.

    Args:
        timeout: Maximum seconds to wait.

    Raises:
        SystemExit: If Gitea does not respond within timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE_URL}/api/healthz", timeout=3)
            if r.status_code == 200:
                print("Gitea is ready.")
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    print("ERROR: Gitea did not become ready in time.", file=sys.stderr)
    sys.exit(1)


def verify_auth(client: httpx.Client) -> None:
    """Verify that basic-auth credentials are accepted.

    Args:
        client: Authenticated HTTP client.

    Raises:
        SystemExit: If authentication fails.
    """
    r = client.get(f"{API_URL}/user")
    if r.status_code == 200:
        print(f"Authenticated as '{r.json().get('login')}'.")
        return
    print(
        f"ERROR: auth check returned {r.status_code}: {r.text}\n"
        f"Make sure GITEA_USERNAME={ADMIN_USER} and GITEA_PASSWORD are correct.",
        file=sys.stderr,
    )
    sys.exit(1)


def create_repo(client: httpx.Client) -> None:
    """Create the seed public repository.

    Args:
        client: Authenticated HTTP client.
    """
    payload = {
        "name": SEED_REPO,
        "description": "Seed repo for CI component tests",
        "private": False,
        "auto_init": True,
        "readme": "Default",
        "default_branch": "main",
    }
    r = client.post(f"{API_URL}/user/repos", json=payload)
    if r.status_code in (200, 201):
        print(f"Repo '{ADMIN_USER}/{SEED_REPO}' created.")
    elif r.status_code == 409:
        print(f"Repo '{ADMIN_USER}/{SEED_REPO}' already exists, skipping.")
    else:
        print(f"WARN: create repo returned {r.status_code}: {r.text}", file=sys.stderr)


def create_issue(client: httpx.Client) -> None:
    """Create a seed issue in the public repository.

    Args:
        client: Authenticated HTTP client.
    """
    payload = {"title": SEED_ISSUE_TITLE, "body": "Automatically seeded by CI."}
    r = client.post(f"{API_URL}/repos/{ADMIN_USER}/{SEED_REPO}/issues", json=payload)
    if r.status_code in (200, 201):
        print(f"Seed issue created in '{ADMIN_USER}/{SEED_REPO}'.")
    else:
        print(f"WARN: create issue returned {r.status_code}: {r.text}", file=sys.stderr)


def generate_api_token(client: httpx.Client) -> str:
    """Generate a personal access token for the admin user.

    Deletes any existing token with the same name first so that re-runs
    always produce a fresh token value.

    Args:
        client: Authenticated HTTP client.

    Returns:
        The generated token string.

    Raises:
        SystemExit: If token generation fails.
    """
    token_name = "ci-token"

    # Delete existing token if present (idempotent re-runs).
    del_r = client.delete(f"{API_URL}/users/{ADMIN_USER}/tokens/{token_name}")
    if del_r.status_code == 204:
        print(f"Existing token '{token_name}' deleted.")

    payload = {
        "name": token_name,
        "scopes": ["write:issue", "write:repository", "read:user"],
    }
    r = client.post(f"{API_URL}/users/{ADMIN_USER}/tokens", json=payload)
    if r.status_code in (200, 201):
        token: str = r.json()["sha1"]
        print(f"API token generated: {token[:8]}...")
        return token
    print(f"ERROR: generate token returned {r.status_code}: {r.text}", file=sys.stderr)
    sys.exit(1)


def emit_token(token: str) -> None:
    """Write the token to GitHub Actions outputs.

    Args:
        token: The API token value to emit.
    """
    # Legacy set-output (still shown in logs for visibility).
    print(f"::set-output name=api_token::{token}")

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as fh:
            fh.write(f"api_token={token}\n")
        print("Token written to GITHUB_OUTPUT.")
    else:
        print("WARN: GITHUB_OUTPUT not set; token not persisted for subsequent steps.", file=sys.stderr)


def main() -> None:
    """Run the full seed sequence."""
    print(f"Seeding Gitea at {BASE_URL} as '{ADMIN_USER}'")
    wait_for_gitea()

    with httpx.Client(
        base_url=BASE_URL,
        auth=(ADMIN_USER, ADMIN_PASS),
        headers={"Content-Type": "application/json"},
        timeout=10,
        follow_redirects=True,
    ) as client:
        verify_auth(client)
        create_repo(client)
        create_issue(client)
        token = generate_api_token(client)

    emit_token(token)
    print("Seed complete.")


if __name__ == "__main__":
    main()
