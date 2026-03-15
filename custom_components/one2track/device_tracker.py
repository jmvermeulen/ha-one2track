"""Device tracker for One2Track watches."""

import logging

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import One2TrackCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: One2TrackCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    devices = coordinator.data or []
    async_add_entities(
        [One2TrackTracker(coordinator, device) for device in devices],
        update_before_add=False,
    )


class One2TrackTracker(CoordinatorEntity, TrackerEntity):
    """Represents a One2Track GPS watch on the map."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:watch"

    def __init__(self, coordinator: One2TrackCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = device["uuid"]

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device["name"],
            manufacturer="One2Track",
            model="Connect MOVE",
            serial_number=self._device["serial_number"],
        )

    @property
    def source_type(self) -> str:
        return "gps"

    @property
    def latitude(self) -> float | None:
        val = self._device.get("last_location", {}).get("latitude")
        try:
            return float(val) if val else None
        except (ValueError, TypeError):
            return None

    @property
    def longitude(self) -> float | None:
        val = self._device.get("last_location", {}).get("longitude")
        try:
            return float(val) if val else None
        except (ValueError, TypeError):
            return None

    @property
    def location_accuracy(self) -> int:
        meta = self._device.get("last_location", {}).get("meta_data", {})
        return int(meta.get("accuracy_meters", 10))

    @property
    def battery_level(self) -> int | None:
        return self._device.get("last_location", {}).get("battery_percentage")

    @property
    def extra_state_attributes(self) -> dict:
        loc = self._device.get("last_location", {})
        sim = self._device.get("simcard", {})
        return {
            "uuid": self._device["uuid"],
            "serial_number": self._device["serial_number"],
            "phone_number": self._device["phone_number"],
            "status": self._device["status"],
            "address": loc.get("address"),
            "location_type": loc.get("location_type"),
            "altitude": loc.get("altitude"),
            "speed": loc.get("speed"),
            "last_communication": loc.get("last_communication"),
            "last_location_update": loc.get("last_location_update"),
            "sim_balance": round((sim.get("balance_cents") or 0) / 100, 2),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            device = next(
                (d for d in self.coordinator.data if d["uuid"] == self.unique_id),
                None,
            )
            if device:
                self._device = device
        self.async_write_ha_state()
