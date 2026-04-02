"""One2Track API client."""

import re
import logging

from aiohttp import ClientSession

from .const import BASE_URL, LOGIN_URL

_LOGGER = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class One2TrackApiClient:
    """Client for the One2Track web API."""

    def __init__(self, username: str, password: str, session: ClientSession) -> None:
        self._username = username
        self._password = password
        self._session = session
        self._cookie = ""
        self._account_id = ""

    @property
    def account_id(self) -> str:
        return self._account_id

    def _cookies(self) -> dict[str, str]:
        cookies = {"accepted_cookies": "true"}
        if self._cookie:
            cookies["_iadmin"] = self._cookie
        return cookies

    async def _get(self, url: str, *, json: bool = False, allow_redirects: bool = True):
        headers = {}
        if json:
            headers["Accept"] = "application/json"
            headers["X-Requested-With"] = "XMLHttpRequest"
        return await self._session.get(
            url,
            headers=headers,
            cookies=self._cookies(),
            allow_redirects=allow_redirects,
        )

    async def _post(self, url: str, data: dict, *, extra_headers: dict | None = None):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        if extra_headers:
            headers.update(extra_headers)
        return await self._session.post(
            url,
            data=data,
            headers=headers,
            cookies=self._cookies(),
            allow_redirects=False,
        )

    async def _get_csrf_token(self) -> str:
        """Get a CSRF token from an HTML page."""
        resp = await self._get(f"{BASE_URL}/users/{self._account_id}/devices")
        if resp.status != 200:
            # Fall back to login page (will 302 if already logged in)
            resp = await self._get(LOGIN_URL)
        html = await resp.text()
        match = re.search(r'name="csrf-token" content="([^"]+)"', html)
        if not match:
            raise AuthenticationError("Could not extract CSRF token")
        # Update cookie if server sent a new one
        new_cookie = resp.cookies.get("_iadmin")
        if new_cookie:
            self._cookie = new_cookie.value
        return match.group(1)

    async def authenticate(self) -> str:
        """Full login flow. Returns account_id."""
        # Step 1: Get login page for CSRF token + initial cookie
        resp = await self._get(LOGIN_URL)

        # If we get a 302, we're already logged in
        if resp.status == 302:
            new_cookie = resp.cookies.get("_iadmin")
            if new_cookie:
                self._cookie = new_cookie.value
            return await self._get_account_id()

        if resp.status != 200:
            raise AuthenticationError(f"Login page returned {resp.status}")

        html = await resp.text()
        match = re.search(r'name="csrf-token" content="([^"]+)"', html)
        if not match:
            raise AuthenticationError("CSRF token not found")
        csrf = match.group(1)

        initial_cookie = resp.cookies.get("_iadmin")
        if initial_cookie:
            self._cookie = initial_cookie.value

        # Step 2: POST login
        resp = await self._post(LOGIN_URL, data={
            "authenticity_token": csrf,
            "user[login]": self._username,
            "user[password]": self._password,
            "gdpr": "1",
            "user[remember_me]": "1",
        })

        if resp.status != 302:
            raise AuthenticationError("Invalid username or password")

        new_cookie = resp.cookies.get("_iadmin")
        if not new_cookie:
            raise AuthenticationError("No session cookie after login")
        self._cookie = new_cookie.value

        # Step 3: Extract account ID
        return await self._get_account_id()

    async def _get_account_id(self) -> str:
        """Follow redirect from base URL to extract account_id."""
        resp = await self._get(BASE_URL, allow_redirects=False)
        location = resp.headers.get("Location", "")
        match = re.search(r"/users/([^/]+)", location)
        if not match:
            raise AuthenticationError(f"Could not extract account ID from: {location}")
        self._account_id = match.group(1)
        return self._account_id

    async def _ensure_authenticated(self) -> None:
        """Re-authenticate if session is invalid."""
        if not self._cookie or not self._account_id:
            await self.authenticate()
            return

        # Test if session is still valid
        resp = await self._get(
            f"{BASE_URL}/users/{self._account_id}/devices",
            json=True,
            allow_redirects=False,
        )
        if resp.status != 200:
            _LOGGER.debug("Session expired, re-authenticating")
            self._cookie = ""
            self._session.cookie_jar.clear()
            await self.authenticate()

    async def async_get_devices(self) -> list[dict]:
        """Fetch all devices with location data."""
        await self._ensure_authenticated()
        resp = await self._get(
            f"{BASE_URL}/users/{self._account_id}/devices",
            json=True,
        )
        if resp.status != 200:
            raise AuthenticationError(f"Failed to get devices: {resp.status}")
        data = await resp.json(content_type=None)
        return [item["device"] for item in data]

    async def async_get_geofences(self, device_uuid: str) -> dict:
        """Fetch geofences for a device."""
        await self._ensure_authenticated()
        resp = await self._get(
            f"{BASE_URL}/devices/{device_uuid}/geofences",
            json=True,
        )
        if resp.status != 200:
            return {"fences": []}
        return await resp.json(content_type=None)

    async def async_send_message(self, device_uuid: str, message: str) -> bool:
        """Send a text message to a watch. Max 30 characters."""
        await self._ensure_authenticated()
        csrf = await self._get_csrf_token()

        resp = await self._post(
            f"{BASE_URL}/devices/{device_uuid}/messages",
            data={
                "utf8": "\u2713",
                "authenticity_token": csrf,
                "device_message[message]": message[:30],
            },
            extra_headers={
                "X-CSRF-Token": csrf,
                "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
            },
        )
        return resp.status == 200

    async def async_send_command(self, device_uuid: str, code: str, name: str = "", value: str = "") -> bool:
        """Send a command to a watch via the functions endpoint."""
        await self._ensure_authenticated()
        csrf = await self._get_csrf_token()

        data = {
            "utf8": "\u2713",
            "function[code]": code,
            "function[name]": name,
        }
        if value:
            data["function[value]"] = value

        resp = await self._post(
            f"{BASE_URL}/api/devices/{device_uuid}/functions",
            data=data,
            extra_headers={
                "X-CSRF-Token": csrf,
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        if resp.status != 200:
            return False

        # Check response for success/failure
        text = await resp.text()
        return "opgeslagen" in text and "niet" not in text
