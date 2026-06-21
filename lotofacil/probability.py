from __future__ import annotations

from dataclasses import dataclass
from math import comb

TOTAL_NUMBERS = 25
DRAW_SIZE = 15
POSSIBLE_DRAW_COUNT = comb(TOTAL_NUMBERS, DRAW_SIZE)
MIN_BET_SIZE = 15
MAX_BET_SIZE = 20
DEFAULT_BET_SIZE = 15
OFFICIAL_BET_PRICES = {
    15: 3.50,
    16: 56.00,
    17: 476.00,
    18: 2856.00,
    19: 13566.00,
    20: 54264.00,
}


@dataclass(frozen=True)
class MatchDistributionEntry:
    hits: int
    probability: float


def validate_bet_size(ticket_size: int) -> int:
    if ticket_size < MIN_BET_SIZE or ticket_size > MAX_BET_SIZE:
        raise ValueError(f"ticket_size must be between {MIN_BET_SIZE} and {MAX_BET_SIZE}")
    return ticket_size


def exact_match_probability(
    hits: int,
    *,
    population: int = TOTAL_NUMBERS,
    success_states: int = DRAW_SIZE,
    draws: int = DRAW_SIZE,
) -> float:
    if hits < 0 or hits > draws or hits > success_states:
        return 0.0
    failures = population - success_states
    if draws - hits > failures:
        return 0.0
    return (
        comb(success_states, hits)
        * comb(failures, draws - hits)
        / comb(population, draws)
    )


def ticket_size_to_combination_count(ticket_size: int) -> int:
    ticket_size = validate_bet_size(ticket_size)
    return comb(ticket_size, DRAW_SIZE)


def ticket_size_to_jackpot_probability(ticket_size: int) -> float:
    ticket_size = validate_bet_size(ticket_size)
    return ticket_size_to_combination_count(ticket_size) / POSSIBLE_DRAW_COUNT


def ticket_size_to_jackpot_odds(ticket_size: int) -> float:
    probability = ticket_size_to_jackpot_probability(ticket_size)
    if probability == 0:
        return float("inf")
    return 1.0 / probability


def official_ticket_price(ticket_size: int) -> float:
    ticket_size = validate_bet_size(ticket_size)
    return OFFICIAL_BET_PRICES[ticket_size]


def exact_match_distribution(
    *,
    population: int = TOTAL_NUMBERS,
    success_states: int = DRAW_SIZE,
    draws: int = DRAW_SIZE,
) -> tuple[MatchDistributionEntry, ...]:
    entries = [
        MatchDistributionEntry(
            hits=hits,
            probability=exact_match_probability(
                hits,
                population=population,
                success_states=success_states,
                draws=draws,
            ),
        )
        for hits in range(0, min(success_states, draws) + 1)
    ]
    return tuple(entries)


def probability_at_least(
    hits: int,
    *,
    population: int = TOTAL_NUMBERS,
    success_states: int = DRAW_SIZE,
    draws: int = DRAW_SIZE,
) -> float:
    if hits <= 0:
        return 1.0
    upper = min(success_states, draws)
    return sum(
        exact_match_probability(
            current,
            population=population,
            success_states=success_states,
            draws=draws,
        )
        for current in range(hits, upper + 1)
    )


def expected_hits(
    *,
    population: int = TOTAL_NUMBERS,
    success_states: int = DRAW_SIZE,
    draws: int = DRAW_SIZE,
) -> float:
    return draws * success_states / population


def ticket_count_to_jackpot_probability(ticket_count: int) -> float:
    if ticket_count <= 0:
        return 0.0
    return min(1.0, ticket_count / POSSIBLE_DRAW_COUNT)


def ticket_count_to_jackpot_odds(ticket_count: int) -> float:
    probability = ticket_count_to_jackpot_probability(ticket_count)
    if probability == 0:
        return float("inf")
    return 1.0 / probability
