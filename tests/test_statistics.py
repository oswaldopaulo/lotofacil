from __future__ import annotations

import unittest

from lotofacil.statistics import (
    bayesian_smoothed_probability,
    chi_square_uniform_test,
    cumulative_probability_model,
    frequency_table,
    wilson_interval,
)

from tests.helpers import valid_history


class StatisticsTests(unittest.TestCase):
    def test_frequency_table_and_chi_square(self) -> None:
        history = valid_history()
        entries = frequency_table(history.draws)
        self.assertEqual(25, len(entries))

        result = chi_square_uniform_test(history.draws)
        self.assertEqual(24, result.degrees_of_freedom)
        self.assertGreaterEqual(result.p_value, 0.0)
        self.assertLessEqual(result.p_value, 1.0)

    def test_frequency_models_and_intervals(self) -> None:
        history = valid_history()
        model = cumulative_probability_model(history.draws)
        self.assertEqual(25, len(model))
        self.assertTrue(all(0.0 <= value <= 1.0 for value in model.values()))

        low, high = wilson_interval(30, 50)
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(high, 1.0)

        self.assertGreater(bayesian_smoothed_probability(30, 50), 0.0)
