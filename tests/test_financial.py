from __future__ import annotations

import unittest

from lotofacil.financial import build_prize_profile, compare_portfolios_financially
from lotofacil.portfolio import (
    generate_baseline_portfolio,
    generate_balanced_portfolio,
    generate_random_portfolio,
)
from lotofacil.probability import official_ticket_price

from tests.helpers import valid_history_with_prizes


class FinancialTests(unittest.TestCase):
    def test_build_prize_profile_uses_fixed_and_recent_payouts(self) -> None:
        history = valid_history_with_prizes()

        profile = build_prize_profile(history)

        self.assertEqual(7.0, profile.tier_profiles[11].estimated_payout)
        self.assertEqual(14.0, profile.tier_profiles[12].estimated_payout)
        self.assertEqual(35.0, profile.tier_profiles[13].estimated_payout)
        self.assertEqual(6_000.0, profile.tier_profiles[14].estimated_payout)
        self.assertEqual(1_500_000.0, profile.tier_profiles[15].estimated_payout)

    def test_compare_portfolios_financially_returns_risk_metrics(self) -> None:
        history = valid_history_with_prizes()
        portfolios = {
            "baseline": generate_baseline_portfolio(history, 5, seed=1, forbidden_tickets=set()),
            "aleatoria": generate_random_portfolio(5, seed=2),
            "balanceada": generate_balanced_portfolio(5, seed=3, candidate_pool=40),
        }

        profile, summaries = compare_portfolios_financially(
            portfolios,
            history,
            ticket_price=3.50,
            simulations=50,
            seed=4,
        )

        self.assertEqual(3, len(summaries))
        self.assertEqual(5, len(profile.tier_profiles))
        baseline = summaries["baseline"]
        self.assertEqual(5, baseline.requested_quantity)
        self.assertEqual(5, baseline.unique_quantity)
        self.assertAlmostEqual(17.5, baseline.total_cost)
        self.assertAlmostEqual(
            baseline.estimated_gross_return - baseline.total_cost,
            baseline.estimated_net_return,
        )
        self.assertGreater(baseline.estimated_gross_per_ticket, 0.0)
        self.assertGreaterEqual(baseline.probability_any_prize, 0.0)
        self.assertLessEqual(baseline.probability_any_prize, 1.0)
        self.assertEqual(50, baseline.simulations)

    def test_compare_portfolios_financially_supports_twenty_number_bets(self) -> None:
        history = valid_history_with_prizes()
        portfolios = {
            "aleatoria": generate_random_portfolio(2, ticket_size=20, seed=5),
        }

        _, summaries = compare_portfolios_financially(
            portfolios,
            history,
            simulations=20,
            seed=6,
        )

        summary = summaries["aleatoria"]
        self.assertEqual(20, summary.ticket_size)
        self.assertEqual(15504, summary.combination_count)
        self.assertAlmostEqual(official_ticket_price(20) * 2, summary.total_cost)
