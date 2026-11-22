"""Einstellbare Schaltzeiten."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ResumatConfigEntry
from .entity import EXCLUDED_MENUS, ResumatEntity, display_names, is_controlled


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResumatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    names = display_names(coordinator.tokens)
    async_add_entities(
        ResumatTime(coordinator, token, names[token.menu])
        for token in coordinator.tokens
        if is_controlled(token)
        and token.data_type == "Time"
        and token.menu not in EXCLUDED_MENUS
    )


class ResumatTime(ResumatEntity, TimeEntity):
    @property
    def native_value(self) -> time | None:
        value = self.raw_value  # "HH:MM:SS"
        if not value:
            return None
        try:
            hour, minute, second = (int(p) for p in value.split(":"))
            return time(hour, minute, second)
        except ValueError:
            return None

    async def async_set_value(self, value: time) -> None:
        await self.coordinator.async_write_value(self.token, value)
