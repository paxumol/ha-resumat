"""DataUpdateCoordinator: liest den Adapter zyklisch aus und schreibt Werte."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .protocol import ResumatProtocolError, async_read_memory_retry, async_write
from .tokens import Token

_LOGGER = logging.getLogger(__name__)

# Erlaubte Abweichung beim Zurücklesen der laufenden Uhr (05.00)
CLOCK_TOLERANCE_S = 10


def _seconds_apart(a: bytes, b: bytes) -> int:
    """Abstand zweier Uhrzeiten im Reglerformat (Sek, Min, Std) über Mitternacht hinweg."""
    def secs(t: bytes) -> int:
        return t[2] * 3600 + t[1] * 60 + t[0]

    diff = abs(secs(a) - secs(b)) % 86400
    return min(diff, 86400 - diff)


class ResumatCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Hält die dekodierten Werte als {menu: wert}."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        host: str,
        port: int,
        tokens: list[Token],
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self.tokens = tokens
        # Der Adapter bekommt immer nur eine Verbindung gleichzeitig
        self._lock = asyncio.Lock()

    def _decode_all(self, memory: bytes) -> dict[str, Any]:
        return {token.menu: token.decode(memory) for token in self.tokens}

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            async with self._lock:
                memory = await async_read_memory_retry(self.host, self.port)
        except ResumatProtocolError as err:
            raise UpdateFailed(str(err)) from err
        return self._decode_all(memory)

    async def async_write_value(self, token: Token, value: Any) -> None:
        """Wert schreiben, danach zurücklesen und prüfen (wie im Java-Adapter)."""
        if not token.writable:
            raise HomeAssistantError(f"{token.name} ist nicht beschreibbar")
        raw = token.encode(value)
        if len(raw) > token.length:
            raise HomeAssistantError(f"Wert zu lang für {token.name}")

        _LOGGER.info("Schreibe %s (%s) = %s [%s]", token.menu, token.name, value, raw.hex())
        async with self._lock:
            try:
                await async_write(self.host, self.port, token.start, raw)
            except ResumatProtocolError as err:
                # Antwort fehlerhaft heißt nicht zwingend, dass nicht geschrieben wurde
                _LOGGER.warning("Antwort auf Schreibbefehl fehlerhaft: %s", err)
            await asyncio.sleep(0.5)
            try:
                memory = await async_read_memory_retry(self.host, self.port)
            except ResumatProtocolError as err:
                raise HomeAssistantError(
                    f"{token.name}: Kontrolle nach dem Schreiben fehlgeschlagen ({err})"
                ) from err

        self.async_set_updated_data(self._decode_all(memory))
        actual = memory[token.start : token.start + len(raw)]
        if token.dynamic and token.data_type == "Time":
            # Laufende Uhr: tickt zwischen Schreiben und Zurücklesen weiter
            if _seconds_apart(raw, actual) > CLOCK_TOLERANCE_S:
                raise HomeAssistantError(
                    f"{token.name}: Uhrzeit wurde nicht übernommen "
                    f"(gesendet {raw.hex()}, gelesen {actual.hex()})"
                )
        elif actual != raw:
            raise HomeAssistantError(
                f"{token.name}: Wert wurde nicht übernommen "
                f"(gesendet {raw.hex()}, gelesen {actual.hex()})"
            )
