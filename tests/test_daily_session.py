import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from diy_eeg_mac.alpha import (
    channel_metrics,
    daily_phases,
    format_channel_summary,
    fz_focus_scores,
    fz_theta_ratio,
    mains_notch,
)
from diy_eeg_mac.report import EXAMPLE_NOTICE, example_rows, render_report
from diy_eeg_mac.session import append_index, dump_session, index_row, prompt_context, read_index, session_document


def _answers(*lines: str):
    pending = iter(lines)

    def answer(prompt: str) -> str:
        try:
            return next(pending)
        except StopIteration as error:
            raise AssertionError(f"unexpected prompt: {prompt}") from error

    return answer


class DailyPhaseTests(unittest.TestCase):
    def test_serial7_adds_two_blocks_and_keeps_berger_cues(self) -> None:
        markers = [phase.marker for phase in daily_phases(60, 5, 487)]
        self.assertEqual(
            markers,
            ["Settle", "Eyes_Open_1", "Eyes_Closed", "Eyes_Open_2", "Task_Serial7", "Eyes_Open_3"],
        )
        cues = {phase.marker: phase.cue_count for phase in daily_phases(60, 5, 487)}
        self.assertEqual(cues["Settle"], 0)
        self.assertEqual(cues["Eyes_Closed"], 2)
        self.assertEqual(cues["Task_Serial7"], 3)
        self.assertEqual(daily_phases(60, 5, 487)[-1].duration, 30)
        self.assertIsNone(next((phase for phase in daily_phases(60, 5, None) if phase.marker == "Task_Serial7"), None))


class ScoreTests(unittest.TestCase):
    def test_ratio_ignores_the_cue_and_the_recovery_block(self) -> None:
        rate = 100.0
        stamps = np.arange(0, 100, 1 / rate)
        signal = np.zeros_like(stamps)

        def fill(start: float, end: float, amplitude: float) -> None:
            mask = (stamps >= start) & (stamps < end)
            signal[mask] = amplitude * np.sin(2 * np.pi * 10 * stamps[mask])

        fill(5, 25, 10)
        fill(25, 27, 200)
        fill(27, 45, 40)
        fill(45, 65, 10)
        fill(65, 85, 5)
        fill(85, 100, 100)
        markers = [
            (0.0, "Settle_Start"),
            (5.0, "Settle_End"),
            (5.0, "Eyes_Open_1_Start"),
            (25.0, "Eyes_Open_1_End"),
            (25.0, "Eyes_Closed_Start"),
            (45.0, "Eyes_Closed_End"),
            (45.0, "Eyes_Open_2_Start"),
            (65.0, "Eyes_Open_2_End"),
            (65.0, "Task_Serial7_Start"),
            (85.0, "Task_Serial7_End"),
            (85.0, "Eyes_Open_3_Start"),
            (100.0, "Eyes_Open_3_End"),
        ]

        scored = channel_metrics(signal, stamps, markers, rate, skip=2)
        included = channel_metrics(signal, stamps, markers, rate, skip=0)
        self.assertIsNotNone(scored)
        self.assertAlmostEqual(scored["ratio"], 4.0, delta=0.4)
        self.assertAlmostEqual(scored["task_ratio"], 0.5, delta=0.15)
        self.assertAlmostEqual(scored["peak_hz"], 10.0, delta=0.5)
        self.assertGreater(included["ratio"], scored["ratio"])

    def test_summary_names_fz_on_channel_4(self) -> None:
        rate = 100.0
        stamps = np.arange(0, 30, 1 / rate)
        eeg = np.zeros((stamps.size, 5))
        eeg[:, 4] = 10 * np.sin(2 * np.pi * 10 * stamps)
        markers = [
            (0.0, "Eyes_Open_1_Start"),
            (10.0, "Eyes_Open_1_End"),
            (10.0, "Eyes_Closed_Start"),
            (20.0, "Eyes_Closed_End"),
            (20.0, "Eyes_Open_2_Start"),
            (30.0, "Eyes_Open_2_End"),
        ]
        text = format_channel_summary(eeg, stamps, markers)
        self.assertIn("channel 4 (Fz)", text)
        self.assertIn("channel 0 (O1): input not moving", text)


