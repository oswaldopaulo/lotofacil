from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path

import pandas as pd

from lotofacil.data import BALL_COLUMNS, DrawRecord, PrizeRecord, REQUIRED_COLUMNS, ValidatedHistory


def build_row(contest: int, draw_date: str, numbers: Iterable[int], **extra_columns: object) -> dict[str, object]:
    row: dict[str, object] = {
        "Concurso": contest,
        "Data Sorteio": draw_date,
    }
    for index, number in enumerate(numbers, start=1):
        row[f"Bola{index}"] = number
    row.update(extra_columns)
    return row


def valid_history() -> ValidatedHistory:
    draws = (
        DrawRecord(1, date(2024, 1, 1), tuple(range(1, 16)), 2),
        DrawRecord(2, date(2024, 1, 4), tuple(range(11, 26)), 3),
        DrawRecord(3, date(2024, 1, 8), tuple(list(range(1, 11)) + list(range(16, 21))), 4),
    )
    return ValidatedHistory(
        source_path=Path("synthetic.xlsx"),
        draws=draws,
        rejected_rows=(),
        warnings=(),
        total_rows=3,
    )


def valid_history_with_prizes() -> ValidatedHistory:
    draws = (
        DrawRecord(1, date(2024, 1, 1), tuple(range(1, 16)), 2),
        DrawRecord(2, date(2024, 1, 4), tuple(range(11, 26)), 3),
        DrawRecord(3, date(2024, 1, 8), tuple(list(range(1, 11)) + list(range(16, 21))), 4),
    )
    prize_rows = (
        PrizeRecord(
            contest=1,
            draw_date=date(2024, 1, 1),
            winners=(1, 2, 3, 4, 5),
            payouts=(7.0, 14.0, 35.0, 5000.0, 1_200_000.0),
            row_number=2,
            accumulated_prize=1_100_000.0,
            total_collection=3_500_000.0,
            estimated_prize=1_250_000.0,
        ),
        PrizeRecord(
            contest=2,
            draw_date=date(2024, 1, 4),
            winners=(2, 3, 4, 5, 6),
            payouts=(7.0, 14.0, 35.0, 6_000.0, 1_500_000.0),
            row_number=3,
            accumulated_prize=1_250_000.0,
            total_collection=3_650_000.0,
            estimated_prize=1_350_000.0,
        ),
        PrizeRecord(
            contest=3,
            draw_date=date(2024, 1, 8),
            winners=(3, 4, 5, 6, 7),
            payouts=(7.0, 14.0, 35.0, 7_500.0, 1_800_000.0),
            row_number=4,
            accumulated_prize=1_400_000.0,
            total_collection=3_800_000.0,
            estimated_prize=1_450_000.0,
        ),
    )
    return ValidatedHistory(
        source_path=Path("synthetic.xlsx"),
        draws=draws,
        rejected_rows=(),
        warnings=(),
        total_rows=3,
        prize_rows=prize_rows,
    )


def write_workbook(rows: list[dict[str, object]], destination: Path) -> Path:
    frame = pd.DataFrame(rows)
    for column in REQUIRED_COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    frame = frame.loc[:, list(REQUIRED_COLUMNS) + [column for column in frame.columns if column not in REQUIRED_COLUMNS]]
    frame.to_excel(destination, index=False)
    return destination
