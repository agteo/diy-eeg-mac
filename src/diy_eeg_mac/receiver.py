# SPDX-License-Identifier: GPL-3.0-or-later
"""Receive a compatible BLE EEG stream and republish it through LSL."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import math

from bleak import BleakClient, BleakScanner
from pylsl import StreamInfo, StreamOutlet

from .protocol import CHANNELS, SAMPLE_RATE_HZ, decode, gaps_before_frames

DEFAULT_NAME = "ESP32_EEG_DATA"
CHARACTERISTIC_UUID = "cba1d466-344c-4be3-ab3f-189f80dd7518"
SAMPLE_RATE = SAMPLE_RATE_HZ


async def discover(name: str, address: str | None, timeout: float):
    if address:
        return await BleakScanner.find_device_by_address(address, timeout=timeout)
    devices = await BleakScanner.discover(timeout=timeout)
    return next((device for device in devices if device.name == name), None)


async def receive(name: str, address: str | None, scan_timeout: float) -> None:
    stream = StreamOutlet(
        StreamInfo("Custom_ESP32_EEG", "EEG", CHANNELS, SAMPLE_RATE, "float32", "diy_eeg_mac")
    )
    samples: asyncio.Queue[bytes] = asyncio.Queue()
    expected_sequence: int | None = None
    dropped = 0

    def on_notification(_: int, payload: bytearray) -> None:
        try:
            decode(bytes(payload))
        except ValueError:
            print(f"Ignoring malformed BLE notification ({len(payload)} bytes).")
        else:
            samples.put_nowait(bytes(payload))

    async def publish() -> None:
        nonlocal expected_sequence, dropped
        while True:
            frames = decode(await samples.get())
            gaps, expected_sequence = gaps_before_frames(
                expected_sequence, tuple(frame.sequence for frame in frames)
            )
            for frame, missing in zip(frames, gaps, strict=True):
                if missing:
                    dropped += missing
                    stream.push_chunk([[math.nan] * CHANNELS for _ in range(missing)])
                    print(f"Detected {missing} missing samples (total: {dropped}).")
                stream.push_sample(frame.microvolts)

    publisher = asyncio.create_task(publish())
    try:
        while True:
            print(f"Scanning for {address or name}…")
            device = await discover(name, address, scan_timeout)
            if device is None:
                print("Not found; retrying in two seconds.")
                await asyncio.sleep(2)
                continue
            disconnected = asyncio.Event()
            print(f"Connecting to {device.name or name} ({device.address})…")
            async with BleakClient(device, disconnected_callback=lambda _: disconnected.set()) as client:
                print("Connected. LSL stream Custom_ESP32_EEG is live; press Ctrl-C to stop.")
                expected_sequence = None
                await client.start_notify(CHARACTERISTIC_UUID, on_notification)
                await disconnected.wait()
                if client.is_connected:
                    await client.stop_notify(CHARACTERISTIC_UUID)
                print("Disconnected.")
    finally:
        publisher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await publisher


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=DEFAULT_NAME, help="advertised BLE name")
    parser.add_argument("--address", help="macOS BLE UUID, to skip name discovery")
    parser.add_argument("--scan-timeout", type=float, default=5.0)
    args = parser.parse_args()
    try:
        asyncio.run(receive(args.name, args.address, args.scan_timeout))
    except KeyboardInterrupt:
        print("\nReceiver stopped.")


if __name__ == "__main__":
    main()
