"""Parameterdefinitionen (menu_addresses.csv) und Dekodierung der Rohdaten.

Portierung von WPUtil.readAddressFile() und DataToken.getFormattedValue().
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import struct
from typing import Any

CSV_FILE = Path(__file__).parent / "menu_addresses.csv"


@dataclass(frozen=True, slots=True)
class Token:
    menu: str
    name: str
    dynamic: bool
    writable: bool
    unit: str
    start: int
    length: int
    data_type: str

    def decode(self, memory: bytes) -> Any:
        raw = memory[self.start : self.start + self.length]
        if len(raw) < self.length:
            return None
        dt = self.data_type
        if dt == "Float":
            value = struct.unpack("<f", raw[:4])[0]
            return None if math.isnan(value) or math.isinf(value) else round(value, 2)
        if dt == "Integer":
            return int.from_bytes(raw, "big")
        if dt == "Boolean":
            return int.from_bytes(raw, "big") != 0
        if dt == "Binary":
            return format(int.from_bytes(raw, "big"), "08b")
        if dt == "Date":
            return f"{raw[0]:02d}.{raw[1]:02d}.{raw[2]:02d}"
        if dt == "Time":
            return f"{raw[2]:02d}:{raw[1]:02d}:{raw[0]:02d}"
        if dt == "Text":
            return f"{int.from_bytes(raw, 'big'):02d}"
        # IntegerString und Unbekanntes: Hex wie im Java-Code
        return raw.hex()

    def encode(self, value: Any) -> bytes:
        """Wert in Rohbytes für einen Schreibbefehl wandeln."""
        dt = self.data_type
        if dt == "Float":
            return struct.pack("<f", float(value))
        if dt == "Boolean":
            return (1 if value else 0).to_bytes(self.length, "big")
        if dt == "Integer":
            return int(value).to_bytes(self.length, "big")
        if dt == "Time":
            # value: datetime.time -> Sekunden, Minuten, Stunden (wie decode)
            return bytes([value.second, value.minute, value.hour])
        raise ValueError(f"Schreiben für Datentyp {dt} nicht unterstützt")


def load_tokens() -> list[Token]:
    """CSV lesen (blockierend, im Executor aufrufen)."""
    tokens: list[Token] = []
    with CSV_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(";")]
            if len(parts) < 10:
                continue
            tokens.append(
                Token(
                    menu=parts[0],
                    name=parts[1],
                    dynamic=parts[2] == "dynamic",
                    writable=parts[3].lower() == "true",
                    unit=parts[4],
                    start=int(parts[5] + parts[6], 16),
                    length=int(parts[7] + parts[8], 16),
                    data_type=parts[9],
                )
            )
    return tokens
