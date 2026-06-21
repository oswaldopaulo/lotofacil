from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import comb
from random import Random
from statistics import mean, pstdev

from .data import ValidatedHistory
from .probability import (
    DEFAULT_BET_SIZE,
    MAX_BET_SIZE,
    MIN_BET_SIZE,
)

Ticket = tuple[int, ...]
PORTFOLIO_TICKET_SIZE = DEFAULT_BET_SIZE
MIN_PORTFOLIO_TICKET_SIZE = MIN_BET_SIZE
MAX_PORTFOLIO_TICKET_SIZE = MAX_BET_SIZE
PORTFOLIO_NUMBER_COUNT = 25
BASELINE_GROUP_COUNT = 8
BASELINE_GROUP_SIZE = 3
BASELINE_PORTFOLIO_CAPACITY = comb(BASELINE_GROUP_COUNT, 5)


class PortfolioCapacityError(ValueError):
    """Raised when the requested quantity exceeds the supported capacity."""


@dataclass(frozen=True)
class PortfolioEvaluation:
    strategy: str
    requested_quantity: int
    generated_quantity: int
    unique_quantity: int
    number_exposure: tuple[int, ...]
    pair_overlap_mean: float
    pair_overlap_max: int
    best_hit_mean: float
    best_hit_histogram: dict[int, int]
    threshold_any_rates: dict[int, float]
    threshold_mean_winners: dict[int, float]
    jackpot_probability: float

    @property
    def exposure_min(self) -> int:
        return min(self.number_exposure) if self.number_exposure else 0

    @property
    def exposure_max(self) -> int:
        return max(self.number_exposure) if self.number_exposure else 0

    @property
    def exposure_stdev(self) -> float:
        return pstdev(self.number_exposure) if len(self.number_exposure) > 1 else 0.0


def _validate_ticket_size(ticket_size: int) -> int:
    if ticket_size < MIN_PORTFOLIO_TICKET_SIZE or ticket_size > MAX_PORTFOLIO_TICKET_SIZE:
        raise ValueError(
            f"ticket_size must be between {MIN_PORTFOLIO_TICKET_SIZE} and {MAX_PORTFOLIO_TICKET_SIZE}"
        )
    return ticket_size


def _portfolio_ticket_size(portfolio: tuple[Ticket, ...]) -> int:
    if not portfolio:
        raise ValueError("portfolio must not be empty")
    ticket_size = len(portfolio[0])
    if ticket_size < MIN_PORTFOLIO_TICKET_SIZE or ticket_size > MAX_PORTFOLIO_TICKET_SIZE:
        raise ValueError(
            f"portfolio tickets must contain between {MIN_PORTFOLIO_TICKET_SIZE} and {MAX_PORTFOLIO_TICKET_SIZE} numbers"
        )
    if any(len(ticket) != ticket_size for ticket in portfolio):
        raise ValueError("all tickets in a portfolio must have the same size")
    return ticket_size


def _maximum_unique_tickets(ticket_size: int) -> int:
    ticket_size = _validate_ticket_size(ticket_size)
    return comb(PORTFOLIO_NUMBER_COUNT, ticket_size)


def normalize_ticket(numbers: object, *, ticket_size: int | None = None) -> Ticket:
    try:
        values = [int(number) for number in numbers]  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError("ticket must be an iterable of integers") from exc
    if ticket_size is None:
        ticket_size = len(values)
    ticket_size = _validate_ticket_size(ticket_size)
    if len(values) != ticket_size:
        raise ValueError(f"ticket must contain exactly {ticket_size} numbers")
    ticket = tuple(sorted(values))
    if len(set(ticket)) != ticket_size:
        raise ValueError("ticket must not contain repeated numbers")
    if ticket[0] < 1 or ticket[-1] > PORTFOLIO_NUMBER_COUNT:
        raise ValueError("ticket numbers must be between 1 and 25")
    return ticket


def ticket_to_mask(ticket: Ticket) -> int:
    mask = 0
    for number in ticket:
        mask |= 1 << (number - 1)
    return mask


def draw_to_mask(draw: Ticket) -> int:
    return ticket_to_mask(draw)


