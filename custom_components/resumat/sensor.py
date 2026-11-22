"""Sensoren für Zahlen- und Textwerte."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPressure, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ResumatConfigEntry
from .coordinator import ResumatCoordinator
from .entity import (
    DUPLICATE_MENUS,
    EXCLUDED_MENUS,
    MODE_MENUS,
    ResumatEntity,
    display_names,
    is_controlled,
)
from .tokens import Token

NUMERIC_TYPES = {"Float", "Integer"}
DIAGNOSTIC_TYPES = {"Binary", "Text", "IntegerString", "Date"}

# CSV-Einheit (ohne Leerzeichen, klein) -> (Einheit, Device Class, State Class)
UNIT_MAP = {
    "gradcelsius": (UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    "gradcelcius": (UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    "kelvin": (UnitOfTemperature.KELVIN, None, SensorStateClass.MEASUREMENT),  # Hysterese/Differenz
    "stunden": (UnitOfTime.HOURS, SensorDeviceClass.DURATION, SensorStateClass.TOTAL_INCREASING),
    "minuten": (UnitOfTime.MINUTES, SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT),
    "bardruck": (UnitOfPressure.BAR, SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    "prozent": (PERCENTAGE, None, SensorStateClass.MEASUREMENT),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResumatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    names = display_names(coordinator.tokens)
    async_add_entities(
        ResumatSensor(coordinator, token, names[token.menu])
        for token in coordinator.tokens
        if token.data_type != "Boolean"
        and token.menu not in EXCLUDED_MENUS | DUPLICATE_MENUS
        and token.menu not in MODE_MENUS
        and not is_controlled(token)
    )


class ResumatSensor(ResumatEntity, SensorEntity):
    def __init__(self, coordinator: ResumatCoordinator, token: Token, name: str) -> None:
        super().__init__(coordinator, token, name)
        if token.data_type in NUMERIC_TYPES:
            mapped = UNIT_MAP.get(token.unit.replace(" ", "").lower())
            if mapped:
                (
                    self._attr_native_unit_of_measurement,
                    self._attr_device_class,
                    self._attr_state_class,
                ) = mapped
            else:
                self._attr_state_class = SensorStateClass.MEASUREMENT
            if token.data_type == "Float":
                self._attr_suggested_display_precision = 1
        if token.data_type in DIAGNOSTIC_TYPES or (
            not token.dynamic and token.data_type not in NUMERIC_TYPES
        ):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if token.data_type == "Binary":
            # Bitfelder (Statusregister) – bei Bedarf manuell aktivieren
            self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self):
        return self.raw_value
