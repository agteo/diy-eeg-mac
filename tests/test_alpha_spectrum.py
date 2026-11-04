import unittest

import numpy as np

from diy_eeg_mac.alpha_spectrum import alpha_peak, phase_spectra


class AlphaSpectrumTests(unittest.TestCase):
    def test_closed_phase_peaks_in_alpha_band(self) -> None:
        rate = 500.0
        stamps = np.arange(0, 60, 1 / rate)
        rng = np.random.default_rng(0)
        signal = rng.normal(0, 1, stamps.size)
        closed = (stamps >= 20) & (stamps < 40)
        signal[closed] += 5 * np.sin(2 * np.pi * 10 * stamps[closed])
        windows = [("Eyes_Open_1", 0.0, 20.0), ("Eyes_Closed", 20.0, 40.0), ("Eyes_Open_2", 40.0, 60.0)]

        freqs, spectra = phase_spectra(signal, stamps, windows, rate)

        self.assertEqual(set(spectra), {"Eyes_Open_1", "Eyes_Closed", "Eyes_Open_2"})
        self.assertAlmostEqual(alpha_peak(freqs, spectra["Eyes_Closed"]), 10.0, delta=0.5)
        alpha = (freqs >= 8) & (freqs <= 12)
        self.assertGreater(spectra["Eyes_Closed"][alpha].mean(), 10 * spectra["Eyes_Open_1"][alpha].mean())

    def test_peak_is_nan_when_band_missing(self) -> None:
        self.assertTrue(np.isnan(alpha_peak(np.array([1.0, 2.0]), np.array([1.0, 2.0]))))


if __name__ == "__main__":
    unittest.main()
