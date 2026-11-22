"""Direkte TCP-Kommunikation mit dem Resümat-Adapter (Port 6001).

Python-Portierung von de.gz.wpadapter.WpAdapter:

Lesen:     10 02 | 01 15 <start:2> <len:2> | 10 03 | CRC16
Antwort:   FF 10 02 | 00 17 <daten...> | 10 03 | CRC16 | FF
Schreiben: 10 02 | 01 13 <start:2> <wert...> | 10 03 | CRC16
Antwort:   FF 10 02 | 00 11 ... | 10 03 | CRC16 | FF

- Byte 0x10 im Nutzdatenteil wird als 10 10 gesendet (DLE-Stuffing).
- CRC: CRC-16 Poly 0x8005, Init 0, nicht reflektiert (CRC-16/BUYPASS),
  berechnet über den gestopften Nutzdatenteil.
"""

from __future__ import annotations

import asyncio

DLE = 0x10
STX = 0x02
ETX = 0x03

CMD_READ = bytes.fromhex("0115")
ANSWER_READ = bytes.fromhex("0017")
CMD_WRITE = bytes.fromhex("0113")
ANSWER_WRITE = bytes.fromhex("0011")

# Der Adapter liefert den gesamten Speicher in einem Rutsch (wie im Java-Code)
READ_START = 0x0000
READ_LEN = 0x0176

TIMEOUT = 10


class ResumatProtocolError(Exception):
    """Kommunikations- oder Prüfsummenfehler."""


def crc16(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x8005) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def stuff(data: bytes) -> bytes:
    return data.replace(b"\x10", b"\x10\x10")


def _frame(message: bytes) -> bytes:
    payload = stuff(message)
    crc = crc16(payload)
    # Java: Long.toHexString(crc), auf gerade Länge aufgefüllt
    crc_bytes = crc.to_bytes(2 if crc > 0xFF else 1, "big")
    return bytes([DLE, STX]) + payload + bytes([DLE, ETX]) + crc_bytes


def build_read_request(start: int = READ_START, length: int = READ_LEN) -> bytes:
    return _frame(CMD_READ + start.to_bytes(2, "big") + length.to_bytes(2, "big"))


def build_write_request(start: int, value: bytes) -> bytes:
    return _frame(CMD_WRITE + start.to_bytes(2, "big") + value)


async def _read_frame(reader: asyncio.StreamReader, answer: bytes) -> bytes:
    """Liest eine Antwort und gibt die entstopften Daten (ohne Antwort-Kennung) zurück."""
    # Auf Frame-Start 10 02 warten (davor kommt üblicherweise FF)
    prev = None
    while True:
        byte = (await reader.readexactly(1))[0]
        if prev == DLE and byte == STX:
            break
        prev = byte

    raw = bytearray()       # gestopft, für CRC
    data = bytearray()      # entstopft
    while True:
        byte = (await reader.readexactly(1))[0]
        if byte == DLE:
            nxt = (await reader.readexactly(1))[0]
            if nxt == ETX:
                break
            if nxt != DLE:
                raise ResumatProtocolError(f"Ungültige Escape-Sequenz 10 {nxt:02x}")
            raw += b"\x10\x10"
            data.append(DLE)
        else:
            raw.append(byte)
            data.append(byte)

    crc_bytes = await reader.readexactly(2)
    if crc16(bytes(raw) + crc_bytes) != 0:
        raise ResumatProtocolError("CRC-Fehler")
    if not data.startswith(answer):
        raise ResumatProtocolError(f"Unerwartete Antwort {bytes(data[:2]).hex()}")
    return bytes(data[len(answer):])


async def _transact(host: str, port: int, request: bytes, answer: bytes) -> bytes:
    """Eine Anfrage senden und die Antwort lesen (eigene Verbindung je Anfrage)."""
    try:
        async with asyncio.timeout(TIMEOUT):
            reader, writer = await asyncio.open_connection(host, port)
            try:
                writer.write(request)
                await writer.drain()
                return await _read_frame(reader, answer)
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
    except (OSError, TimeoutError, asyncio.IncompleteReadError) as err:
        raise ResumatProtocolError(f"Verbindung zu {host}:{port} fehlgeschlagen: {err}") from err


async def async_read_memory(host: str, port: int) -> bytes:
    """Liest den kompletten Datenblock (READ_LEN Bytes) vom Adapter."""
    data = await _transact(host, port, build_read_request(), ANSWER_READ)
    if len(data) < READ_LEN:
        raise ResumatProtocolError(f"Zu wenig Daten: {len(data)} statt {READ_LEN} Bytes")
    return data


async def async_read_memory_retry(host: str, port: int) -> bytes:
    """Wie im Java-Code: bei Fehler nach 0,5 s noch einmal versuchen."""
    try:
        return await async_read_memory(host, port)
    except ResumatProtocolError:
        await asyncio.sleep(0.5)
        return await async_read_memory(host, port)


async def async_write(host: str, port: int, start: int, value: bytes) -> None:
    """Schreibt Rohbytes ab Adresse start. Ohne Wiederholung (Schreiben nie doppelt)."""
    await _transact(host, port, build_write_request(start, value), ANSWER_WRITE)
