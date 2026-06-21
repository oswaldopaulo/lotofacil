from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import comb
from pathlib import Path
from random import Random
from statistics import mean, median, pvariance, pstdev

from .data import PRIZE_TIERS, PrizeRecord, ValidatedHistory
from .portfolio import Ticket, draw_to_mask, ticket_to_mask
from .probability import exact_match_probability, official_ticket_price, validate_bet_size

DEFAULT_TICKET_PRICE = 3.50
DEFAULT_RECENT_WINDOW = 100
DEFAULT_SIMULATION_COUNT = 10_000
OFFICIAL_FIXED_PAYOUTS = {
    11: 7.0,
    12: 14.0,
    13: 35.0,
}
PRIZE_TIER_INDEX = {tier: index for index, tier in enumerate(PRIZE_TIERS)}


@dataclass(frozen=True)
class PrizeTierProfile:
    tier: int
    fixed_payout: float | None
    sample_size: int
    positive_sample_size: int
    recent_sample_size: int
    historical_mean: float | None
    historical_median: float | None
    recent_mean: float | None
    recent_median: float | None
    historical_p25: float | None
    historical_p75: float | None
    recent_p25: float | None
    recent_p75: float | None
    estimated_payout: float


@dataclass(frozen=True)
class PrizeProfile:
    source_path: Path
    ticket_price: float
    recent_window: int
    tier_profiles: dict[int, PrizeTierProfile]

    def estimated_payout_for(self, tier: int) -> float:
        return self.tier_profiles[tier].estimated_payout


@dataclass(frozen=True)
class FinancialScenario:
    draw_mask: int
    payouts: tuple[float, ...]


@dataclass(frozen=True)
class PortfolioFinancialSummary:
    strategy: str
    requested_quantity: int
    unique_quantity: int
    ticket_size: int
    combination_count: int
    ticket_price: float
    total_cost: float
    estimated_gross_per_ticket: float
    estimated_net_per_ticket: float
    estimated_gross_return: float
    estimated_net_return: float
    expected_roi: float
    tier_probabilities: dict[int, float]
    tier_expected_gross: dict[int, float]
    simulated_mean_gross_return: float
    simulated_mean_net_return: float
    simulated_median_net_return: float
    variance_net_return: float
    std_dev_net_return: float
    probability_any_prize: float
    probability_full_loss: float
    probability_loss: float
    probability_break_even_or_better: float
    value_at_risk_95: float
    expected_shortfall_95: float
    simulations: int


def _positive_payouts(records: Sequence[PrizeRecord], tier: int) -> list[float]:
    index = PRIZE_TIER_INDEX[tier]
    values: list[float] = []
    for record in records:
        if index >= len(record.payouts):
            continue
        payout = record.payouts[index]
        if payout is None or payout <= 0:
            continue
        values.append(float(payout))
    return values


