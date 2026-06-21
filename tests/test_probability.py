from __future__ import annotations

import math
import unittest

from lotofacil.probability import (
    DRAW_SIZE,
    official_ticket_price,
    POSSIBLE_DRAW_COUNT,
    exact_match_distribution,
    exact_match_probability,
    expected_hits,
    probability_at_least,
    ticket_count_to_jackpot_odds,
    ticket_count_to_jackpot_probability,
    ticket_size_to_jackpot_odds,
    ticket_size_to_jackpot_probability,
)


class ProbabilityTests(unittest.TestCase):
    def test_draw_count_and_jackpot_probability(self) -> None:
        self.assertEqual(3268760, POSSIBLE_DRAW_COUNT)
        self.assertAlmostEqual(1.0 / POSSIBLE_DRAW_COUNT, exact_match_probability(15))
        self.assertAlmostEqual(56 / POSSIBLE_DRAW_COUNT, ticket_count_to_jackpot_probability(56))
        self.assertAlmostEqual(POSSIBLE_DRAW_COUNT / 56, ticket_count_to_jackpot_odds(56))
        self.assertAlmostEqual(15504 / POSSIBLE_DRAW_COUNT, ticket_size_to_jackpot_probability(20))
        self.assertAlmostEqual(POSSIBLE_DRAW_COUNT / 15504, ticket_size_to_jackpot_odds(20), places=2)
        self.assertEqual(54264.0, official_ticket_price(20))

    def test_distribution_sums_to_one(self) -> None:
        total = sum(entry.probability for entry in exact_match_distribution())
        self.assertAlmostEqual(1.0, total, places=12)

    def test_probability_bounds(self) -> None:
        self.assertGreater(probability_at_least(11), 0.0)
        self.assertLess(probability_at_least(11), 1.0)
        self.assertAlmostEqual(9.0, expected_hits())
