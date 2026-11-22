"""DataUpdateCoordinator: liest den Adapter zyklisch aus."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .protocol import ResumatProtocolError, async_read_memory_retry
from .tokens import Token

_LOGGER = logging.getLogger(__name__)


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

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            memory = await async_read_memory_retry(self.host, self.port)
        except ResumatProtocolError as err:
            raise UpdateFailed(str(err)) from err
        return {token.menu: token.decode(memory) for token in self.tokens}
