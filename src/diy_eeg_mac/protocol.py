# SPDX-License-Identifier: GPL-3.0-or-later
"""Binary protocol helpers for the supported eight-channel BLE EEG stream."""

from __future__ import annotations

from dataclasses import dataclass

CHANNELS = 8
FRAMES_PER_NOTIFICATION = 8
FRAME_BYTES = 28
NOTIFICATION_BYTES = FRAME_BYTES * FRAMES_PER_NOTIFICATION
ADC_TO_MICROVOLTS = 4_500_000.0 / (24 * 8_388_608)


@dataclass(frozen=True)
class Frame:
    sequence: int
    status: int
    microvolts: tuple[float, ...]


def _signed_24(raw: bytes) -> int:
    value = int.from_bytes(raw, byteorder="big", signed=False)
    return value - (1 << 24) if value & (1 << 23) else value


def decode(data: bytes) -> tuple[Frame, ...]:
    """Decode one fixed-size notification into ordered EEG frames."""
    if len(data) != NOTIFICATION_BYTES:
        raise ValueError(f"Expected {NOTIFICATION_BYTES} bytes, got {len(data)}")

    result: list[Frame] = []
    for offset in range(0, NOTIFICATION_BYTES, FRAME_BYTES):
        raw = data[offset : offset + FRAME_BYTES]
        channels = tuple(
            _signed_24(raw[channel_offset : channel_offset + 3]) * ADC_TO_MICROVOLTS
            for channel_offset in range(4, 4 + CHANNELS * 3, 3)
        )
        result.append(
            Frame(
                sequence=raw[0],
                status=int.from_bytes(raw[1:4], byteorder="big"),
                microvolts=channels,
            )
        )
    return tuple(result)
