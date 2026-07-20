"""
Gitea self-hosted instance seed script for CI.

Creates a public repository with issues so that component and E2E tests
have stable data to assert against.

The admin user and API token are created beforehand via the Gitea CLI
(see the 'Create Gitea admin' step in the workflow). This script expects
API_TOKEN to already be set in the environment, or falls back to Basic Auth
via GITEA_USERNAME + GITEA_PASSWORD.

Usage:
    python scripts/seed_gitea.py

Environment variables:
    BASE_URL        Gitea base URL              (default: http://localhost:3000)
    GITEA_USERNAME  Admin username              (default: testadmin)
    GITEA_PASSWORD  Admin password              (default: testadmin123)
    API_TOKEN       Pre-generated API token     (preferred over Basic Auth)
"""

from __future__ import annotations

import os
import sys
import time

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000").rstrip("/")
ADMIN_USER = os.environ.get("GITEA_USERNAME", "testadmin")
ADMIN_PASS = os.environ.get("GITEA_PASSWORD", "testadmin123")
API_TOKEN = os.environ.get("API_TOKEN", "")
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


def build_client() -> httpx.Client:
    """Build an authenticated HTTP client.

    Prefers token auth; falls back to Basic Auth.

    Returns:
        Configured httpx.Client.
    """
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        print(f"Using API token auth (token: {API_TOKEN[:8]}...)")
        headers["Authorization"] = f"token {API_TOKEN}"
        return httpx.Client(
            base_url=BASE_URL,
            headers=headers,
            timeout=10,
            follow_redirects=True,
        )
    print(f"Using Basic Auth as '{ADMIN_USER}'")
    return httpx.Client(
        base_url=BASE_URL,
        auth=(ADMIN_USER, ADMIN_PASS),
        headers=headers,
        timeout=10,
        follow_redirects=True,
    )


def verify_auth(client: httpx.Client) -> None:
    """Verify that credentials are accepted.

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
        f"GITEA_USERNAME={ADMIN_USER}, API_TOKEN={'set' if API_TOKEN else 'not set'}",
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


def emit_token(token: str) -> None:
    """Write the token to GitHub Actions outputs.

    Args:
        token: The API token value to emit.
    """
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as fh:
            fh.write(f"api_token={token}\n")
        print(f"Token written to GITHUB_OUTPUT (token: {token[:8]}...)")
    else:
        print("WARN: GITHUB_OUTPUT not set; token not persisted.", file=sys.stderr)


def main() -> None:
    """Run the full seed sequence."""
    print(f"Seeding Gitea at {BASE_URL} as '{ADMIN_USER}'")
    wait_for_gitea()

    with build_client() as client:
        verify_auth(client)
        create_repo(client)
        create_issue(client)

    # If token was passed in via env — emit it again for subsequent steps.
    token = API_TOKEN
    if token:
        emit_token(token)
    print("Seed complete.")


if __name__ == "__main__":
    main()