def _draw_from_rng(rng: Random, ticket_size: int) -> Ticket:
    ticket_size = _validate_ticket_size(ticket_size)
    return tuple(sorted(rng.sample(range(1, PORTFOLIO_NUMBER_COUNT + 1), ticket_size)))


def _ticket_score(
    candidate: Ticket,
    number_counts: Counter[int],
    target_counts: dict[int, int],
    pair_counts: Counter[tuple[int, int]],
    *,
    pair_weight: float = 0.15,
) -> float:
    score = 0.0
    for number in candidate:
        before = number_counts.get(number, 0)
        after = before + 1
        target = target_counts[number]
        score += (after - target) ** 2 - (before - target) ** 2
    for pair in combinations(candidate, 2):
        score += pair_weight * pair_counts.get(pair, 0)
    return score


def build_baseline_groups(history: ValidatedHistory) -> tuple[tuple[int, int, int], ...]:
    frequencies = history.number_counter()
    ranked = sorted(
        frequencies.items(),
        key=lambda item: (-item[1], item[0]),
    )
    if len(ranked) < 24:
        raise ValueError("historical data must contain at least 24 distinct numbers")
    top_24 = [number for number, _ in ranked[:24]]
    groups = []
    for index in range(0, 24, BASELINE_GROUP_SIZE):
        group = tuple(sorted(top_24[index : index + BASELINE_GROUP_SIZE]))
        groups.append(group)
    return tuple(groups)


def _baseline_candidates(groups: tuple[tuple[int, int, int], ...]) -> list[Ticket]:
    candidates: list[Ticket] = []
    for group_selection in combinations(groups, 5):
        numbers: list[int] = []
        for group in group_selection:
            numbers.extend(group)
        candidates.append(tuple(sorted(numbers)))
    return candidates


def _baseline_candidates_wide(history: ValidatedHistory, ticket_size: int) -> list[Ticket]:
    frequencies = history.number_counter()
    ranked = sorted(
        frequencies.items(),
        key=lambda item: (-item[1], item[0]),
    )
    if len(ranked) < ticket_size:
        raise ValueError("historical data must contain enough distinct numbers")

    pool_size = min(PORTFOLIO_NUMBER_COUNT, ticket_size + 5)
    pool_numbers = [number for number, _ in ranked[:pool_size]]
    candidates = list(combinations(pool_numbers, ticket_size))
    return candidates


def generate_baseline_portfolio(
    history: ValidatedHistory,
    quantity: int,
    *,
    ticket_size: int = PORTFOLIO_TICKET_SIZE,
    seed: int | None = None,
    forbidden_tickets: set[Ticket] | None = None,
    strict_quantity: bool = False,
) -> tuple[Ticket, ...]:
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    ticket_size = _validate_ticket_size(ticket_size)

    forbidden = set(forbidden_tickets or set())
    rng = Random(seed)

    if ticket_size == PORTFOLIO_TICKET_SIZE:
        if quantity > BASELINE_PORTFOLIO_CAPACITY:
            if strict_quantity:
                raise PortfolioCapacityError(
                    f"baseline strategy supports at most {BASELINE_PORTFOLIO_CAPACITY} tickets"
                )
            quantity = BASELINE_PORTFOLIO_CAPACITY
        groups = build_baseline_groups(history)
        candidates = _baseline_candidates(groups)
        rng.shuffle(candidates)

        selected: list[Ticket] = []
        seen: set[Ticket] = set()
        for ticket in candidates:
            if ticket in forbidden or ticket in seen:
                continue
            selected.append(ticket)
            seen.add(ticket)
            if len(selected) >= quantity:
                break
        return tuple(selected)

    frequencies = history.number_counter()
    candidates = _baseline_candidates_wide(history, ticket_size)
    if quantity > len(candidates):
        if strict_quantity:
            raise PortfolioCapacityError(
                f"baseline strategy supports at most {len(candidates)} tickets for {ticket_size} numbers"
            )
        quantity = len(candidates)
    scored_candidates = [
        (sum(frequencies[number] for number in ticket), ticket)
        for ticket in candidates
    ]
    rng.shuffle(scored_candidates)
    scored_candidates.sort(key=lambda item: item[0], reverse=True)

    selected: list[Ticket] = []
    seen: set[Ticket] = set()
    for _, ticket in scored_candidates:
        if ticket in forbidden or ticket in seen:
            continue
        selected.append(ticket)
        seen.add(ticket)
        if len(selected) >= quantity:
            break
    return tuple(selected)


