"""
Gitea self-hosted instance seed script for CI.

Creates an admin user, a public repository with issues, and a public user
profile so that component and E2E tests have stable data to assert against.

Usage:
    python scripts/seed_gitea.py

Environment variables:
    BASE_URL        Gitea base URL (default: http://localhost:3000)
    GITEA_USERNAME  Admin username to create (default: testadmin)
    GITEA_PASSWORD  Admin password (default: testadmin123)
"""

from __future__ import annotations

import sys
import time

import httpx

BASE_URL = "http://localhost:3000"
ADMIN_USER = "testadmin"
ADMIN_PASS = "testadmin123"
ADMIN_EMAIL = "testadmin@example.com"
API_URL = f"{BASE_URL}/api/v1"

# Public "mirror" repo that component tests look for.
# We create it under the admin user so /testadmin/go-sdk exists.
SEED_REPO = "go-sdk"
SEED_ISSUE_TITLE = "Seed issue for CI"


def wait_for_gitea(timeout: int = 60) -> None:
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


def create_admin(client: httpx.Client) -> None:
    """Register the admin user via the installation endpoint.

    Gitea exposes a one-time POST /api/v1/admin/self-info that does not
    require auth only during the *first* install. For fresh containers we
    use the gitea admin CLI approach via the /api/v1/admin/users endpoint
    with basic auth from the default internal admin token.

    For simplicity we use the public registration endpoint instead and
    then promote the user to admin via the env flag GITEA_ADMIN pre-set
    in the Docker image (see workflow).

    Args:
        client: HTTP client without auth headers.
    """
    payload = {
        "username": ADMIN_USER,
        "password": ADMIN_PASS,
        "retype": ADMIN_PASS,
        "email": ADMIN_EMAIL,
        "must_change_password": False,
    }
    r = client.post(f"{API_URL}/admin/users", json=payload)
    if r.status_code in (200, 201):
        print(f"Admin user '{ADMIN_USER}' created.")
    elif r.status_code == 422 and "user already exists" in r.text.lower():
        print(f"Admin user '{ADMIN_USER}' already exists, skipping.")
    else:
        print(f"WARN: create admin returned {r.status_code}: {r.text}", file=sys.stderr)


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


def main() -> None:
    """Run the full seed sequence."""
    wait_for_gitea()

    # Bootstrap client uses basic auth with the built-in gitea admin.
    # The gitea Docker image creates an initial admin when GITEA_ADMIN_* env
    # vars are set (see e2e.yml). We use those creds here.
    with httpx.Client(
        base_url=BASE_URL,
        auth=(ADMIN_USER, ADMIN_PASS),
        headers={"Content-Type": "application/json"},
        timeout=10,
        follow_redirects=True,
    ) as client:
        create_repo(client)
        create_issue(client)
        token = generate_api_token(client)

    if token:
        # Emit as GitHub Actions output so subsequent steps can consume it.
        print(f"::set-output name=api_token::{token}")
        # Also write to $GITHUB_OUTPUT if available.
        import os

        gh_output = os.environ.get("GITHUB_OUTPUT")
        if gh_output:
            with open(gh_output, "a") as fh:
                fh.write(f"api_token={token}\n")

    print("Seed complete.")


if __name__ == "__main__":
    main()
