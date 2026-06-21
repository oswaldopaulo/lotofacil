from __future__ import annotations

from collections import Counter
import unittest

from lotofacil.portfolio import (
    PortfolioCapacityError,
    build_baseline_groups,
    compare_portfolios,
    evaluate_portfolio,
    generate_baseline_portfolio,
    generate_balanced_portfolio,
    generate_random_portfolio,
    simulate_draws,
)

from tests.helpers import valid_history


class PortfolioTests(unittest.TestCase):
    def test_baseline_generation_is_reproducible(self) -> None:
        history = valid_history()
        first = generate_baseline_portfolio(history, 56, seed=123, forbidden_tickets=set(), strict_quantity=True)
        second = generate_baseline_portfolio(history, 56, seed=123, forbidden_tickets=set(), strict_quantity=True)

        self.assertEqual(first, second)
        self.assertEqual(56, len(first))
        self.assertEqual(56, len(set(first)))
        self.assertTrue(all(len(ticket) == 15 for ticket in first))

        groups = build_baseline_groups(history)
        self.assertEqual(8, len(groups))
        self.assertTrue(all(len(group) == 3 for group in groups))

    def test_baseline_capacity_limit(self) -> None:
        history = valid_history()
        with self.assertRaises(PortfolioCapacityError):
            generate_baseline_portfolio(history, 57, forbidden_tickets=set(), strict_quantity=True)

    def test_random_portfolio_is_reproducible(self) -> None:
        first = generate_random_portfolio(10, seed=7)
        second = generate_random_portfolio(10, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(10, len(first))
        self.assertEqual(10, len(set(first)))

    def test_wide_portfolios_support_twenty_numbers(self) -> None:
        history = valid_history()
        first = generate_baseline_portfolio(
            history,
            10,
            ticket_size=20,
            seed=123,
            forbidden_tickets=set(),
            strict_quantity=True,
        )
        second = generate_random_portfolio(10, ticket_size=20, seed=7)
        third = generate_balanced_portfolio(10, ticket_size=20, seed=9, candidate_pool=50)

        self.assertEqual(first, generate_baseline_portfolio(
            history,
            10,
            ticket_size=20,
            seed=123,
            forbidden_tickets=set(),
            strict_quantity=True,
        ))
        self.assertTrue(all(len(ticket) == 20 for ticket in first))
        self.assertTrue(all(len(ticket) == 20 for ticket in second))
        self.assertTrue(all(len(ticket) == 20 for ticket in third))

    def test_balanced_portfolio_is_reasonably_even(self) -> None:
        portfolio = generate_balanced_portfolio(56, seed=7, candidate_pool=200)
        counts = Counter(number for ticket in portfolio for number in ticket)

        self.assertEqual(56, len(portfolio))
        self.assertEqual(56, len(set(portfolio)))
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 6)

    def test_portfolio_evaluation_works(self) -> None:
        portfolio = generate_random_portfolio(12, seed=21)
        sample_draws = simulate_draws(100, seed=99)
        evaluation = evaluate_portfolio(portfolio, sample_draws=sample_draws)

        self.assertEqual(12, evaluation.generated_quantity)
        self.assertEqual(12, evaluation.unique_quantity)
        self.assertEqual(100, sum(evaluation.best_hit_histogram.values()))
        self.assertIn(11, evaluation.threshold_any_rates)

    def test_compare_portfolios_returns_all_strategies(self) -> None:
        history = valid_history()
        portfolios = {
            "baseline": generate_baseline_portfolio(history, 20, seed=1, forbidden_tickets=set(), strict_quantity=True),
            "aleatoria": generate_random_portfolio(20, seed=2),
            "balanceada": generate_balanced_portfolio(20, seed=3, candidate_pool=120),
        }
        evaluations = compare_portfolios(portfolios, sample_draw_count=50, seed=4)

        self.assertEqual({"baseline", "aleatoria", "balanceada"}, set(evaluations))
        self.assertTrue(all(evaluation.generated_quantity == 20 for evaluation in evaluations.values()))