class SessionLogTests(unittest.TestCase):
    def test_yaml_and_index_round_trip(self) -> None:
        context = prompt_context(
            _answers("singapore", "", "1.5", "6.5", "80", "40", "", "coffee-1", "2", "fresh", "blinked once"),
        )
        context["qc"] = "pass"
        self.assertEqual(context["caffeine_mg"], 80)
        self.assertEqual(context["location"], "singapore")
        self.assertEqual(context["mains_hz"], 50)
        document = session_document(
            context,
            started="2026-11-06T07:40:00+08:00",
            ended="2026-11-06T07:46:00+08:00",
            protocol="berger+serial7",
            phase_s=60,
            settle_s=5,
            score_skip_s=2,
            xdf_name="alpha-20261106-074000.xdf",
            serial7_seed=487,
            metrics={"O1": {"ratio": 1.8, "peak_hz": 10.2, "task_ratio": 0.7, "rms": {}}},
        )
        text = dump_session(document)
        self.assertIn('started: "2026-11-06T07:40:00+08:00"', text)
        self.assertIn("protocol: berger+serial7", text)
        self.assertIn("minutes_since_exercise: null", text)
        self.assertIn("  O1: 1.8", text)
        self.assertIn("  4: Fz", text)
        self.assertIn("location: singapore", text)
        self.assertIn("mains_hz: 50", text)

        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.csv"
            row = index_row(document)
            append_index(index, row)
            append_index(index, row)
            with index.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["xdf"], "alpha-20261106-074000.xdf")
        self.assertEqual(rows[0]["ratio_o1"], "1.8000")
        self.assertEqual(rows[0]["pair_id"], "coffee-1")
        self.assertEqual(rows[0]["anomalies"], "blinked once")
        self.assertEqual(rows[0]["fz_theta_ratio"], "")
        self.assertEqual(rows[0]["location"], "singapore")
        self.assertEqual(rows[0]["mains_hz"], "50")

    def test_united_states_selects_a_sixty_hertz_notch(self) -> None:
        context = prompt_context(
            _answers("united-states", "", "1", "7", "0", "", "", "1", "fresh", ""),
        )
        self.assertEqual(context["location"], "united-states")
        self.assertEqual(context["mains_hz"], 60)

    def test_old_index_gains_the_focus_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.csv"
            index.write_text(
                "started,protocol,qc,xdf,phase_s,settle_s,hours_since_wake,sleep_hours,caffeine_mg,"
                "minutes_since_caffeine,minutes_since_exercise,pair_id,drowsy_1_to_5,paste,"
                "montage_confirmed,serial7_seed,ratio_o1,ratio_oz,ratio_o2,peak_hz_o1,peak_hz_oz,"
                "peak_hz_o2,task_ratio_o1,anomalies\n"
                "2026-11-06T16:09:16+08:00,berger,pass,alpha.xdf,60,5,8,5,100,120,,,2,fresh,true,,2.5,2.5,2.5,9.3,9.3,9.3,,\n"
            )
            rows = read_index(index)
            self.assertEqual(rows[0]["fz_theta_ratio"], "")
            self.assertIn("fz_theta_ratio", index.read_text().splitlines()[0])


class FocusScoreTests(unittest.TestCase):
    def test_serial7_theta_ratio_uses_fz(self) -> None:
        rate = 100.0
        stamps = np.arange(0, 40, 1 / rate)
        eeg = np.zeros((stamps.size, 5))

        def fill(start: float, end: float, amplitude: float) -> None:
            mask = (stamps >= start) & (stamps < end)
            eeg[mask, 4] = amplitude * np.sin(2 * np.pi * 6 * stamps[mask])

        fill(0, 10, 10)
        fill(10, 20, 10)
        fill(20, 30, 10)
        fill(30, 40, 20)
        markers = [
            (0.0, "Eyes_Open_1_Start"),
            (10.0, "Eyes_Open_1_End"),
            (10.0, "Eyes_Closed_Start"),
            (20.0, "Eyes_Closed_End"),
            (20.0, "Eyes_Open_2_Start"),
            (30.0, "Eyes_Open_2_End"),
            (30.0, "Task_Serial7_Start"),
            (40.0, "Task_Serial7_End"),
        ]
        self.assertAlmostEqual(fz_theta_ratio(eeg, stamps, markers, skip=0), 2.0, delta=0.15)

    def test_engagement_falls_when_theta_rises(self) -> None:
        rate = 100.0
        stamps = np.arange(0, 40, 1 / rate)
        eeg = np.zeros((stamps.size, 5))

        def tone(start: float, end: float, frequency: float, amplitude: float) -> None:
            mask = (stamps >= start) & (stamps < end)
            eeg[mask, 4] += amplitude * np.sin(2 * np.pi * frequency * stamps[mask])

        for start in (0.0, 10.0, 20.0):
            tone(start, start + 10, 6, 10)
            tone(start, start + 10, 10, 10)
            tone(start, start + 10, 20, 10)
        tone(30, 40, 6, 20)
        tone(30, 40, 10, 10)
        tone(30, 40, 20, 5)
        markers = [
            (0.0, "Eyes_Open_1_Start"),
            (10.0, "Eyes_Open_1_End"),
            (10.0, "Eyes_Closed_Start"),
            (20.0, "Eyes_Closed_End"),
            (20.0, "Eyes_Open_2_Start"),
            (30.0, "Eyes_Open_2_End"),
            (30.0, "Task_Serial7_Start"),
            (40.0, "Task_Serial7_End"),
        ]
        scores = fz_focus_scores(eeg, stamps, markers, skip=0)
        self.assertIsNotNone(scores)
        assert scores is not None
        self.assertLess(scores["engagement_task"], scores["engagement_open"])
        self.assertGreater(scores["tbr_task"], scores["tbr_open"])
        self.assertAlmostEqual(scores["engagement_open"], 0.5, delta=0.15)
        self.assertGreater(scores["tbr_task"], 4)


