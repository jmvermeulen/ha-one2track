"""Services for One2Track integration."""

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .api import One2TrackApiClient
from .const import DOMAIN, CMD_REFRESH_LOCATION
from .coordinator import One2TrackCoordinator

_LOGGER = logging.getLogger(__name__)


def _resolve_device(hass: HomeAssistant, entity_ids: list[str]) -> tuple[str, One2TrackApiClient, One2TrackCoordinator]:
    """Resolve entity IDs to a device UUID, its API client, and coordinator."""
    if not entity_ids:
        raise HomeAssistantError("No target entity specified")

    registry = er.async_get(hass)

    for entity_id in entity_ids:
        entry = registry.async_get(entity_id)
        if not entry or entry.platform != DOMAIN:
            continue

        unique_id = entry.unique_id
        for entry_data in hass.data.get(DOMAIN, {}).values():
            if not isinstance(entry_data, dict):
                continue
            coordinator: One2TrackCoordinator = entry_data.get("coordinator")
            if not coordinator or not coordinator.data:
                continue
            for device in coordinator.data:
                uuid = device.get("uuid", "")
                if unique_id == uuid or unique_id.startswith(uuid + "_"):
                    return uuid, entry_data["client"], coordinator

    raise HomeAssistantError(f"Could not resolve One2Track device from {entity_ids}")


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register One2Track services."""
    if hass.services.has_service(DOMAIN, "send_message"):
        return

    async def handle_send_message(call: ServiceCall) -> None:
        entity_ids = call.data.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        message = call.data["message"]
        uuid, client, _ = _resolve_device(hass, entity_ids)

        _LOGGER.info("Sending message to %s: %s", uuid, message)
        success = await client.async_send_message(uuid, message)
        if not success:
            raise HomeAssistantError("Failed to send message")

    async def handle_force_update(call: ServiceCall) -> None:
        entity_ids = call.data.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        uuid, client, coordinator = _resolve_device(hass, entity_ids)

        _LOGGER.info("Force location update for %s", uuid)
        success = await client.async_send_command(uuid, CMD_REFRESH_LOCATION, "Ververs locatie")
        if not success:
            raise HomeAssistantError("Failed to force location update (watch may be offline)")

        await coordinator.async_request_refresh()

    async def handle_send_command(call: ServiceCall) -> None:
        entity_ids = call.data.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        code = call.data["code"]
        name = call.data.get("name", "")
        value = call.data.get("value", "")
        uuid, client, _ = _resolve_device(hass, entity_ids)

        _LOGGER.info("Sending command %s to %s", code, uuid)
        success = await client.async_send_command(uuid, code, name, value)
        if not success:
            raise HomeAssistantError(f"Command {code} failed (watch may be offline)")

    hass.services.async_register(
        DOMAIN,
        "send_message",
        handle_send_message,
        schema=vol.Schema({
            vol.Required("entity_id"): vol.Any(str, [str]),
            vol.Required("message"): str,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        "force_update",
        handle_force_update,
        schema=vol.Schema({
            vol.Required("entity_id"): vol.Any(str, [str]),
        }),
    )

    hass.services.async_register(
        DOMAIN,
        "send_command",
        handle_send_command,
        schema=vol.Schema({
            vol.Required("entity_id"): vol.Any(str, [str]),
            vol.Required("code"): str,
            vol.Optional("name", default=""): str,
            vol.Optional("value", default=""): str,
        }),
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove One2Track services."""
    for service in ("send_message", "force_update", "send_command"):
        hass.services.async_remove(DOMAIN, service)
