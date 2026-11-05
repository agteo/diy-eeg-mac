# SPDX-License-Identifier: GPL-3.0-or-later
"""Binary protocol helpers for the supported eight-channel BLE EEG stream."""

from __future__ import annotations

from dataclasses import dataclass

CHANNELS = 8
FRAMES_PER_NOTIFICATION = 8
FRAME_BYTES = 28
NOTIFICATION_BYTES = FRAME_BYTES * FRAMES_PER_NOTIFICATION
ADC_TO_MICROVOLTS = 4_500_000.0 / (24 * 8_388_608)
SEQUENCE_MODULUS = 256
SAMPLE_RATE_HZ = 500.0
EXPECTED_NOTIFICATION_INTERVAL_S = FRAMES_PER_NOTIFICATION / SAMPLE_RATE_HZ


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


def missing_samples(expected_sequence: int, sequence: int) -> int:
    """Return how many frame numbers were skipped before `sequence`.

    Zero means `sequence` is the next expected frame. The counter wraps at 256,
    so a hole of exactly 256 frames looks the same as no hole.
    """
    return (sequence - expected_sequence) % SEQUENCE_MODULUS


def gaps_before_frames(
    expected_sequence: int | None, sequences: tuple[int, ...]
) -> tuple[tuple[int, ...], int | None]:
    """Return missing-sample counts before each frame, and the next expected number."""
    gaps: list[int] = []
    expected = expected_sequence
    for sequence in sequences:
        gaps.append(0 if expected is None else missing_samples(expected, sequence))
        expected = (sequence + 1) % SEQUENCE_MODULUS
    return tuple(gaps), expected


def arrival_interval_s(previous_arrival_s: float | None, arrival_s: float) -> float | None:
    """Seconds since the previous notification reached the host.

    This is independent of the frame sequence. A late or bunched notification
    can still contain every sample.
    """
    if previous_arrival_s is None:
        return None
    return arrival_s - previous_arrival_s
