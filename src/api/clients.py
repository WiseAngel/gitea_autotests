"""
API clients for test automation.

Provides HTTPX-based async API clients with Gitea-specific helpers for
repository, issue, and user workflows.
"""

from typing import Any

import httpx

from src.api.gitea import build_api_base_url, build_auth_headers, build_issue_payload, build_repo_payload
from src.config.settings import settings


class APIClient:
    """
    Async API client with automatic authentication and base URL handling.

    Usage:
        async with APIClient() as client:
            response = await client.get("/users")

    Attributes:
        base_url: Base API URL from settings
        headers: Default headers including auth token
    """

    def __init__(self, base_url: str | None = None, token: str | None = None):
        """
        Initialize API client.

        Args:
            base_url: Override default API base URL
            token: Override default API token
        """
        self.base_url = build_api_base_url(settings.base_url, base_url or settings.api_base_url)
        self.token = token or settings.api_token
        self._client: httpx.AsyncClient | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Get default headers with authentication."""
        return build_auth_headers(self.token)

    async def __aenter__(self) -> "APIClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=settings.timeout / 1000,
        )
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """
        Make GET request.

        Args:
            path: Request path
            params: Query parameters

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPStatusError: On HTTP error status codes
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return await self._client.get(path, params=params)

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a generic HTTP request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return await self._client.request(method, path, json=json, params=params)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> httpx.Response:
        """
        Make POST request.

        Args:
            path: Request path
            json: JSON body

        Returns:
            httpx.Response object
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return await self._client.post(path, json=json)

    async def put(self, path: str, json: dict[str, Any] | None = None) -> httpx.Response:
        """Make PUT request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return await self._client.put(path, json=json)

    async def delete(self, path: str) -> httpx.Response:
        """Make DELETE request."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return await self._client.delete(path)


class GiteaClient(APIClient):
    """Async client with Gitea-specific endpoint helpers."""

    async def get_authenticated_user(self) -> httpx.Response:
        """Get the currently authenticated user."""
        return await self.get("/user")

    async def list_my_repos(self) -> httpx.Response:
        """List repositories accessible to the authenticated user."""
        return await self.get("/user/repos")

    async def get_user_repos(self, username: str) -> httpx.Response:
        """List repositories owned by a user."""
        return await self.get(f"/users/{username}/repos")

    async def get_repo(self, owner: str, repo: str) -> httpx.Response:
        """Get repository details."""
        return await self.get(f"/repos/{owner}/{repo}")

    async def search_repos(self, query: str) -> httpx.Response:
        """Search repositories by keyword."""
        return await self.get("/repos/search", params={"q": query})

    async def create_repo(
        self,
        name: str,
        *,
        private: bool = False,
        auto_init: bool = True,
        description: str | None = None,
        readme: bool = True,
        default_branch: str | None = None,
    ) -> httpx.Response:
        """Create a repository for the authenticated user."""
        payload = build_repo_payload(
            name,
            private=private,
            auto_init=auto_init,
            description=description,
            readme=readme,
            default_branch=default_branch,
        )
        return await self.post("/user/repos", json=payload)

    async def delete_repo(self, owner: str, repo: str) -> httpx.Response:
        """Delete a repository."""
        return await self.delete(f"/repos/{owner}/{repo}")

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        *,
        body: str | None = None,
        labels: list[int] | None = None,
        assignees: list[str] | None = None,
        milestone: int | None = None,
        ref: str | None = None,
        closed: bool | None = None,
    ) -> httpx.Response:
        """Create an issue in a repository."""
        payload = build_issue_payload(
            title,
            body=body,
            labels=labels,
            assignees=assignees,
            milestone=milestone,
            ref=ref,
            closed=closed,
        )
        return await self.post(f"/repos/{owner}/{repo}/issues", json=payload)
