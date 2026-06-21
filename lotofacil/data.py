from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import unicodedata

import pandas as pd

BALL_COLUMNS = tuple(f"Bola{i}" for i in range(1, 16))
REQUIRED_COLUMNS = ("Concurso", "Data Sorteio", *BALL_COLUMNS)
DEFAULT_WORKBOOK_NAME = "Lotofacil.xlsx"
PRIZE_TIERS = (11, 12, 13, 14, 15)
PRIZE_WINNER_COLUMNS = {
    11: "Ganhadores 11 acertos",
    12: "Ganhadores 12 acertos",
    13: "Ganhadores 13 acertos",
    14: "Ganhadores 14 acertos",
    15: "Ganhadores 15 acertos",
}
PRIZE_RATEIO_COLUMNS = {
    11: "Rateio 11 acertos",
    12: "Rateio 12 acertos",
    13: "Rateio 13 acertos",
    14: "Rateio 14 acertos",
    15: "Rateio 15 acertos",
}
PRIZE_OPTIONAL_COLUMNS = {
    "acumulated": "Acumulado 15 acertos",
    "collection": "Arrecadacao Total",
    "estimate": "Estimativa Prêmio",
}


class HistoryValidationError(ValueError):
    """Raised when the workbook cannot be read or is structurally invalid."""


@dataclass(frozen=True)
class DrawRecord:
    contest: int
    draw_date: date
    numbers: tuple[int, ...]
    row_number: int


@dataclass(frozen=True)
class ValidationIssue:
    row_number: int
    contest: int | None
    field: str
    message: str


@dataclass(frozen=True)
class PrizeRecord:
    contest: int
    draw_date: date
    winners: tuple[int | None, ...]
    payouts: tuple[float | None, ...]
    row_number: int
    accumulated_prize: float | None = None
    total_collection: float | None = None
    estimated_prize: float | None = None


@dataclass(frozen=True)
class ValidatedHistory:
    source_path: Path
    draws: tuple[DrawRecord, ...]
    rejected_rows: tuple[ValidationIssue, ...]
    warnings: tuple[str, ...]
    total_rows: int
    prize_rows: tuple[PrizeRecord, ...] = ()

    def number_counter(self) -> Counter[int]:
        return Counter(number for draw in self.draws for number in draw.numbers)

    def ticket_set(self) -> set[tuple[int, ...]]:
        return {draw.numbers for draw in self.draws}


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def discover_workbook(search_root: str | Path | None = None) -> Path:
    root = Path(search_root) if search_root is not None else Path.cwd()
    if not root.exists():
        raise FileNotFoundError(f"Diretorio nao encontrado: {root}")

    candidates = [
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() == ".xlsx"
    ]
    if not candidates:
        raise FileNotFoundError("Nenhum arquivo .xlsx foi encontrado na pasta atual.")

    normalized_default = _strip_accents(DEFAULT_WORKBOOK_NAME)
    matches = [path for path in candidates if _strip_accents(path.name).startswith("lotof")]
    if not matches:
        raise FileNotFoundError(
            "Nenhum arquivo de historico Lotofacil foi encontrado. "
            "Passe --arquivo com o caminho da planilha."
        )

    exact = [path for path in matches if _strip_accents(path.name) == normalized_default]
    chosen = exact or matches
    return sorted(chosen, key=lambda item: (_strip_accents(item.name), -item.stat().st_mtime))[0]


def _coerce_int(value: object) -> int | None:
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    text = str(value).strip()
    if not text:
        return None
    try:
        as_float = float(text)
    except (TypeError, ValueError):
        return None
    if not as_float.is_integer():
        return None
    return int(as_float)


def _coerce_date(value: object) -> date | None:
    if pd.isna(value) or value is None:
        return None
    parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _coerce_currency(value: object) -> float | None:
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    cleaned = (
        text.replace("R$", "")
        .replace("\xa0", "")
        .replace(".", "")
        .replace(" ", "")
        .replace(",", ".")
    )
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def _format_number_list(numbers: list[int]) -> str:
    if not numbers:
        return "-"
    return ", ".join(str(number) for number in numbers)


def _optional_column_value(row: pd.Series, column_name: str, parser) -> object:
    if column_name not in row.index:
        return None
    return parser(row[column_name])


