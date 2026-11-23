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
    """Betriebsart aktiv, wenn Bit 0 gesetzt ist.

    Die Menüs 09.100/09.110/09.120 sind Bitfelder (an der Anlage beobachtet):
    Bit 0 = Verdichter für diesen Kreis aktiv, Bit 2 = externe Anhebung,
    Bit 5 = Sperre, Bit 6 = kein Bedarf. Heizen mit Anhebung liefert z. B. 5,
    daher reicht ein Vergleich auf == 1 nicht.
    """

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool | None:
        value = self.raw_value
        return None if value is None else bool(value & 1)
