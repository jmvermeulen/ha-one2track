"""Data update coordinator for One2Track."""

import asyncio
import logging
from datetime import timedelta

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import One2TrackApiClient, AuthenticationError
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class One2TrackCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch device data from One2Track."""

    def __init__(self, hass: HomeAssistant, client: One2TrackApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="One2Track",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            always_update=False,
        )
        self.client = client

    async def _async_update_data(self) -> list[dict]:
        try:
            async with asyncio.timeout(30):
                return await self.client.async_get_devices()
        except (ClientError, AuthenticationError, TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with One2Track: {err}") from err
