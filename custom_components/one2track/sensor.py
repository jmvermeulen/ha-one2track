"""Sensors for One2Track watches."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfSpeed
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import One2TrackCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class One2TrackSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any]


def _loc(device: dict) -> dict:
    return device.get("last_location", {})


def _meta(device: dict) -> dict:
    return _loc(device).get("meta_data", {})


SENSORS: list[One2TrackSensorDescription] = [
    One2TrackSensorDescription(
        key="battery",
        translation_key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _loc(d).get("battery_percentage"),
    ),
    One2TrackSensorDescription(
        key="sim_balance",
        translation_key="sim_balance",
        native_unit_of_measurement="EUR",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:sim",
        value_fn=lambda d: round(c / 100, 2) if (c := d.get("simcard", {}).get("balance_cents")) is not None else None,
    ),
    One2TrackSensorDescription(
        key="signal_strength",
        translation_key="signal_strength",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal",
        value_fn=lambda d: _loc(d).get("signal_strength"),
    ),
    One2TrackSensorDescription(
        key="steps",
        translation_key="steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:shoe-print",
        value_fn=lambda d: int(v) if (v := _meta(d).get("steps")) is not None else None,
    ),
    One2TrackSensorDescription(
        key="speed",
        translation_key="speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: float(v) if (v := _loc(d).get("speed")) is not None else None,
    ),
    One2TrackSensorDescription(
        key="accuracy",
        translation_key="accuracy",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:crosshairs-gps",
        value_fn=lambda d: _meta(d).get("accuracy_meters"),
    ),
    One2TrackSensorDescription(
        key="altitude",
        translation_key="altitude",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:altimeter",
        value_fn=lambda d: float(v) if (v := _loc(d).get("altitude")) is not None else None,
    ),
    One2TrackSensorDescription(
        key="satellite_count",
        translation_key="satellite_count",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:satellite-variant",
        value_fn=lambda d: _loc(d).get("satellite_count"),
    ),
    One2TrackSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=["gps", "wifi", "offline"],
        icon="mdi:access-point-network",
        value_fn=lambda d: d.get("status", "").lower() or None,
    ),
    One2TrackSensorDescription(
        key="location_type",
        translation_key="location_type",
        device_class=SensorDeviceClass.ENUM,
        options=["gps", "wifi", "lbs"],
        icon="mdi:map-marker-question",
        value_fn=lambda d: v.lower() if (v := _loc(d).get("location_type")) else None,
    ),
    One2TrackSensorDescription(
        key="address",
        translation_key="address",
        icon="mdi:map-marker",
        value_fn=lambda d: _loc(d).get("address"),
    ),
    One2TrackSensorDescription(
        key="last_seen",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: datetime.fromisoformat(v) if (v := _loc(d).get("last_communication")) else None,
    ),
    One2TrackSensorDescription(
        key="last_gps",
        translation_key="last_gps",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: datetime.fromisoformat(v) if (v := _loc(d).get("last_location_update")) else None,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: One2TrackCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    devices = coordinator.data or []
    async_add_entities(
        [
            One2TrackSensor(coordinator, device, desc)
            for device in devices
            for desc in SENSORS
        ]
    )


class One2TrackSensor(CoordinatorEntity, SensorEntity):
    """A One2Track sensor entity."""

    entity_description: One2TrackSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: One2TrackCoordinator,
        device: dict,
        description: One2TrackSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device = device
        self._attr_unique_id = f"{device['uuid']}_{description.key}"

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
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._device)

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
