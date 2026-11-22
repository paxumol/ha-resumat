"""Schalter für beschreibbare 0/1-Werte (z. B. Abschaltungen)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
        ResumatSwitch(coordinator, token, names[token.menu])
        for token in coordinator.tokens
        if is_controlled(token)
        and token.data_type == "Boolean"
        and token.menu not in EXCLUDED_MENUS
    )


class ResumatSwitch(ResumatEntity, SwitchEntity):
    """An = Wert 1. Achtung: bei „Abschaltung“ bedeutet An = abgeschaltet."""

    @property
    def is_on(self) -> bool | None:
        value = self.raw_value
        return None if value is None else bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_value(self.token, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_value(self.token, False)