def generate_random_portfolio(
    quantity: int,
    *,
    ticket_size: int = PORTFOLIO_TICKET_SIZE,
    seed: int | None = None,
    forbidden_tickets: set[Ticket] | None = None,
    strict_quantity: bool = True,
) -> tuple[Ticket, ...]:
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    ticket_size = _validate_ticket_size(ticket_size)
    max_unique_tickets = _maximum_unique_tickets(ticket_size)
    if quantity > max_unique_tickets:
        if strict_quantity:
            raise PortfolioCapacityError(
                f"random strategy supports at most {max_unique_tickets} unique tickets"
            )
        quantity = max_unique_tickets

    forbidden = set(forbidden_tickets or set())
    rng = Random(seed)
    tickets: list[Ticket] = []
    seen: set[Ticket] = set()
    attempts = 0
    while len(tickets) < quantity:
        attempts += 1
        if attempts > quantity * 5000:
            raise RuntimeError("could not sample enough unique random tickets")
        ticket = _draw_from_rng(rng, ticket_size)
        if ticket in forbidden or ticket in seen:
            continue
        tickets.append(ticket)
        seen.add(ticket)
    return tuple(tickets)


def _weighted_candidate(
    rng: Random,
    number_counts: Counter[int],
    target_counts: dict[int, int],
    ticket_size: int,
) -> Ticket:
    available = list(range(1, PORTFOLIO_NUMBER_COUNT + 1))
    chosen: list[int] = []
    for _ in range(ticket_size):
        weights = [max(target_counts[number] - number_counts.get(number, 0), 1) for number in available]
        number = rng.choices(available, weights=weights, k=1)[0]
        chosen.append(number)
        index = available.index(number)
        del available[index]
    return tuple(sorted(chosen))


def generate_balanced_portfolio(
    quantity: int,
    *,
    ticket_size: int = PORTFOLIO_TICKET_SIZE,
    seed: int | None = None,
    forbidden_tickets: set[Ticket] | None = None,
    candidate_pool: int = 400,
    pair_weight: float = 0.15,
    strict_quantity: bool = True,
) -> tuple[Ticket, ...]:
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    ticket_size = _validate_ticket_size(ticket_size)
    max_unique_tickets = _maximum_unique_tickets(ticket_size)
    if quantity > max_unique_tickets:
        if strict_quantity:
            raise PortfolioCapacityError(
                f"balanced strategy supports at most {max_unique_tickets} unique tickets"
            )
        quantity = max_unique_tickets
    if candidate_pool <= 0:
        raise ValueError("candidate_pool must be positive")
    if pair_weight <= 0:
        raise ValueError("pair_weight must be positive")

    forbidden = set(forbidden_tickets or set())
    rng = Random(seed)
    target_base = (quantity * ticket_size) // PORTFOLIO_NUMBER_COUNT
    extra = (quantity * ticket_size) % PORTFOLIO_NUMBER_COUNT
    target_counts = {
        number: target_base + (1 if number <= extra else 0)
        for number in range(1, PORTFOLIO_NUMBER_COUNT + 1)
    }

    number_counts: Counter[int] = Counter()
    pair_counts: Counter[tuple[int, int]] = Counter()
    selected: list[Ticket] = []
    seen: set[Ticket] = set()

    while len(selected) < quantity:
        best_ticket: Ticket | None = None
        best_score = float("inf")
        for _ in range(candidate_pool):
            candidate = _weighted_candidate(rng, number_counts, target_counts, ticket_size)
            if candidate in forbidden or candidate in seen:
                continue
            score = _ticket_score(
                candidate,
                number_counts,
                target_counts,
                pair_counts,
                pair_weight=pair_weight,
            )
            if score < best_score:
                best_score = score
                best_ticket = candidate
        if best_ticket is None:
            candidate = _draw_from_rng(rng, ticket_size)
            if candidate in forbidden or candidate in seen:
                continue
            best_ticket = candidate

        selected.append(best_ticket)
        seen.add(best_ticket)
        for number in best_ticket:
            number_counts[number] += 1
        for pair in combinations(best_ticket, 2):
            pair_counts[pair] += 1

    return tuple(selected)


