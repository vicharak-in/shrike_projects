"""
packet_parser.py

Converts raw serial text lines from the RP2040 into structured Packet dicts.
All protocol logic lives here — the GUI never inspects raw strings.

Packet schema:
{
    "timestamp": str,       # HH:MM:SS
    "protocol":  str,       # "I2C" | "UART" | "SYSTEM" | "UNKNOWN"
    "event":     str,       # "START" | "ADDR" | "DATA" | "STOP" |
                            # "MESSAGE" | "SEPARATOR" | ...
    "details":   str,       # human-readable detail string
}

A "SEPARATOR" event signals the GUI to render a visual transaction divider.
"""

from datetime import datetime


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _make_packet(protocol: str, event: str, details: str) -> dict:
    return {
        "timestamp": _now(),
        "protocol":  protocol,
        "event":     event,
        "details":   details,
    }


def _separator(protocol: str) -> dict:
    return _make_packet(protocol, "SEPARATOR", "Transaction Complete")


class PacketParser:
    """
    Stateful parser. Feed it one line at a time via parse_line().

    Returns a list of 0, 1, or 2 packets per line.
    A UART MESSAGE always appends a SEPARATOR after it.
    An I2C STOP always appends a SEPARATOR after it.
    """

    def __init__(self):
        self._active_protocol = "UNKNOWN"

    def parse_line(self, line: str) -> list:
        """
        Returns a list of Packet dicts (may be empty, or contain 1-2 packets).
        The GUI iterates the list and ingests each packet in order.
        """
        if not line:
            return []

        # 1. Protocol announcement
        if line.startswith("PROTOCOL DETECTED"):
            parts = line.split(":")
            if len(parts) >= 2:
                self._active_protocol = parts[-1].strip().upper()
            else:
                self._active_protocol = "UNKNOWN"
            return [_make_packet("", "", line)]

        # 2. Dynamic protocol updates based on unique prefixes
        if any(line.startswith(p) for p in ("MOSI", "MISO", "BYTES")):
            self._active_protocol = "SPI"
        elif any(line.startswith(p) for p in ("ADDR", "DATA")):
            if self._active_protocol != "I2C SLAVE":
                self._active_protocol = "I2C"
        elif line.startswith("MESSAGE"):
            if self._active_protocol != "I2C SLAVE":
                self._active_protocol = "UART"

        proto = self._active_protocol

        # 3. Parse allowed protocol events
        # MESSAGE event (used by UART, I2C SLAVE, etc.)
        if line.startswith("MESSAGE"):
            detail = line[len("MESSAGE"):].strip().lstrip(":").strip()
            return [
                _make_packet(proto, "MESSAGE", detail),
                _separator(proto),
            ]

        # SPI events
        elif proto == "SPI":
            if line == "START":
                return [_make_packet(proto, "START", "")]
            if line == "STOP":
                return [
                    _make_packet(proto, "STOP", ""),
                    _separator(proto),
                ]
            if line.startswith("BYTES"):
                detail = line[len("BYTES"):].strip().lstrip(":").strip()
                return [_make_packet(proto, "BYTES", detail)]
            if line.startswith("MOSI"):
                detail = line[len("MOSI"):].strip().lstrip(":").strip()
                return [_make_packet(proto, "MOSI", detail)]
            if line.startswith("MISO"):
                detail = line[len("MISO"):].strip().lstrip(":").strip()
                return [_make_packet(proto, "MISO", detail)]

        # I2C/I2C SLAVE events
        elif proto == "I2C" or proto == "I2C SLAVE":
            if line == "START":
                return [_make_packet(proto, "START", "Bus Start")]
            if line == "STOP":
                return [
                    _make_packet(proto, "STOP", "Bus Stop"),
                    _separator(proto),
                ]
            if line.startswith("ADDR"):
                detail = line[len("ADDR"):].strip().lstrip(":").strip()
                return [_make_packet(proto, "ADDR", detail)]
            if line.startswith("DATA"):
                detail = line[len("DATA"):].strip().lstrip(":").strip()
                return [_make_packet(proto, "DATA", detail)]

        # If protocol is UNKNOWN, still allow START/STOP so we don't drop them
        else:
            if line == "START":
                return [_make_packet(proto, "START", "")]
            if line == "STOP":
                return [_make_packet(proto, "STOP", "")]

        # Anything else (including raw bytes, exceptions, boot messages, REPL lines) is silently filtered out
        return []