def _percentile(sorted_values: Sequence[float], percentile: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    if percentile <= 0:
        return float(sorted_values[0])
    if percentile >= 1:
        return float(sorted_values[-1])

    position = (len(sorted_values) - 1) * percentile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    if lower_index == upper_index:
        return float(sorted_values[lower_index])

    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    weight = position - lower_index
    return float(lower_value + (upper_value - lower_value) * weight)


def _mean_or_none(values: Sequence[float]) -> float | None:
    return float(mean(values)) if values else None


def _median_or_none(values: Sequence[float]) -> float | None:
    return float(median(values)) if values else None


def _portfolio_ticket_size(portfolio: tuple[Ticket, ...]) -> int:
    if not portfolio:
        raise ValueError("portfolio must not be empty")
    ticket_size = len(portfolio[0])
    validate_bet_size(ticket_size)
    if any(len(ticket) != ticket_size for ticket in portfolio):
        raise ValueError("all tickets in a portfolio must have the same size")
    return ticket_size


def _winning_combination_count(ticket_size: int, hits: int, tier: int) -> int:
    if hits < tier:
        return 0
    remaining_selected = ticket_size - hits
    remainder_needed = 15 - tier
    if remaining_selected < remainder_needed:
        return 0
    return comb(hits, tier) * comb(remaining_selected, remainder_needed)


def build_prize_profile(
    history: ValidatedHistory,
    *,
    ticket_price: float = DEFAULT_TICKET_PRICE,
    recent_window: int = DEFAULT_RECENT_WINDOW,
) -> PrizeProfile:
    if ticket_price <= 0:
        raise ValueError("ticket_price must be positive")
    if recent_window <= 0:
        raise ValueError("recent_window must be positive")

    prize_rows = list(history.prize_rows)
    recent_rows = prize_rows[-recent_window:] if recent_window < len(prize_rows) else prize_rows
    tier_profiles: dict[int, PrizeTierProfile] = {}

    for tier in PRIZE_TIERS:
        all_values = _positive_payouts(prize_rows, tier)
        recent_values = _positive_payouts(recent_rows, tier)
        fixed_payout = OFFICIAL_FIXED_PAYOUTS.get(tier)
        if fixed_payout is not None:
            estimated_payout = fixed_payout
        else:
            candidates = recent_values or all_values
            estimated_payout = float(median(candidates)) if candidates else 0.0

        sorted_all = sorted(all_values)
        sorted_recent = sorted(recent_values)
        tier_profiles[tier] = PrizeTierProfile(
            tier=tier,
            fixed_payout=fixed_payout,
            sample_size=len(prize_rows),
            positive_sample_size=len(all_values),
            recent_sample_size=len(recent_values),
            historical_mean=_mean_or_none(all_values),
            historical_median=_median_or_none(all_values),
            recent_mean=_mean_or_none(recent_values),
            recent_median=_median_or_none(recent_values),
            historical_p25=_percentile(sorted_all, 0.25),
            historical_p75=_percentile(sorted_all, 0.75),
            recent_p25=_percentile(sorted_recent, 0.25),
            recent_p75=_percentile(sorted_recent, 0.75),
            estimated_payout=estimated_payout,
        )

    return PrizeProfile(
        source_path=Path(history.source_path),
        ticket_price=ticket_price,
        recent_window=recent_window,
        tier_profiles=tier_profiles,
    )


def expected_ticket_gross_return(
    prize_profile: PrizeProfile,
    ticket_size: int,
) -> tuple[float, dict[int, float], dict[int, float], int]:
    ticket_size = validate_bet_size(ticket_size)
    combination_count = comb(ticket_size, 15)
    tier_probabilities = {
        tier: exact_match_probability(tier)
        for tier in PRIZE_TIERS
    }
    tier_expected_gross = {
        tier: combination_count * tier_probabilities[tier] * prize_profile.estimated_payout_for(tier)
        for tier in PRIZE_TIERS
    }
    estimated_gross_per_ticket = sum(tier_expected_gross.values())
    return estimated_gross_per_ticket, tier_probabilities, tier_expected_gross, combination_count


def build_financial_scenarios(
    history: ValidatedHistory,
    prize_profile: PrizeProfile,
    *,
    simulations: int = DEFAULT_SIMULATION_COUNT,
    seed: int | None = None,
) -> tuple[FinancialScenario, ...]:
    if simulations <= 0:
        raise ValueError("simulations must be positive")
    if not history.draws:
        raise ValueError("history must contain at least one draw")

    rng = Random(seed)
    draw_count = len(history.draws)
    prize_rows = list(history.prize_rows)
    scenarios: list[FinancialScenario] = []

    for _ in range(simulations):
        index = rng.randrange(draw_count)
        draw = history.draws[index]
        prize_row = prize_rows[index] if index < len(prize_rows) else None
        payouts = []
        for tier in PRIZE_TIERS:
            profile_value = prize_profile.estimated_payout_for(tier)
            payout = profile_value
            if prize_row is not None and PRIZE_TIER_INDEX[tier] < len(prize_row.payouts):
                observed = prize_row.payouts[PRIZE_TIER_INDEX[tier]]
                if observed is not None and observed > 0:
                    payout = float(observed)
            payouts.append(float(payout))
        scenarios.append(
            FinancialScenario(
                draw_mask=draw_to_mask(draw.numbers),
                payouts=tuple(payouts),
            )
        )

    return tuple(scenarios)


def analyze_portfolio_financials(
    portfolio: tuple[Ticket, ...],
    prize_profile: PrizeProfile,
    scenarios: Sequence[FinancialScenario],
    *,
    strategy: str = "custom",
) -> PortfolioFinancialSummary:
    if not portfolio:
        raise ValueError("portfolio must not be empty")
    if not scenarios:
        raise ValueError("scenarios must not be empty")

    ticket_size = _portfolio_ticket_size(portfolio)
    ticket_masks = [ticket_to_mask(ticket) for ticket in portfolio]
    requested_quantity = len(portfolio)
    unique_quantity = len(set(portfolio))
    total_cost = requested_quantity * prize_profile.ticket_price

    estimated_gross_per_ticket, tier_probabilities, tier_expected_gross, combination_count = expected_ticket_gross_return(
        prize_profile,
        ticket_size,
    )
    estimated_gross_return = estimated_gross_per_ticket * requested_quantity
    estimated_net_return = estimated_gross_return - total_cost
    estimated_net_per_ticket = estimated_gross_per_ticket - prize_profile.ticket_price
    expected_roi = (estimated_net_return / total_cost) if total_cost else 0.0

    gross_returns: list[float] = []
    net_returns: list[float] = []
    any_prize_count = 0
    full_loss_count = 0
    break_even_or_better_count = 0

    for scenario in scenarios:
        gross = 0.0
        for ticket_mask in ticket_masks:
            hits = (ticket_mask & scenario.draw_mask).bit_count()
            for tier in PRIZE_TIERS:
                count = _winning_combination_count(ticket_size, hits, tier)
                if count:
                    gross += count * scenario.payouts[PRIZE_TIER_INDEX[tier]]
        net = gross - total_cost
        gross_returns.append(gross)
        net_returns.append(net)
        if gross > 0:
            any_prize_count += 1
        if gross <= 0:
            full_loss_count += 1
        if net >= 0:
            break_even_or_better_count += 1

    sorted_net_returns = sorted(net_returns)
    var_95 = _percentile(sorted_net_returns, 0.05)
    if var_95 is None:
        var_95 = 0.0
    tail = [value for value in net_returns if value <= var_95]
    expected_shortfall_95 = float(mean(tail)) if tail else float(var_95)

    return PortfolioFinancialSummary(
        strategy=strategy,
        requested_quantity=requested_quantity,
        unique_quantity=unique_quantity,
        ticket_size=ticket_size,
        combination_count=combination_count,
        ticket_price=prize_profile.ticket_price,
        total_cost=total_cost,
        estimated_gross_per_ticket=estimated_gross_per_ticket,
        estimated_net_per_ticket=estimated_net_per_ticket,
        estimated_gross_return=estimated_gross_return,
        estimated_net_return=estimated_net_return,
        expected_roi=expected_roi,
        tier_probabilities=tier_probabilities,
        tier_expected_gross=tier_expected_gross,
        simulated_mean_gross_return=float(mean(gross_returns)),
        simulated_mean_net_return=float(mean(net_returns)),
        simulated_median_net_return=float(median(net_returns)),
        variance_net_return=float(pvariance(net_returns)),
        std_dev_net_return=float(pstdev(net_returns)),
        probability_any_prize=any_prize_count / len(scenarios),
        probability_full_loss=full_loss_count / len(scenarios),
        probability_loss=sum(1 for value in net_returns if value < 0) / len(scenarios),
        probability_break_even_or_better=break_even_or_better_count / len(scenarios),
        value_at_risk_95=float(var_95),
        expected_shortfall_95=expected_shortfall_95,
        simulations=len(scenarios),
    )


def compare_portfolios_financially(
    portfolios: dict[str, tuple[Ticket, ...]],
    history: ValidatedHistory,
    *,
    ticket_price: float | None = None,
    recent_window: int = DEFAULT_RECENT_WINDOW,
    simulations: int = DEFAULT_SIMULATION_COUNT,
    seed: int | None = None,
    prize_profile: PrizeProfile | None = None,
) -> tuple[PrizeProfile, dict[str, PortfolioFinancialSummary]]:
    reference_portfolio = next(iter(portfolios.values()), None)
    if reference_portfolio is None:
        raise ValueError("portfolios must not be empty")
    ticket_size = _portfolio_ticket_size(reference_portfolio)
    resolved_ticket_price = ticket_price if ticket_price is not None else official_ticket_price(ticket_size)
    profile = prize_profile or build_prize_profile(
        history,
        ticket_price=resolved_ticket_price,
        recent_window=recent_window,
    )
    scenarios = build_financial_scenarios(
        history,
        profile,
        simulations=simulations,
        seed=seed,
    )
    summaries = {
        name: analyze_portfolio_financials(portfolio, profile, scenarios, strategy=name)
        for name, portfolio in portfolios.items()
    }
    return profile, summaries
