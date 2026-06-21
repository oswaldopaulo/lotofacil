from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from lotofacil.backtest import BacktestReport, walk_forward_backtest
from lotofacil.reporting import backtest_detail_frame, backtest_summary_frame, format_backtest_summary
from lotofacil.data import DrawRecord, ValidatedHistory


def _history_for_backtest() -> ValidatedHistory:
    draws = (
        DrawRecord(1, date(2024, 1, 1), tuple(range(1, 16)), 2),
        DrawRecord(2, date(2024, 1, 4), tuple(range(11, 26)), 3),
        DrawRecord(3, date(2024, 1, 8), tuple(list(range(1, 11)) + list(range(16, 21))), 4),
        DrawRecord(4, date(2024, 1, 11), tuple(list(range(6, 16)) + list(range(21, 26))), 5),
        DrawRecord(5, date(2024, 1, 15), tuple(list(range(1, 6)) + list(range(11, 21))), 6),
        DrawRecord(6, date(2024, 1, 18), tuple(list(range(3, 13)) + list(range(18, 23))), 7),
    )
    return ValidatedHistory(
        source_path=Path("synthetic.xlsx"),
        draws=draws,
        rejected_rows=(),
        warnings=(),
        total_rows=len(draws),
    )


class BacktestTests(unittest.TestCase):
    def test_walk_forward_backtest_uses_past_draws_only(self) -> None:
        history = _history_for_backtest()

        report = walk_forward_backtest(
            history,
            5,
            seed=7,
            window=2,
            max_test_draws=2,
        )

        self.assertIsInstance(report, BacktestReport)
        self.assertEqual(6, len(report.rows))
        self.assertEqual({"baseline", "aleatoria", "balanceada"}, set(report.summaries))
        self.assertEqual(2, report.summaries["baseline"].evaluated_draws)
        self.assertEqual(1, report.summaries["baseline"].skipped_draws)
        self.assertEqual(2, report.rows[0].training_draws)
        self.assertEqual(2, report.rows[1].training_draws)
        self.assertTrue(all(row.generated_quantity == 5 for row in report.rows))
        self.assertTrue(all(row.unique_quantity == 5 for row in report.rows))

    def test_backtest_reporting_frames(self) -> None:
        history = _history_for_backtest()
        report = walk_forward_backtest(history, 5, seed=7, window=2, max_test_draws=2)

        summary_frame = backtest_summary_frame(report)
        detail_frame = backtest_detail_frame(report.rows)

        self.assertEqual(3, len(summary_frame))
        self.assertEqual(6, len(detail_frame))
        text = format_backtest_summary(report)
        self.assertIn("Backtest walk-forward", text)
        self.assertIn("Estrategia: baseline", text)
