"""Binärsensoren: 0/1-Werte und aktive Betriebsarten."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ResumatConfigEntry
from .coordinator import ResumatCoordinator
from .entity import EXCLUDED_MENUS, MODE_MENUS, ResumatEntity, display_names, is_controlled
from .tokens import Token


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResumatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    names = display_names(coordinator.tokens)
    entities: list[BinarySensorEntity] = []
    for token in coordinator.tokens:
        if token.menu in EXCLUDED_MENUS or is_controlled(token):
            continue
        if token.menu in MODE_MENUS:
            entities.append(ResumatModeSensor(coordinator, token, MODE_MENUS[token.menu]))
        elif token.data_type == "Boolean":
            entities.append(ResumatBinarySensor(coordinator, token, names[token.menu]))
    async_add_entities(entities)


class ResumatBinarySensor(ResumatEntity, BinarySensorEntity):
    def __init__(self, coordinator: ResumatCoordinator, token: Token, name: str) -> None:
        super().__init__(coordinator, token, name)
        if not token.dynamic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        value = self.raw_value
        return None if value is None else bool(value)


class ResumatModeSensor(ResumatEntity, BinarySensorEntity):
    """Betriebsart aktiv, wenn der Wert 1 ist (wie reformatMode im Java-Adapter)."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool | None:
        value = self.raw_value
        return None if value is None else value == 1
