"""
One2Track API session concept.
Demonstrates login, session persistence, and device data retrieval.

Usage:
    export ONE2TRACK_EMAIL="your@email.com"
    export ONE2TRACK_PASSWORD="your_password"
    python3 session_test.py
"""

import json
import os
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

import requests

BASE_URL = "https://www.one2trackgps.com"
SESSION_FILE = Path(__file__).parent / ".session.json"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0"


@dataclass
class Session:
    cookie: str
    account_id: str
    created_at: str

    def save(self):
        SESSION_FILE.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> "Session | None":
        if SESSION_FILE.exists():
            data = json.loads(SESSION_FILE.read_text())
            return cls(**data)
        return None


class One2TrackAPI:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.cookie = ""
        self.account_id = ""

    def _set_cookies(self):
        self.session.cookies.set("_iadmin", self.cookie, domain="www.one2trackgps.com")
        self.session.cookies.set("accepted_cookies", "true", domain="www.one2trackgps.com")

    def try_restore_session(self) -> bool:
        """Try to restore a saved session. Returns True if session is still valid."""
        saved = Session.load()
        if not saved:
            return False

        self.cookie = saved.cookie
        self.account_id = saved.account_id
        self._set_cookies()

        # Test if session is still valid by fetching devices
        resp = self.session.get(
            f"{BASE_URL}/users/{self.account_id}/devices",
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            allow_redirects=False,
        )

        if resp.status_code == 200:
            print(f"Restored session for account '{self.account_id}' (saved {saved.created_at})")
            return True

        print(f"Saved session expired (status {resp.status_code}), re-authenticating...")
        SESSION_FILE.unlink(missing_ok=True)
        return False

    def login(self) -> bool:
        """Full login flow: get CSRF, post credentials, extract account_id."""
        # Step 1: Get CSRF token
        resp = self.session.get(f"{BASE_URL}/auth/users/sign_in")
        if resp.status_code != 200:
            print(f"Failed to get login page: {resp.status_code}")
            return False

        csrf_match = re.search(r'name="csrf-token" content="([^"]+)"', resp.text)
        if not csrf_match:
            print("CSRF token not found in login page")
            return False

        csrf_token = csrf_match.group(1)
        self.cookie = resp.cookies.get("_iadmin", "")
        self._set_cookies()

        # Step 2: POST login
        login_data = {
            "authenticity_token": csrf_token,
            "user[login]": self.email,
            "user[password]": self.password,
            "gdpr": "1",
            "user[remember_me]": "1",
        }

        resp = self.session.post(
            f"{BASE_URL}/auth/users/sign_in",
            data=login_data,
            allow_redirects=False,
        )

        if resp.status_code != 302 or "_iadmin" not in resp.headers.get("Set-Cookie", ""):
            print(f"Login failed: status {resp.status_code}")
            return False

        self.cookie = resp.cookies.get("_iadmin", "")
        self._set_cookies()

        # Step 3: Follow redirect to get account_id
        resp = self.session.get(BASE_URL, allow_redirects=False)
        location = resp.headers.get("Location", "")
        match = re.search(r"/users/([^/]+)/", location)
        if not match:
            print(f"Could not extract account_id from redirect: {location}")
            return False

        self.account_id = match.group(1)
        print(f"Logged in as '{self.account_id}'")

        # Save session
        Session(
            cookie=self.cookie,
            account_id=self.account_id,
            created_at=datetime.now().isoformat(),
        ).save()

        return True

    def get_devices(self) -> list[dict]:
        """Fetch all devices with location data."""
        resp = self.session.get(
            f"{BASE_URL}/users/{self.account_id}/devices",
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
        )
        resp.raise_for_status()
        return [item["device"] for item in resp.json()]

    def get_geofences(self, device_uuid: str) -> dict:
        """Fetch geofences for a device."""
        resp = self.session.get(
            f"{BASE_URL}/devices/{device_uuid}/geofences",
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
        )
        resp.raise_for_status()
        return resp.json()

    def get_history(self, device_uuid: str, date: str) -> list[dict]:
        """Fetch location history for a device on a given date (YYYY-MM-DD)."""
        resp = self.session.get(
            f"{BASE_URL}/devices/{device_uuid}/history",
            params={"date": date},
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
        )
        resp.raise_for_status()
        return resp.json()


def main():
    api = One2TrackAPI(
        os.environ.get("ONE2TRACK_EMAIL", "your@email.com"),
        os.environ.get("ONE2TRACK_PASSWORD", "your_password"),
    )

    # Try saved session first, login if needed
    if not api.try_restore_session():
        if not api.login():
            print("Authentication failed")
            return

    # Fetch devices
    devices = api.get_devices()
    print(f"\nFound {len(devices)} device(s):\n")

    for dev in devices:
        loc = dev.get("last_location", {})
        meta = loc.get("meta_data", {})
        sim = dev.get("simcard", {})

        print(f"  Name:          {dev['name']}")
        print(f"  Status:        {dev['status']}")
        print(f"  Serial:        {dev['serial_number']}")
        print(f"  UUID:          {dev['uuid']}")
        print(f"  Phone:         {dev['phone_number']}")
        print(f"  Battery:       {loc.get('battery_percentage')}%")
        print(f"  Signal:        {loc.get('signal_strength')}")
        print(f"  Location:      {loc.get('latitude')}, {loc.get('longitude')}")
        print(f"  Address:       {loc.get('address')}")
        print(f"  Location type: {loc.get('location_type')}")
        print(f"  Accuracy:      {meta.get('accuracy_meters')}m")
        print(f"  Steps:         {meta.get('steps')}")
        print(f"  Last seen:     {loc.get('last_communication')}")
        print(f"  Last GPS:      {loc.get('last_location_update')}")
        print(f"  SIM balance:   €{sim.get('balance_cents', 0) / 100:.2f}")
        print(f"  WiFi networks: {len(meta.get('routers', []))}")
        print(f"  Cell towers:   {len(meta.get('stations', []))}")

        # Geofences
        fences = api.get_geofences(dev["uuid"])
        print(f"  Geofences:     {len(fences.get('fences', []))}")
        print()


if __name__ == "__main__":
    main()
