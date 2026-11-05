import unittest

from diy_eeg_mac.protocol import (
    ADC_TO_MICROVOLTS,
    EXPECTED_NOTIFICATION_INTERVAL_S,
    NOTIFICATION_BYTES,
    arrival_interval_s,
    decode,
    gaps_before_frames,
    missing_samples,
)


class ProtocolTests(unittest.TestCase):
    def test_decode_preserves_signed_values_and_sequences(self) -> None:
        payload = bytearray(NOTIFICATION_BYTES)
        payload[0] = 254
        payload[4:7] = b"\x00\x00\x03"
        payload[7:10] = b"\xff\xff\xfd"
        payload[28] = 255

        frames = decode(bytes(payload))

        self.assertEqual(len(frames), 8)
        self.assertEqual(frames[0].sequence, 254)
        self.assertEqual(frames[1].sequence, 255)
        self.assertEqual(frames[0].microvolts[:2], (3 * ADC_TO_MICROVOLTS, -3 * ADC_TO_MICROVOLTS))

    def test_decode_rejects_incomplete_notification(self) -> None:
        with self.assertRaisesRegex(ValueError, "224"):
            decode(b"incomplete")

    def test_sequence_gap_counts_missing_samples(self) -> None:
        self.assertEqual(missing_samples(4, 7), 3)
        self.assertEqual(EXPECTED_NOTIFICATION_INTERVAL_S, 0.016)

        _, expected = gaps_before_frames(None, tuple(range(8)))
        gaps, _ = gaps_before_frames(expected, tuple(range(16, 24)))

        self.assertEqual(gaps, (8, 0, 0, 0, 0, 0, 0, 0))
        self.assertAlmostEqual(
            arrival_interval_s(1.0, 1.0 + EXPECTED_NOTIFICATION_INTERVAL_S),
            EXPECTED_NOTIFICATION_INTERVAL_S,
        )

    def test_late_arrival_with_continuous_sequence_is_not_missing_data(self) -> None:
        _, expected = gaps_before_frames(None, tuple(range(248, 256)))
        gaps, expected = gaps_before_frames(expected, tuple(range(8)))

        self.assertEqual(gaps, (0, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(expected, 8)
        self.assertGreater(arrival_interval_s(2.0, 2.080), EXPECTED_NOTIFICATION_INTERVAL_S)

    def test_sequence_gap_of_exactly_256_samples_is_invisible(self) -> None:
        self.assertEqual(missing_samples(0, 0), 0)
