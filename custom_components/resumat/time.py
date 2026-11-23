"""Einstellbare Schaltzeiten."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ResumatConfigEntry
from .entity import EXCLUDED_MENUS, ResumatEntity, display_names, is_controlled


def parse_time(value: str | None) -> time | None:
    """'HH:MM:SS' vom Regler in time wandeln.

    Der Regler kennt 24:00:00 als Tagesende; Home Assistant kann das nicht
    darstellen, daher wird es als 23:59:59 angezeigt.
    """
    if not value:
        return None
    try:
        hour, minute, second = (int(p) for p in value.split(":"))
        if (hour, minute, second) == (24, 0, 0):
            return time(23, 59, 59)
        return time(hour, minute, second)
    except ValueError:
        return None


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
        return parse_time(self.raw_value)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        # Rohwert mitgeben, damit z. B. 24:00:00 (Tagesende) erkennbar bleibt
        return {**self._attr_extra_state_attributes, "raw": self.raw_value}

    async def async_set_value(self, value: time) -> None:
        await self.coordinator.async_write_value(self.token, value)