def validate_history_frame(
    frame: pd.DataFrame,
    *,
    source_path: Path,
    strict: bool = False,
) -> ValidatedHistory:
    columns = [str(column) for column in frame.columns]
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing_columns:
        raise HistoryValidationError(
            "Colunas obrigatorias ausentes: " + ", ".join(missing_columns)
        )

    draws: list[DrawRecord] = []
    prize_rows: list[PrizeRecord] = []
    rejected_rows: list[ValidationIssue] = []
    contest_date_pairs: list[tuple[int, date, int]] = []

    for row_index, row in frame.iterrows():
        excel_row = int(row_index) + 2
        row_issues: list[ValidationIssue] = []

        contest = _coerce_int(row["Concurso"])
        if contest is None:
            row_issues.append(
                ValidationIssue(
                    row_number=excel_row,
                    contest=None,
                    field="Concurso",
                    message=f"valor invalido: {row['Concurso']!r}",
                )
            )

        draw_date = _coerce_date(row["Data Sorteio"])
        if draw_date is None:
            row_issues.append(
                ValidationIssue(
                    row_number=excel_row,
                    contest=contest,
                    field="Data Sorteio",
                    message=f"valor invalido: {row['Data Sorteio']!r}",
                )
            )

        numbers: list[int] = []
        for column in BALL_COLUMNS:
            value = _coerce_int(row[column])
            if value is None:
                row_issues.append(
                    ValidationIssue(
                        row_number=excel_row,
                        contest=contest,
                        field=column,
                        message=f"valor ausente ou nao inteiro: {row[column]!r}",
                    )
                )
                continue
            if not 1 <= value <= 25:
                row_issues.append(
                    ValidationIssue(
                        row_number=excel_row,
                        contest=contest,
                        field=column,
                        message=f"valor fora da faixa 1..25: {value}",
                    )
                )
                continue
            numbers.append(value)

        if len(numbers) != 15:
            row_issues.append(
                ValidationIssue(
                    row_number=excel_row,
                    contest=contest,
                    field="Bolas",
                    message=f"esperado 15 numeros validos, obtidos {len(numbers)}",
                )
            )

        duplicated = [number for number, count in Counter(numbers).items() if count > 1]
        if duplicated:
            row_issues.append(
                ValidationIssue(
                    row_number=excel_row,
                    contest=contest,
                    field="Bolas",
                    message="numeros repetidos no mesmo concurso: " + _format_number_list(duplicated),
                )
            )

        if contest is not None and draw_date is not None:
            contest_date_pairs.append((contest, draw_date, excel_row))

        if row_issues:
            rejected_rows.extend(row_issues)
            continue

        draws.append(
            DrawRecord(
                contest=contest,
                draw_date=draw_date,
                numbers=tuple(sorted(numbers)),
                row_number=excel_row,
            )
        )

        prize_rows.append(
            PrizeRecord(
                contest=contest,
                draw_date=draw_date,
                winners=tuple(
                    _coerce_int(row[PRIZE_WINNER_COLUMNS[tier]])
                    if PRIZE_WINNER_COLUMNS[tier] in row.index
                    else None
                    for tier in PRIZE_TIERS
                ),
                payouts=tuple(
                    _coerce_currency(row[PRIZE_RATEIO_COLUMNS[tier]])
                    if PRIZE_RATEIO_COLUMNS[tier] in row.index
                    else None
                    for tier in PRIZE_TIERS
                ),
                row_number=excel_row,
                accumulated_prize=_optional_column_value(row, PRIZE_OPTIONAL_COLUMNS["acumulated"], _coerce_currency),
                total_collection=_optional_column_value(row, PRIZE_OPTIONAL_COLUMNS["collection"], _coerce_currency),
                estimated_prize=_optional_column_value(row, PRIZE_OPTIONAL_COLUMNS["estimate"], _coerce_currency),
            )
        )

    warnings: list[str] = []
    if contest_date_pairs:
        contest_values = [contest for contest, _, _ in contest_date_pairs]
        duplicates = [contest for contest, count in Counter(contest_values).items() if count > 1]
        if duplicates:
            warnings.append(
                "Concursos duplicados na base: " + _format_number_list(sorted(duplicates))
            )

        unique_contests = sorted(set(contest_values))
        expected_contests = list(range(unique_contests[0], unique_contests[-1] + 1))
        missing_contests = sorted(set(expected_contests) - set(unique_contests))
        if missing_contests:
            warnings.append(
                "Lacunas na sequencia de concursos: "
                + _format_number_list(missing_contests[:50])
            )

        ordered_pairs = sorted(contest_date_pairs, key=lambda item: item[0])
        ordered_dates = [draw_date for _, draw_date, _ in ordered_pairs]
        if any(later < earlier for earlier, later in zip(ordered_dates, ordered_dates[1:])):
            warnings.append("Datas fora de ordem cronologica em relacao ao numero do concurso.")

    if strict and (rejected_rows or warnings):
        details = [
            f"Fonte: {source_path}",
            f"Linhas totais: {len(frame)}",
            f"Sorteios validos: {len(draws)}",
            f"Linhas rejeitadas: {len(rejected_rows)}",
        ]
        if rejected_rows:
            details.append("Primeiros problemas:")
            for issue in rejected_rows[:10]:
                details.append(
                    f"- linha {issue.row_number}, concurso {issue.contest}, {issue.field}: {issue.message}"
                )
        if warnings:
            details.append("Avisos:")
            details.extend(f"- {warning}" for warning in warnings)
        raise HistoryValidationError("\n".join(details))

    draws = tuple(sorted(draws, key=lambda item: item.contest))
    return ValidatedHistory(
        source_path=source_path,
        draws=draws,
        rejected_rows=tuple(rejected_rows),
        warnings=tuple(warnings),
        total_rows=len(frame),
        prize_rows=tuple(prize_rows),
    )


def load_history(
    path: str | Path | None = None,
    *,
    strict: bool = False,
) -> ValidatedHistory:
    source_path = discover_workbook() if path is None else Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {source_path}")

    try:
        frame = pd.read_excel(source_path, engine="openpyxl")
    except Exception as exc:  # pragma: no cover - error text is environment specific
        raise HistoryValidationError(f"Falha ao ler a planilha: {exc}") from exc

    return validate_history_frame(frame, source_path=source_path, strict=strict)