def evaluate_portfolio(
    portfolio: tuple[Ticket, ...],
    *,
    sample_draws: Iterable[Ticket],
) -> PortfolioEvaluation:
    _ = _portfolio_ticket_size(portfolio)
    ticket_masks = [ticket_to_mask(ticket) for ticket in portfolio]
    unique_quantity = len(set(portfolio))
    number_counts = Counter(number for ticket in portfolio for number in ticket)

    pair_intersections: list[int] = []
    for left_index, left_ticket in enumerate(portfolio):
        left_mask = ticket_masks[left_index]
        for right_mask in ticket_masks[left_index + 1 :]:
            pair_intersections.append((left_mask & right_mask).bit_count())

    thresholds = (11, 12, 13, 14, 15)
    any_rates = {threshold: 0 for threshold in thresholds}
    mean_winners = {threshold: 0 for threshold in thresholds}
    best_histogram: Counter[int] = Counter()
    best_hit_sum = 0.0
    sample_count = 0

    for draw in sample_draws:
        sample_count += 1
        draw_mask = draw_to_mask(draw)
        best_hit = 0
        winners_by_threshold = {threshold: 0 for threshold in thresholds}

        for ticket_mask in ticket_masks:
            hits = (ticket_mask & draw_mask).bit_count()
            if hits > best_hit:
                best_hit = hits
            for threshold in thresholds:
                if hits >= threshold:
                    winners_by_threshold[threshold] += 1

        best_histogram[best_hit] += 1
        best_hit_sum += best_hit
        for threshold in thresholds:
            if winners_by_threshold[threshold] > 0:
                any_rates[threshold] += 1
            mean_winners[threshold] += winners_by_threshold[threshold]

    if sample_count == 0:
        raise ValueError("sample_draws must contain at least one draw")

    return PortfolioEvaluation(
        strategy="custom",
        requested_quantity=len(portfolio),
        generated_quantity=len(portfolio),
        unique_quantity=unique_quantity,
        number_exposure=tuple(number_counts[number] for number in range(1, PORTFOLIO_NUMBER_COUNT + 1)),
        pair_overlap_mean=mean(pair_intersections) if pair_intersections else 0.0,
        pair_overlap_max=max(pair_intersections) if pair_intersections else 0,
        best_hit_mean=best_hit_sum / sample_count,
        best_hit_histogram=dict(sorted(best_histogram.items())),
        threshold_any_rates={threshold: any_rates[threshold] / sample_count for threshold in thresholds},
        threshold_mean_winners={threshold: mean_winners[threshold] / sample_count for threshold in thresholds},
        jackpot_probability=any_rates[15] / sample_count,
    )


def simulate_draws(quantity: int, *, seed: int | None = None) -> tuple[Ticket, ...]:
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    rng = Random(seed)
    return tuple(_draw_from_rng(rng, PORTFOLIO_TICKET_SIZE) for _ in range(quantity))


def compare_portfolios(
    portfolios: dict[str, tuple[Ticket, ...]],
    *,
    sample_draw_count: int = 5000,
    seed: int | None = None,
) -> dict[str, PortfolioEvaluation]:
    sample_draws = simulate_draws(sample_draw_count, seed=seed)
    evaluations: dict[str, PortfolioEvaluation] = {}
    for name, portfolio in portfolios.items():
        evaluation = evaluate_portfolio(portfolio, sample_draws=sample_draws)
        evaluations[name] = PortfolioEvaluation(
            strategy=name,
            requested_quantity=evaluation.requested_quantity,
            generated_quantity=evaluation.generated_quantity,
            unique_quantity=evaluation.unique_quantity,
            number_exposure=evaluation.number_exposure,
            pair_overlap_mean=evaluation.pair_overlap_mean,
            pair_overlap_max=evaluation.pair_overlap_max,
            best_hit_mean=evaluation.best_hit_mean,
            best_hit_histogram=evaluation.best_hit_histogram,
            threshold_any_rates=evaluation.threshold_any_rates,
            threshold_mean_winners=evaluation.threshold_mean_winners,
            jackpot_probability=evaluation.jackpot_probability,
        )
    return evaluations
