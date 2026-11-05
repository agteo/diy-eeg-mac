import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from diy_eeg_mac.alpha import channel_metrics, daily_phases
from diy_eeg_mac.session import append_index, dump_session, index_row, prompt_session, session_document


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


class SessionLogTests(unittest.TestCase):
    def test_prompt_decline_records_nothing(self) -> None:
        with self.assertRaises(SystemExit):
            prompt_session(
                "none",
                _answers("", "1", "8", "0", "", "", "1", "fresh", "n", "n"),
            )

    def test_yaml_and_index_round_trip(self) -> None:
        context = prompt_session(
            "serial7",
            _answers("", "1.5", "6.5", "80", "40", "", "coffee-1", "2", "fresh", "", "blinked once"),
        )
        self.assertEqual(context["task"], "serial7")
        self.assertEqual(context["caffeine_mg"], 80)
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


if __name__ == "__main__":
    unittest.main()
