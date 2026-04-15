"""Cast4All FlexMon API client with Keycloak authentication."""

import asyncio
import logging
import time
from typing import Any

from aiohttp import ClientSession, ClientError

from .const import BASE_URL, TOKEN_URL, CLIENT_ID

_LOGGER = logging.getLogger(__name__)

TOKEN_EXPIRY_BUFFER = 30  # seconds before expiry to refresh


class Cast4AllAuthError(Exception):
    """Authentication failed."""


class Cast4AllApiError(Exception):
    """API request failed."""


class Cast4AllConnectionError(Exception):
    """Connection to API failed."""


class Cast4AllApiClient:
    """API client for Cast4All FlexMon."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: float = 0
        self._lock = asyncio.Lock()

    async def _authenticate(self) -> None:
        """Get a new token using password grant."""
        data = {
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "username": self._username,
            "password": self._password,
            "scope": "openid",
        }
        await self._token_request(data)

    async def _refresh(self) -> None:
        """Refresh the token using refresh_token grant."""
        if not self._refresh_token:
            raise Cast4AllAuthError("No refresh token available")
        data = {
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": self._refresh_token,
        }
        await self._token_request(data)

    async def _token_request(self, data: dict) -> None:
        """Execute a token request to Keycloak."""
        try:
            async with self._session.post(TOKEN_URL, data=data) as resp:
                if resp.status == 401 or resp.status == 400:
                    body = await resp.json()
                    error = body.get("error_description", body.get("error", "unknown"))
                    raise Cast4AllAuthError(f"Auth failed: {error}")
                resp.raise_for_status()
                result = await resp.json()
                self._access_token = result["access_token"]
                self._refresh_token = result.get("refresh_token")
                self._token_expiry = time.time() + result.get("expires_in", 300) - TOKEN_EXPIRY_BUFFER
                _LOGGER.debug("Token acquired, expires in %ss", result.get("expires_in"))
        except ClientError as err:
            raise Cast4AllConnectionError(f"Connection failed: {err}") from err

    async def _ensure_token(self) -> None:
        """Ensure we have a valid token."""
        async with self._lock:
            if self._access_token and time.time() < self._token_expiry:
                return
            if self._refresh_token:
                try:
                    await self._refresh()
                    return
                except Cast4AllAuthError:
                    _LOGGER.debug("Refresh failed, trying password grant")
            await self._authenticate()

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an authenticated API request."""
        await self._ensure_token()
        url = f"{BASE_URL}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            async with self._session.request(method, url, headers=headers, **kwargs) as resp:
                if resp.status == 401:
                    # Token might have been invalidated, try once more
                    self._access_token = None
                    self._token_expiry = 0
                    await self._ensure_token()
                    headers = {"Authorization": f"Bearer {self._access_token}"}
                    async with self._session.request(method, url, headers=headers, **kwargs) as retry_resp:
                        retry_resp.raise_for_status()
                        return await retry_resp.json()
                resp.raise_for_status()
                return await resp.json()
        except ClientError as err:
            raise Cast4AllConnectionError(f"API request failed: {err}") from err

    async def get_installations(self) -> list[dict]:
        """Get all installations."""
        data = await self.request("GET", "/installations?size=50")
        return data.get("_embedded", {}).get("installations", [])

    async def get_measurements(self, installation_id: str) -> list[dict]:
        """Get all measurements for an installation."""
        data = await self.request(
            "GET",
            f"/measurements?installation={installation_id}&size=50",
        )
        return data.get("_embedded", {}).get("measurements", [])

    async def validate_credentials(self) -> bool:
        """Validate that credentials work."""
        try:
            await self._authenticate()
            return True
        except (Cast4AllAuthError, Cast4AllConnectionError):
            return False
