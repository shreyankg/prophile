from __future__ import annotations

import ast
import math
import unittest
from pathlib import Path

from roast_parser import RoastParseError, parse_alog


ROOT = Path(__file__).resolve().parents[1]


def fixture(*, missing_events=False, extras=True, mismatched=False):
    times = list(range(0, 120, 10))
    et = [180 + index for index in range(len(times))]
    bt = [100 + 0.2 * time for time in times]
    data = {
        "mode": "C",
        "title": "Synthetic roast",
        "weight": [125.0, 105.0, "g"],
        "timex": times,
        "temp1": et + ([999] if mismatched else []),
        "temp2": bt,
        "timeindex": [1, 3, 5, 0, 0, 0, 9, 11] if not missing_events else [1, 0, 0, 0, 0, 0, 0, 11],
        "computed": {
            "CHARGE_BT": 102.0,
            "CHARGE_ET": 181.0,
            "TP_time": 10.0,
            "TP_BT": 104.0,
            "TP_ET": 182.0,
            **({"DRY_time": 20.0, "DRY_BT": 106.0, "DRY_ET": 183.0,
                "FCs_time": 40.0, "FCs_BT": 110.0, "FCs_ET": 185.0,
                "DROP_time": 80.0, "DROP_BT": 118.0, "DROP_ET": 189.0} if not missing_events else {}),
        },
        "devices": ["Main"],
    }
    if extras:
        data.update({
            "devices": ["Main", "+Kaleido Heater/Fan"],
            "extradevices": [141],
            "extratimex": [times],
            "extratemp1": [[75] * len(times)],
            "extratemp2": [[30] * len(times)],
        })
    return repr(data)


class RoastParserTests(unittest.TestCase):
    def test_representative_real_alog(self):
        path = ROOT / "Roast Profiles" / "26-07-26_Baarbara_Washed_AAA_batch_1.alog"
        result = parse_alog(path.read_text(), path.name, "real-id")
        self.assertEqual(result["id"], "real-id")
        self.assertEqual(result["unit"], "C")
        self.assertEqual(result["series"]["et"][0][1], 205.7)
        self.assertEqual(result["series"]["bt"][0][1], 207.6)
        self.assertEqual(result["series"]["heat"][0][1], 50.0)
        self.assertEqual(result["series"]["air"][0][1], 0.0)
        self.assertEqual(result["weights"], {"green": 125.0, "final": 105.0, "lossPercent": 16.0, "unit": "g"})
        self.assertEqual(result["series"]["bt"][0][0], 0.0)
        events = {event["key"]: event for event in result["events"]}
        self.assertEqual(events["charge"]["bt"], 207.6)
        self.assertEqual(events["drop"]["bt"], 187.7)
        self.assertLessEqual(result["series"]["bt"][-1][0], 364.5)

    def test_phase_calculations_and_filename_display(self):
        result = parse_alog(fixture(), "my_test_profile.alog")
        self.assertEqual(result["displayName"], "my test profile")
        self.assertEqual(result["phases"]["total"], 80.0)
        self.assertEqual(result["phases"]["drying"], {"seconds": 20.0, "percent": 25.0})
        self.assertEqual(result["phases"]["browning"], {"seconds": 20.0, "percent": 25.0})
        self.assertEqual(result["phases"]["development"], {"seconds": 40.0, "percent": 50.0})
        self.assertEqual(result["weights"], {"green": 125.0, "final": 105.0, "lossPercent": 16.0, "unit": "g"})

    def test_ror_for_linear_temperature(self):
        result = parse_alog(fixture(), "linear.alog")
        finite_values = [value for _, value in result["series"]["ror"] if value is not None]
        self.assertTrue(finite_values)
        for value in finite_values:
            self.assertTrue(math.isfinite(value))
            self.assertAlmostEqual(value, 12.0, places=5)

    def test_missing_events_remain_chartable(self):
        result = parse_alog(fixture(missing_events=True), "missing.alog")
        self.assertIsNone(result["phases"]["total"])
        self.assertIsNone(result["phases"]["drying"]["seconds"])
        self.assertNotIn("drop", {event["key"] for event in result["events"]})
        self.assertGreater(len(result["series"]["bt"]), 0)
        self.assertIn("Drop event is missing; curves continue to the recording end.", result["warnings"])

    def test_mismatched_arrays_are_clipped_and_optional_channels_warn(self):
        result = parse_alog(fixture(extras=False, mismatched=True), "mismatch.alog")
        self.assertEqual(len(result["series"]["bt"]), 9)
        self.assertEqual(len(result["series"]["et"]), 9)
        self.assertEqual(result["series"]["heat"], [])
        self.assertIn("Heater and air channels were not found.", result["warnings"])

    def test_fahrenheit_is_converted(self):
        data = ast.literal_eval(fixture())
        data["mode"] = "F"
        data["computed"]["CHARGE_BT"] = 212.0
        result = parse_alog(repr(data), "fahrenheit.alog")
        self.assertAlmostEqual(next(e for e in result["events"] if e["key"] == "charge")["bt"], 100.0)
        self.assertEqual(result["unit"], "C")

    def test_rejects_executable_and_malformed_input(self):
        with self.assertRaises(RoastParseError):
            parse_alog("__import__('os').system('echo unsafe')", "unsafe.alog")
        with self.assertRaises(RoastParseError):
            parse_alog("[]", "list.alog")
        with self.assertRaises(RoastParseError):
            parse_alog(fixture(), "wrong.txt")


if __name__ == "__main__":
    unittest.main()
