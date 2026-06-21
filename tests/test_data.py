from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

import pandas as pd

from lotofacil.data import HistoryValidationError, load_history

from tests.helpers import build_row, write_workbook


class DataValidationTests(unittest.TestCase):
    def test_load_history_accepts_valid_workbook(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "Lotofacil_teste.xlsx"
            rows = [
                build_row(1, "01/01/2024", range(1, 16)),
                build_row(2, "04/01/2024", range(11, 26)),
                build_row(3, "08/01/2024", list(range(1, 11)) + list(range(16, 21))),
            ]
            write_workbook(rows, path)

            history = load_history(path)

            self.assertEqual(3, len(history.draws))
            self.assertFalse(history.rejected_rows)
            self.assertFalse(history.warnings)
            self.assertEqual([1, 2, 3], [draw.contest for draw in history.draws])

    def test_load_history_parses_prize_information(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "Lotofacil_teste.xlsx"
            rows = [
                build_row(
                    1,
                    "01/01/2024",
                    range(1, 16),
                    **{
                        "Ganhadores 15 acertos": 1,
                        "Rateio 15 acertos": 1_200_000.0,
                        "Ganhadores 14 acertos": 2,
                        "Rateio 14 acertos": 5_000.0,
                        "Ganhadores 13 acertos": 3,
                        "Rateio 13 acertos": 35.0,
                        "Ganhadores 12 acertos": 4,
                        "Rateio 12 acertos": 14.0,
                        "Ganhadores 11 acertos": 5,
                        "Rateio 11 acertos": 7.0,
                        "Acumulado 15 acertos": 1_100_000.0,
                        "Arrecadacao Total": 3_500_000.0,
                        "Estimativa Prêmio": 1_250_000.0,
                    },
                ),
                build_row(2, "04/01/2024", range(11, 26)),
                build_row(3, "08/01/2024", list(range(1, 11)) + list(range(16, 21))),
            ]
            write_workbook(rows, path)

            history = load_history(path)

            self.assertEqual(3, len(history.prize_rows))
            first_prize = history.prize_rows[0]
            self.assertEqual((5, 4, 3, 2, 1), first_prize.winners)
            self.assertEqual((7.0, 14.0, 35.0, 5000.0, 1200000.0), first_prize.payouts)
            self.assertEqual(1_100_000.0, first_prize.accumulated_prize)
            self.assertEqual(3_500_000.0, first_prize.total_collection)
            self.assertEqual(1_250_000.0, first_prize.estimated_prize)

    def test_rejects_invalid_rows_without_polluting_valid_draws(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "Lotofacil_teste.xlsx"
            rows = [
                build_row(1, "01/01/2024", range(1, 16)),
                build_row(2, "04/01/2024", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 99]),
                build_row(3, "08/01/2024", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 14]),
            ]
            write_workbook(rows, path)

            history = load_history(path)

            self.assertEqual(1, len(history.draws))
            self.assertGreaterEqual(len(history.rejected_rows), 2)
            messages = " ".join(issue.message for issue in history.rejected_rows)
            self.assertIn("fora da faixa", messages)
            self.assertIn("repetidos", messages)

    def test_missing_columns_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "Lotofacil_teste.xlsx"
            frame = pd.DataFrame(
                [
                    {
                        "Concurso": 1,
                        "Data Sorteio": "01/01/2024",
                        **{f"Bola{i}": i for i in range(1, 15)},
                    }
                ]
            )
            frame.to_excel(path, index=False)

            with self.assertRaises(HistoryValidationError):
                load_history(path)
