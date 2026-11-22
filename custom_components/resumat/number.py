"""Einstellbare Zahlenwerte (Sollwerte, Hysteresen, Anhebung)."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ResumatConfigEntry
from .coordinator import ResumatCoordinator
from .entity import EXCLUDED_MENUS, ResumatEntity, display_names, is_controlled
from .tokens import Token

# Erlaubte Bereiche je Menü: (min, max, schritt). Werte außerhalb lehnt HA ab.
# Nur Menüs mit Eintrag hier werden beschreibbar angelegt.
LIMITS: dict[str, tuple[float, float, float]] = {
    "02.10": (-5.0, 10.0, 0.5),   # Externe Anhebung (ob negativ zulässig ist, noch ungeprüft)
    "04.04": (30.0, 60.0, 0.5),   # Warmwasser Soll
    "04.05": (15.0, 40.0, 0.5),   # Beckenwasser Soll
    "04.06": (1.0, 10.0, 0.5),    # Warmwasser Hysterese
    "04.07": (1.0, 10.0, 0.5),    # Beckenwasser Hysterese
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResumatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    names = display_names(coordinator.tokens)
    async_add_entities(
        ResumatNumber(coordinator, token, names[token.menu])
        for token in coordinator.tokens
        if is_controlled(token)
        and token.data_type == "Float"
        and token.menu in LIMITS
        and token.menu not in EXCLUDED_MENUS
    )


class ResumatNumber(ResumatEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ResumatCoordinator, token: Token, name: str) -> None:
        super().__init__(coordinator, token, name)
        self._attr_native_min_value, self._attr_native_max_value, self._attr_native_step = (
            LIMITS[token.menu]
        )
        unit = token.unit.replace(" ", "").lower()
        if unit in ("gradcelsius", "gradcelcius"):
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            if token.menu != "02.10":  # Anhebung ist eine Differenz, keine Temperatur
                self._attr_device_class = NumberDeviceClass.TEMPERATURE
        elif unit == "kelvin":
            self._attr_native_unit_of_measurement = UnitOfTemperature.KELVIN

    @property
    def native_value(self) -> float | None:
        return self.raw_value

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write_value(self.token, value)
