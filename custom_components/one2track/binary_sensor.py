"""Binary sensors for One2Track watches."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import One2TrackCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: One2TrackCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    devices = coordinator.data or []
    async_add_entities(
        [One2TrackTumbleSensor(coordinator, device) for device in devices]
    )


class One2TrackTumbleSensor(CoordinatorEntity, BinarySensorEntity):
    """Fall/tumble detection sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "tumble"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator: One2TrackCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{device['uuid']}_tumble"

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
    def is_on(self) -> bool | None:
        meta = self._device.get("last_location", {}).get("meta_data", {})
        tumble = meta.get("tumble")
        return tumble == "1" if tumble is not None else None

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            device = next(
                (d for d in self.coordinator.data if d["uuid"] == self._device["uuid"]),
                None,
            )
            if device:
                self._device = device
        self.async_write_ha_state()
