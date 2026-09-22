"""The pre-flight model probe, which separates "cannot run here" from "ran and failed".

These tests exercise the parser only. They never call a provider, because a test that
spends money on a live model is not a test.
"""

from __future__ import annotations

import json
import unittest

from tools.benchmark import probe_models


def stream(*records) -> str:
    return "\n".join(json.dumps(record) for record in records)


class AsInt(unittest.TestCase):
    def test_absent_and_none_become_zero(self):
        self.assertEqual(probe_models.as_int(None), 0)
        self.assertEqual(probe_models.as_int(""), 0)

    def test_numbers_and_numeric_strings_are_read(self):
        self.assertEqual(probe_models.as_int(12), 12)
        self.assertEqual(probe_models.as_int("12"), 12)
        self.assertEqual(probe_models.as_int(12.9), 12)

    def test_a_provider_sending_prose_does_not_crash_the_probe(self):
        self.assertEqual(probe_models.as_int("not a number"), 0)
        self.assertEqual(probe_models.as_int({"nested": 1}), 0)


class ParseProbeStream(unittest.TestCase):
    def test_a_usable_model_is_reported_as_usable(self):
        parsed = probe_models.parse_probe_stream(stream(
            {"message": {"role": "assistant", "stopReason": "stop",
                         "usage": {"input": 40, "output": 7}}},
        ))
        self.assertTrue(parsed["sawAssistantMessage"])
        self.assertIsNone(parsed["errorMessage"])
        self.assertEqual(parsed["outputTokens"], 7)
        self.assertEqual(parsed["inputTokens"], 40)

    def test_a_refused_model_carries_the_provider_message(self):
        parsed = probe_models.parse_probe_stream(stream(
            {"message": {"role": "assistant", "stopReason": "error",
                         "errorMessage": "Codex error: not supported",
                         "usage": {"input": 0, "output": 0}}},
        ))
        self.assertTrue(parsed["sawAssistantMessage"])
        self.assertEqual(parsed["errorMessage"], "Codex error: not supported")

    def test_no_assistant_message_means_the_model_never_answered(self):
        parsed = probe_models.parse_probe_stream(stream({"type": "agent_settled"}))
        self.assertFalse(parsed["sawAssistantMessage"])
        self.assertIsNone(parsed["errorMessage"])

    def test_non_json_output_is_ignored(self):
        parsed = probe_models.parse_probe_stream("hello\nworld\n")
        self.assertFalse(parsed["sawAssistantMessage"])

    def test_a_user_message_is_not_mistaken_for_the_model(self):
        parsed = probe_models.parse_probe_stream(stream(
            {"message": {"role": "user", "content": "Reply OK",
                         "usage": {"output": 999}}},
        ))
        self.assertFalse(parsed["sawAssistantMessage"])
        self.assertEqual(parsed["outputTokens"], 0)

    def test_usage_across_several_turns_is_summed(self):
        parsed = probe_models.parse_probe_stream(stream(
            {"message": {"role": "assistant", "stopReason": "toolUse",
                         "usage": {"input": 10, "output": 5}}},
            {"message": {"role": "assistant", "stopReason": "stop",
                         "usage": {"input": 20, "output": 6}}},
        ))
        self.assertEqual(parsed["inputTokens"], 30)
        self.assertEqual(parsed["outputTokens"], 11)


class Summarize(unittest.TestCase):
    def test_usable_and_unusable_are_split(self):
        report = probe_models.summarize([
            {"route": "p/a", "usable": True, "errorMessage": None},
            {"route": "p/b", "usable": False, "errorMessage": "refused"},
        ])
        self.assertEqual(report["usable"], ["p/a"])
        self.assertEqual(report["unusable"], {"p/b": "refused"})
        self.assertEqual(report["probed"], 2)

    def test_every_verdict_is_kept_in_the_report(self):
        results = [{"route": "p/a", "usable": True, "errorMessage": None}]
        self.assertEqual(probe_models.summarize(results)["results"], results)


class RouteParsing(unittest.TestCase):
    def test_a_route_without_a_model_is_rejected_before_any_call(self):
        with self.assertRaises(ValueError):
            probe_models.probe_all(["openai-codex"])

    def test_a_route_without_a_provider_is_rejected_before_any_call(self):
        with self.assertRaises(ValueError):
            probe_models.probe_all(["/gpt-6-astra"])


if __name__ == "__main__":
    unittest.main()
