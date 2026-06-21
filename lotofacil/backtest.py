from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from statistics import mean

from .data import DrawRecord, ValidatedHistory
from .portfolio import (
    Ticket,
    generate_baseline_portfolio,
    generate_balanced_portfolio,
    generate_random_portfolio,
    draw_to_mask,
)

THRESHOLDS = (11, 12, 13, 14, 15)
STRATEGY_OFFSETS = {
    "baseline": 11,
    "aleatoria": 23,
    "balanceada": 37,
}


@dataclass(frozen=True)
class BacktestRow:
    contest: int
    draw_date: date
    strategy: str
    training_draws: int
    generated_quantity: int
    unique_quantity: int
    best_hit: int
    winners_11: int
    winners_12: int
    winners_13: int
    winners_14: int
    winners_15: int


@dataclass(frozen=True)
class BacktestSummary:
    strategy: str
    requested_quantity: int
    evaluated_draws: int
    skipped_draws: int
    average_training_draws: float
    mean_best_hit: float
    best_hit_histogram: dict[int, int]
    threshold_any_rates: dict[int, float]
    threshold_mean_winners: dict[int, float]
    jackpot_hits: int
    jackpot_rate: float


@dataclass(frozen=True)
class BacktestReport:
    source_path: str
    quantity: int
    ticket_size: int
    seed: int
    window_size: int | None
    step: int
    max_test_draws: int | None
    rows: tuple[BacktestRow, ...]
    summaries: dict[str, BacktestSummary]


def _history_slice(source_history: ValidatedHistory, draws: tuple[DrawRecord, ...]) -> ValidatedHistory:
    return ValidatedHistory(
        source_path=source_history.source_path,
        draws=draws,
        rejected_rows=(),
        warnings=(),
        total_rows=len(draws),
    )


def _strategy_seed(base_seed: int, contest: int, strategy: str) -> int:
    return base_seed + contest * 1009 + STRATEGY_OFFSETS[strategy]


def _generate_portfolio_for_strategy(
    strategy: str,
    training_history: ValidatedHistory,
    quantity: int,
    *,
    ticket_size: int,
    seed: int,
    pair_weight: float,
    balanced_candidate_pool: int,
) -> tuple[Ticket, ...]:
    forbidden = training_history.ticket_set()
    if strategy == "baseline":
        return generate_baseline_portfolio(
            training_history,
            quantity,
            ticket_size=ticket_size,
            seed=seed,
            forbidden_tickets=forbidden,
            strict_quantity=True,
        )
    if strategy == "aleatoria":
        return generate_random_portfolio(
            quantity,
            ticket_size=ticket_size,
            seed=seed,
            forbidden_tickets=forbidden,
            strict_quantity=True,
        )
    if strategy == "balanceada":
        return generate_balanced_portfolio(
            quantity,
            ticket_size=ticket_size,
            seed=seed,
            forbidden_tickets=forbidden,
            candidate_pool=balanced_candidate_pool,
            pair_weight=pair_weight,
            strict_quantity=True,
        )
    raise ValueError(f"Estrategia desconhecida: {strategy}")


def _evaluate_portfolio(portfolio: tuple[Ticket, ...], draw: Ticket) -> tuple[int, dict[int, int]]:
    draw_mask = draw_to_mask(draw)
    best_hit = 0
    winners = {threshold: 0 for threshold in THRESHOLDS}
    for ticket in portfolio:
        hits = (draw_to_mask(ticket) & draw_mask).bit_count()
        if hits > best_hit:
            best_hit = hits
        for threshold in THRESHOLDS:
            if hits >= threshold:
                winners[threshold] += 1
    return best_hit, winners


