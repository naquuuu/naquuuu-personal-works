"""Regression tests for the bilingual relay evaluation set."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import wa_eval


class RelayEvalTests(unittest.TestCase):
    def test_every_recorded_failure_is_caught_and_every_good_reply_passes(self):
        for case_id, caught, clean in wa_eval.run_cases():
            self.assertTrue(caught, f"recorded failure not caught: {case_id}")
            self.assertTrue(clean, f"good reply incorrectly flagged: {case_id}")

    def test_runner_reports_failure_when_a_case_stops_catching(self):
        # If a rule regresses, the recorded failure passes as clean and the case fails.
        tampered = [dict(wa_eval.CASES[0], bad="Coli itu onani, bro. Santai.")]
        self.assertEqual(wa_eval.run_cases(tampered), [("id-slang-coli", False, True)])

    def test_case_inputs_are_anonymized(self):
        joined = " ".join(case["input"] + case["bad"] + case["good"] for case in wa_eval.CASES)
        self.assertIsNone(wa_eval.re.search(r"\+?\d{6,}|@\w+@|@g\.us|@s\.whatsapp", joined))


if __name__ == "__main__":
    unittest.main()