class MainsNotchTests(unittest.TestCase):
    def test_fifty_hertz_drops_and_alpha_stays(self) -> None:
        from scipy.signal import butter, filtfilt

        rate = 500.0
        stamps = np.arange(0, 4, 1 / rate)
        clean = np.sin(2 * np.pi * 10 * stamps)
        noisy = clean + 20 * np.sin(2 * np.pi * 50 * stamps)
        filtered = mains_notch(noisy, rate)

        def band_rms(signal: np.ndarray, low: float, high: float) -> float:
            narrowed = filtfilt(*butter(4, [low / (rate / 2), high / (rate / 2)], btype="band"), signal)
            return float(np.sqrt(np.mean(narrowed**2)))

        self.assertLess(band_rms(filtered, 48, 52), band_rms(noisy, 48, 52) * 0.1)
        self.assertAlmostEqual(band_rms(filtered, 8, 12), band_rms(clean, 8, 12), delta=0.05)

    def test_sixty_hertz_notch_drops_sixty_hertz(self) -> None:
        from scipy.signal import butter, filtfilt

        rate = 500.0
        stamps = np.arange(0, 4, 1 / rate)
        clean = np.sin(2 * np.pi * 10 * stamps)
        noisy = clean + 20 * np.sin(2 * np.pi * 60 * stamps)
        filtered = mains_notch(noisy, rate, 60)

        def band_rms(signal: np.ndarray, low: float, high: float) -> float:
            narrowed = filtfilt(*butter(4, [low / (rate / 2), high / (rate / 2)], btype="band"), signal)
            return float(np.sqrt(np.mean(narrowed**2)))

        self.assertLess(band_rms(filtered, 58, 62), band_rms(noisy, 58, 62) * 0.1)
        self.assertAlmostEqual(band_rms(filtered, 8, 12), band_rms(clean, 8, 12), delta=0.05)


class ReportTests(unittest.TestCase):
    def test_page_charts_passing_runs_only(self) -> None:
        html = render_report(
            [
                {
                    "started": "2026-11-06T16:09:16+08:00",
                    "protocol": "berger",
                    "qc": "pass",
                    "phase_s": "60",
                    "ratio_o1": "2.49",
                    "fz_theta_ratio": "",
                    "anomalies": "",
                },
                {
                    "started": "2026-11-06T16:18:45+08:00",
                    "protocol": "berger+serial7",
                    "qc": "pass",
                    "phase_s": "60",
                    "ratio_o1": "2.10",
                    "fz_theta_ratio": "1.68",
                    "anomalies": "",
                },
                {
                    "started": "2026-11-07T09:00:00+08:00",
                    "protocol": "berger",
                    "qc": "fail",
                    "phase_s": "60",
                    "ratio_o1": "9.99",
                    "fz_theta_ratio": "",
                    "anomalies": "",
                },
            ]
        )
        self.assertIn("O1 eyes closed", html)
        self.assertIn("Fz focus", html)
        self.assertIn("Fz engagement", html)
        self.assertIn("Fz theta/beta", html)
        self.assertIn("Engagement index", html)
        self.assertIn("not a separate focus grade", html)
        self.assertIn("Waveform", html)
        self.assertIn("Spectrum", html)
        self.assertIn("1.68", html)
        self.assertIn('session.qc === "pass"', html)
        self.assertIn("stays out of the trend", html)
        self.assertIn("What the words mean", html)
        self.assertIn("Berger effect", html)
        self.assertIn("What this view is showing", html)

    def test_example_page_shows_scores_without_a_waveform(self) -> None:
        html = render_report(example_rows(), notice=EXAMPLE_NOTICE)
        self.assertIn("Example only", html)
        self.assertIn("Fz engagement", html)
        self.assertIn("Fz theta/beta", html)
        self.assertIn("1.45", html)
        self.assertIn("0.41", html)
        self.assertIn('"traces":null', html)
        self.assertNotIn(".xdf", html)
        self.assertIn("index numbers only", html)


if __name__ == "__main__":
    unittest.main()
