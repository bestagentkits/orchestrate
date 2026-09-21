"""The fifteen issue #15 regression fixtures, each shown to be able to fail.

Run from the repository root:

    PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m unittest discover -s tools/contracts/tests -t . -v

The cache prefix is required for any run that exercises mutated code; see instrument
defect ID-1 in `plans/260921-0805-issue15-contract-reconciliation/instrument-defects.md`.

Every fixture is evaluated twice: once against the owned contract, where its invariant must
hold, and once against the behaviour it replaced, where it must fail. A fixture that cannot
fail is not evidence, and this module refuses to treat it as such.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.contracts import invariants  # noqa: E402


class TheFixtureSetIsWellFormed(unittest.TestCase):
    def test_there_are_fifteen_distinct_regressions(self):
        self.assertEqual(len(invariants.REGRESSIONS), invariants.REGRESSION_COUNT)
        self.assertEqual(invariants.REGRESSION_COUNT, 15)

    def test_the_ids_are_unique_and_sequential(self):
        ids = [regression["id"] for regression in invariants.REGRESSIONS]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(ids, [f"R{index:02d}" for index in range(1, 16)])

    def test_every_regression_names_its_owner_and_its_scenario(self):
        for regression in invariants.REGRESSIONS:
            with self.subTest(regression=regression["id"]):
                self.assertTrue(regression["name"])
                self.assertTrue(regression["owner"])
                self.assertTrue(callable(regression["contract"]))
                self.assertTrue(callable(regression["broken"]))
                self.assertTrue(callable(regression["holds"]))


class EveryFixtureCanFail(unittest.TestCase):
    def test_each_invariant_holds_on_the_contract(self):
        for row in invariants.run_all():
            with self.subTest(regression=row["id"], name=row["name"]):
                self.assertTrue(
                    row["contract_holds"],
                    f"{row['id']} must hold on the contract behaviour: {row['name']}",
                )

    def test_each_invariant_fails_on_the_broken_behaviour(self):
        """The load-bearing assertion: a fixture that cannot fail proves nothing."""
        for row in invariants.run_all():
            with self.subTest(regression=row["id"], name=row["name"]):
                self.assertTrue(
                    row["broken_fails"],
                    f"{row['id']} must FAIL on the broken behaviour: {row['name']}",
                )

    def test_no_fixture_is_vacuous(self):
        """Every fixture must distinguish the contract from the behaviour it replaced."""
        for regression in invariants.REGRESSIONS:
            with self.subTest(regression=regression["id"]):
                contract_result = regression["contract"]()
                broken_result = regression["broken"]()
                self.assertNotEqual(
                    regression["holds"](contract_result),
                    regression["holds"](broken_result),
                    f"{regression['id']} does not distinguish contract from broken behaviour",
                )

    def test_the_recorded_summary_reports_fifteen_passing_fixtures(self):
        rows = invariants.run_all()
        self.assertEqual(len(rows), 15)
        self.assertEqual(sum(1 for row in rows if row["contract_holds"]), 15)
        self.assertEqual(sum(1 for row in rows if row["broken_fails"]), 15)


class TheNormativePayloadIsClean(unittest.TestCase):
    def test_no_normative_reference_names_a_model_default(self):
        offenders = invariants.scan_normative_model_defaults(invariants.normative_text())
        self.assertEqual(offenders, [], f"a model name leaked into the payload: {offenders}")

    def test_the_scanner_can_actually_detect_one(self):
        """Otherwise the check above would pass by being unable to find anything."""
        self.assertTrue(invariants.scan_normative_model_defaults("prefer gpt-6-astra"))
        self.assertTrue(invariants.scan_normative_model_defaults("GLM-5.3-Flash wins"))
        self.assertTrue(invariants.scan_normative_model_defaults("DeepSeek V4.1 is cheaper"))

    def test_the_scanner_does_not_flag_a_generic_harness_mention(self):
        self.assertEqual(invariants.scan_normative_model_defaults("run under Claude Code"), [])


class NoProviderOrModelNameIsNormative(unittest.TestCase):
    def test_module_source_names_no_current_model(self):
        import tools.contracts.invariants as module

        source_path = module.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as handle:
            source = handle.read().lower()
        # The scanner's own brand list is exempt; every other occurrence is a leak.
        without_scanner = source.replace(
            "gpt|glm|deepseek|kimi|qwen|gemini|claude|mistral|llama|luna|astra|opus|sonnet|haiku",
            "",
        ).replace("gpt-6-astra", "").replace("glm-5.3-flash", "").replace("deepseek v4.1", "")
        for brand in ("gpt", "deepseek", "glm", "luna", "astra", "kimi", "gemini", "qwen"):
            self.assertNotIn(brand, without_scanner,
                             "a current model brand leaked outside the scanner's brand list")


if __name__ == "__main__":
    unittest.main()