def walk_forward_backtest(
    history: ValidatedHistory,
    quantity: int,
    *,
    ticket_size: int = 15,
    seed: int = 42,
    window: int = 100,
    step: int = 1,
    strategies: tuple[str, ...] = ("baseline", "aleatoria", "balanceada"),
    pair_weight: float = 0.15,
    balanced_candidate_pool: int = 80,
    max_test_draws: int | None = 250,
) -> BacktestReport:
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if ticket_size < 15 or ticket_size > 20:
        raise ValueError("ticket_size must be between 15 and 20")
    if step <= 0:
        raise ValueError("step must be positive")
    if window < 0:
        raise ValueError("window must be non-negative")
    if balanced_candidate_pool <= 0:
        raise ValueError("balanced_candidate_pool must be positive")
    if pair_weight <= 0:
        raise ValueError("pair_weight must be positive")
    if not strategies:
        raise ValueError("strategies must not be empty")

    draws = history.draws
    if len(draws) < 2:
        raise ValueError("history must contain at least two draws for backtesting")

    supported = set(STRATEGY_OFFSETS)
    unknown = [strategy for strategy in strategies if strategy not in supported]
    if unknown:
        raise ValueError(f"Estrategias desconhecidas: {', '.join(sorted(unknown))}")

    rows: list[BacktestRow] = []
    summary_state = {
        strategy: {
            "evaluated_draws": 0,
            "skipped_draws": 0,
            "training_draws": [],
            "best_hit_sum": 0.0,
            "best_hit_histogram": Counter(),
            "threshold_any_hits": Counter(),
            "threshold_winner_sum": Counter(),
            "jackpot_hits": 0,
        }
        for strategy in strategies
    }

    evaluated_draws = 0
    for index in range(1, len(draws), step):
        if max_test_draws is not None and max_test_draws > 0 and evaluated_draws >= max_test_draws:
            break

        train_start = max(0, index - window) if window > 0 else 0
        training_draws = draws[train_start:index]
        if not training_draws:
            continue

        training_history = _history_slice(history, training_draws)
        if len(training_history.number_counter()) < 24:
            for strategy in strategies:
                summary_state[strategy]["skipped_draws"] += 1
            continue

        test_draw = draws[index]
        row_results: dict[str, tuple[int, dict[int, int], tuple[Ticket, ...]]] = {}
        try:
            for strategy in strategies:
                portfolio = _generate_portfolio_for_strategy(
                    strategy,
                    training_history,
                    quantity,
                    ticket_size=ticket_size,
                    seed=_strategy_seed(seed, test_draw.contest, strategy),
                    pair_weight=pair_weight,
                    balanced_candidate_pool=balanced_candidate_pool,
                )
                best_hit, winners = _evaluate_portfolio(portfolio, test_draw.numbers)
                row_results[strategy] = (best_hit, winners, portfolio)
        except Exception:
            for strategy in strategies:
                summary_state[strategy]["skipped_draws"] += 1
            continue

        evaluated_draws += 1
        for strategy, (best_hit, winners, portfolio) in row_results.items():
            state = summary_state[strategy]
            state["evaluated_draws"] += 1
            state["training_draws"].append(len(training_draws))
            state["best_hit_sum"] += best_hit
            state["best_hit_histogram"][best_hit] += 1
            for threshold in THRESHOLDS:
                if winners[threshold] > 0:
                    state["threshold_any_hits"][threshold] += 1
                state["threshold_winner_sum"][threshold] += winners[threshold]
            if winners[15] > 0:
                state["jackpot_hits"] += 1

            rows.append(
                BacktestRow(
                    contest=test_draw.contest,
                    draw_date=test_draw.draw_date,
                    strategy=strategy,
                    training_draws=len(training_draws),
                    generated_quantity=len(portfolio),
                    unique_quantity=len(set(portfolio)),
                    best_hit=best_hit,
                    winners_11=winners[11],
                    winners_12=winners[12],
                    winners_13=winners[13],
                    winners_14=winners[14],
                    winners_15=winners[15],
                )
            )

    summaries: dict[str, BacktestSummary] = {}
    for strategy in strategies:
        state = summary_state[strategy]
        evaluated = state["evaluated_draws"]
        summaries[strategy] = BacktestSummary(
            strategy=strategy,
            requested_quantity=quantity,
            evaluated_draws=evaluated,
            skipped_draws=state["skipped_draws"],
            average_training_draws=mean(state["training_draws"]) if state["training_draws"] else 0.0,
            mean_best_hit=(state["best_hit_sum"] / evaluated) if evaluated else 0.0,
            best_hit_histogram=dict(sorted(state["best_hit_histogram"].items())),
            threshold_any_rates={
                threshold: (state["threshold_any_hits"][threshold] / evaluated) if evaluated else 0.0
                for threshold in THRESHOLDS
            },
            threshold_mean_winners={
                threshold: (state["threshold_winner_sum"][threshold] / evaluated) if evaluated else 0.0
                for threshold in THRESHOLDS
            },
            jackpot_hits=state["jackpot_hits"],
            jackpot_rate=(state["jackpot_hits"] / evaluated) if evaluated else 0.0,
        )

    return BacktestReport(
        source_path=str(history.source_path),
        quantity=quantity,
        ticket_size=ticket_size,
        seed=seed,
        window_size=window if window > 0 else None,
        step=step,
        max_test_draws=max_test_draws if max_test_draws and max_test_draws > 0 else None,
        rows=tuple(rows),
        summaries=summaries,
    )
