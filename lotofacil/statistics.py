from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import exp, lgamma, log, sqrt
from statistics import NormalDist
from typing import Iterable

from .data import DrawRecord
from .probability import DRAW_SIZE, TOTAL_NUMBERS


@dataclass(frozen=True)
class FrequencyEntry:
    number: int
    count: int
    expected: float
    proportion: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class ChiSquareResult:
    statistic: float
    degrees_of_freedom: int
    p_value: float


def count_number_frequencies(draws: Iterable[DrawRecord]) -> Counter[int]:
    return Counter(number for draw in draws for number in draw.numbers)


def wilson_interval(count: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("trials must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    phat = count / trials
    denom = 1.0 + z**2 / trials
    centre = (phat + z**2 / (2.0 * trials)) / denom
    margin = z * sqrt((phat * (1.0 - phat) / trials) + (z**2 / (4.0 * trials**2))) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _regularized_gamma_p(a: float, x: float, eps: float = 1e-14, max_iter: int = 1000) -> float:
    if x <= 0:
        return 0.0
    if x < a + 1.0:
        ap = a
        total = 1.0 / a
        delta = total
        for _ in range(max_iter):
            ap += 1.0
            delta *= x / ap
            total += delta
            if abs(delta) < abs(total) * eps:
                break
        return total * exp(-x + a * log(x) - lgamma(a))
    return 1.0 - _regularized_gamma_q(a, x, eps=eps, max_iter=max_iter)


def _regularized_gamma_q(a: float, x: float, eps: float = 1e-14, max_iter: int = 1000) -> float:
    if x <= 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _regularized_gamma_p(a, x, eps=eps, max_iter=max_iter)

    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, max_iter + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return exp(-x + a * log(x) - lgamma(a)) * h


def chi_square_p_value(statistic: float, degrees_of_freedom: int) -> float:
    if statistic <= 0:
        return 1.0
    if degrees_of_freedom <= 0:
        raise ValueError("degrees_of_freedom must be positive")
    return _regularized_gamma_q(degrees_of_freedom / 2.0, statistic / 2.0)


def chi_square_uniform_test(draws: Iterable[DrawRecord]) -> ChiSquareResult:
    draw_list = list(draws)
    if not draw_list:
        raise ValueError("draws must not be empty")

    counts = count_number_frequencies(draw_list)
    expected = len(draw_list) * DRAW_SIZE / TOTAL_NUMBERS
    statistic = sum(
        (counts.get(number, 0) - expected) ** 2 / expected
        for number in range(1, TOTAL_NUMBERS + 1)
    )
    degrees_of_freedom = TOTAL_NUMBERS - 1
    p_value = chi_square_p_value(statistic, degrees_of_freedom)
    return ChiSquareResult(
        statistic=statistic,
        degrees_of_freedom=degrees_of_freedom,
        p_value=p_value,
    )


def frequency_table(draws: Iterable[DrawRecord], confidence: float = 0.95) -> tuple[FrequencyEntry, ...]:
    draw_list = list(draws)
    if not draw_list:
        raise ValueError("draws must not be empty")

    counts = count_number_frequencies(draw_list)
    expected = len(draw_list) * DRAW_SIZE / TOTAL_NUMBERS
    rows: list[FrequencyEntry] = []
    for number in range(1, TOTAL_NUMBERS + 1):
        count = counts.get(number, 0)
        low, high = wilson_interval(count, len(draw_list), confidence=confidence)
        rows.append(
            FrequencyEntry(
                number=number,
                count=count,
                expected=expected,
                proportion=count / len(draw_list),
                ci_low=low,
                ci_high=high,
            )
        )
    return tuple(rows)


def bayesian_smoothed_probability(
    count: int,
    trials: int,
    *,
    prior_mean: float = 0.6,
    prior_strength: float = 25.0,
) -> float:
    if trials < 0:
        raise ValueError("trials must be non-negative")
    if not 0.0 <= prior_mean <= 1.0:
        raise ValueError("prior_mean must be between 0 and 1")
    if prior_strength <= 0:
        raise ValueError("prior_strength must be positive")
    prior_successes = prior_strength * prior_mean
    return (count + prior_successes) / (trials + prior_strength)


def cumulative_probability_model(
    draws: Iterable[DrawRecord],
    *,
    prior_mean: float = 0.6,
    prior_strength: float = 25.0,
) -> dict[int, float]:
    draw_list = list(draws)
    counts = count_number_frequencies(draw_list)
    return {
        number: bayesian_smoothed_probability(
            counts.get(number, 0),
            len(draw_list),
            prior_mean=prior_mean,
            prior_strength=prior_strength,
        )
        for number in range(1, TOTAL_NUMBERS + 1)
    }


def rolling_probability_model(
    draws: Iterable[DrawRecord],
    window: int,
    *,
    prior_mean: float = 0.6,
    prior_strength: float = 25.0,
) -> dict[int, float]:
    draw_list = list(draws)
    if window <= 0:
        raise ValueError("window must be positive")
    sample = draw_list[-window:]
    return cumulative_probability_model(
        sample,
        prior_mean=prior_mean,
        prior_strength=prior_strength,
    )


def exponentially_decayed_probability_model(
    draws: Iterable[DrawRecord],
    *,
    half_life: float = 100.0,
    prior_mean: float = 0.6,
    prior_strength: float = 25.0,
) -> dict[int, float]:
    draw_list = list(draws)
    if half_life <= 0:
        raise ValueError("half_life must be positive")

    weights = [0.5 ** ((len(draw_list) - 1 - index) / half_life) for index in range(len(draw_list))]
    weighted_counts = Counter()
    total_weight = 0.0
    for draw, weight in zip(draw_list, weights):
        total_weight += weight
        for number in draw.numbers:
            weighted_counts[number] += weight

    effective_trials = total_weight
    prior_successes = prior_strength * prior_mean
    return {
        number: (weighted_counts.get(number, 0.0) + prior_successes) / (effective_trials + prior_strength)
        for number in range(1, TOTAL_NUMBERS + 1)
    }

