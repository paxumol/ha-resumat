"""Button zum Stellen der Regleruhr auf die Home-Assistant-Zeit."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ResumatConfigEntry
from .coordinator import ResumatCoordinator
from .entity import ResumatEntity
from .tokens import Token

CLOCK_MENU = "05.00"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResumatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ResumatClockSyncButton(coordinator, token)
        for token in coordinator.tokens
        if token.menu == CLOCK_MENU and token.writable
    )


class ResumatClockSyncButton(ResumatEntity, ButtonEntity):
    """Setzt die Uhrzeit (05.00) auf die lokale Zeit von Home Assistant.

    Das Datum (05.01) ist laut Parameterliste nicht beschreibbar.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: ResumatCoordinator, token: Token) -> None:
        super().__init__(coordinator, token, "Uhrzeit synchronisieren")
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{token.menu}_sync"

    async def async_press(self) -> None:
        await self.coordinator.async_write_value(self.token, dt_util.now().time())
