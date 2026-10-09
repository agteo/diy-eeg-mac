import unittest

from diy_eeg_mac.protocol import ADC_TO_MICROVOLTS, NOTIFICATION_BYTES, decode


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
