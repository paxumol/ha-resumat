"""Gemeinsame Basis für alle Resümat-Entitäten."""

from __future__ import annotations

from collections import Counter

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ResumatCoordinator
from .tokens import Token

# Kennwort nicht als Entität anlegen
EXCLUDED_MENUS = {"06.00"}

# Betriebsarten: Integer-Variante wird als Binärsensor dargestellt,
# die Binary-Duplikate unter gleicher Adresse werden ausgelassen.
MODE_MENUS = {
    "09.100": "Heizbetrieb",
    "09.110": "Kühlbetrieb",
    "09.120": "Warmwasserbetrieb",
}
DUPLICATE_MENUS = {"09.10", "09.11", "09.12"}

# Beschreibbare Werte, die als Steuer-Entität (number/switch/time) angelegt
# werden und daher nicht zusätzlich als Sensor. Die Uhrzeit (05.00) bleibt Sensor;
# gestellt wird sie über den Button „Uhrzeit synchronisieren“ (button.py).
NOT_CONTROLLED = {"05.00"}


def is_controlled(token: Token) -> bool:
    return token.writable and token.menu not in NOT_CONTROLLED


def device_info(coordinator: ResumatCoordinator) -> DeviceInfo:
    entry = coordinator.config_entry
    return DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        name=entry.title,
        manufacturer="Resümat",
        model="Wärmepumpenregler",
    )


def display_names(tokens: list[Token]) -> dict[str, str]:
    """Name je Menü; bei doppelten Namen die Menünummer anhängen."""
    counts = Counter(t.name for t in tokens)
    return {
        t.menu: f"{t.name} ({t.menu})" if counts[t.name] > 1 else t.name
        for t in tokens
    }


class ResumatEntity(CoordinatorEntity[ResumatCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ResumatCoordinator, token: Token, name: str) -> None:
        super().__init__(coordinator)
        self.token = token
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{token.menu}"
        self._attr_name = name
        self._attr_device_info = device_info(coordinator)
        self._attr_extra_state_attributes = {"menu": token.menu}

    @property
    def raw_value(self):
        return (self.coordinator.data or {}).get(self.token.menu)

    @property
    def available(self) -> bool:
        return super().available and self.raw_value is not None
