from __future__ import annotations

from dataclasses import asdict
from math import comb
from pathlib import Path
from typing import Iterable

import pandas as pd

from .backtest import BacktestReport, BacktestRow
from .data import PRIZE_TIERS, PrizeRecord, ValidatedHistory, ValidationIssue
from .financial import PortfolioFinancialSummary, PrizeProfile, build_prize_profile
from .portfolio import PortfolioEvaluation, Ticket
from .probability import POSSIBLE_DRAW_COUNT, exact_match_distribution, exact_match_probability
from .statistics import ChiSquareResult, FrequencyEntry, chi_square_uniform_test, frequency_table


def validation_issues_frame(issues: Iterable[ValidationIssue]) -> pd.DataFrame:
    rows = [
        {
            "row_number": issue.row_number,
            "contest": issue.contest,
            "field": issue.field,
            "message": issue.message,
        }
        for issue in issues
    ]
    return pd.DataFrame(rows)


def frequency_frame(entries: Iterable[FrequencyEntry]) -> pd.DataFrame:
    rows = [asdict(entry) for entry in entries]
    return pd.DataFrame(rows)


def probability_frame() -> pd.DataFrame:
    rows = [
        {
            "hits": entry.hits,
            "probability": entry.probability,
            "percentage": entry.probability * 100.0,
        }
        for entry in exact_match_distribution()
    ]
    return pd.DataFrame(rows)


def analysis_summary_frame(history: ValidatedHistory) -> pd.DataFrame:
    chi_square = chi_square_uniform_test(history.draws)
    return pd.DataFrame(
        [
            {
                "source_path": str(history.source_path),
                "total_rows": history.total_rows,
                "valid_draws": len(history.draws),
                "prize_rows": len(history.prize_rows),
                "rejected_rows": len(history.rejected_rows),
                "warnings": len(history.warnings),
                "chi_square": chi_square.statistic,
                "degrees_of_freedom": chi_square.degrees_of_freedom,
                "p_value": chi_square.p_value,
                "expected_frequency_per_number": len(history.draws) * 15 / 25,
                "jackpot_probability_one_ticket": 1 / POSSIBLE_DRAW_COUNT,
                "jackpot_probability_56_tickets": 56 / POSSIBLE_DRAW_COUNT,
            }
        ]
    )


def portfolio_frame(portfolio: tuple[Ticket, ...]) -> pd.DataFrame:
    rows = []
    for index, ticket in enumerate(portfolio, start=1):
        rows.append(
            {
                "ticket": index,
                "numbers": " ".join(f"{number:02d}" for number in ticket),
            }
        )
    return pd.DataFrame(rows)


def portfolio_evaluation_frame(evaluation: PortfolioEvaluation) -> pd.DataFrame:
    rows = []
    for threshold in sorted(evaluation.threshold_any_rates):
        rows.append(
            {
                "strategy": evaluation.strategy,
                "threshold": threshold,
                "probability_any_ticket": evaluation.threshold_any_rates[threshold],
                "mean_winning_tickets": evaluation.threshold_mean_winners[threshold],
            }
        )
    return pd.DataFrame(rows)


def strategy_summary_frame(evaluations: dict[str, PortfolioEvaluation]) -> pd.DataFrame:
    rows = []
    for name, evaluation in evaluations.items():
        row = {
            "strategy": name,
            "requested_quantity": evaluation.requested_quantity,
            "generated_quantity": evaluation.generated_quantity,
            "unique_quantity": evaluation.unique_quantity,
            "jackpot_probability": evaluation.jackpot_probability,
            "best_hit_mean": evaluation.best_hit_mean,
            "pair_overlap_mean": evaluation.pair_overlap_mean,
            "pair_overlap_max": evaluation.pair_overlap_max,
            "exposure_min": evaluation.exposure_min,
            "exposure_max": evaluation.exposure_max,
            "exposure_stdev": evaluation.exposure_stdev,
        }
        for threshold in sorted(evaluation.threshold_any_rates):
            row[f"any_{threshold}"] = evaluation.threshold_any_rates[threshold]
            row[f"mean_winners_{threshold}"] = evaluation.threshold_mean_winners[threshold]
        rows.append(row)
    return pd.DataFrame(rows)


def validation_summary_frame(history: ValidatedHistory) -> pd.DataFrame:
    rows = [
        {
            "source_path": str(history.source_path),
            "total_rows": history.total_rows,
            "valid_draws": len(history.draws),
            "prize_rows": len(history.prize_rows),
            "rejected_rows": len(history.rejected_rows),
            "warnings": len(history.warnings),
        }
    ]
    return pd.DataFrame(rows)


def _format_currency(value: float | None) -> str:
    if value is None:
        return "-"
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2%}"


def _positive_values(records: Iterable[PrizeRecord], attr: str) -> list[float]:
    values: list[float] = []
    for record in records:
        value = getattr(record, attr)
        if value is None or value <= 0:
            continue
        values.append(float(value))
    return values


def prize_profile_frame(profile: PrizeProfile) -> pd.DataFrame:
    rows = []
    for tier in PRIZE_TIERS:
        tier_profile = profile.tier_profiles[tier]
        probability = exact_match_probability(tier)
        rows.append(
            {
                "tier": tier,
                "fixed_payout": tier_profile.fixed_payout,
                "estimated_payout": tier_profile.estimated_payout,
                "probability_exact_hit": probability,
                "expected_gross_per_ticket": probability * tier_profile.estimated_payout,
                "sample_size": tier_profile.sample_size,
                "positive_sample_size": tier_profile.positive_sample_size,
                "positive_share": (
                    tier_profile.positive_sample_size / tier_profile.sample_size
                    if tier_profile.sample_size
                    else 0.0
                ),
                "recent_sample_size": tier_profile.recent_sample_size,
                "historical_mean": tier_profile.historical_mean,
                "historical_median": tier_profile.historical_median,
                "historical_p25": tier_profile.historical_p25,
                "historical_p75": tier_profile.historical_p75,
                "recent_mean": tier_profile.recent_mean,
                "recent_median": tier_profile.recent_median,
                "recent_p25": tier_profile.recent_p25,
                "recent_p75": tier_profile.recent_p75,
            }
        )
    return pd.DataFrame(rows)


def prize_market_frame(history: ValidatedHistory, recent_window: int) -> pd.DataFrame:
    recent_rows = list(history.prize_rows[-recent_window:]) if recent_window > 0 else list(history.prize_rows)
    accumulated_values = _positive_values(recent_rows, "accumulated_prize")
    collection_values = _positive_values(recent_rows, "total_collection")
    estimated_values = _positive_values(recent_rows, "estimated_prize")
    last_record = recent_rows[-1] if recent_rows else None

    rows = [
        {
            "source_path": str(history.source_path),
            "recent_window": recent_window,
            "rows_considered": len(recent_rows),
            "latest_accumulated_prize": last_record.accumulated_prize if last_record else None,
            "latest_total_collection": last_record.total_collection if last_record else None,
            "latest_estimated_prize": last_record.estimated_prize if last_record else None,
            "accumulated_mean": sum(accumulated_values) / len(accumulated_values) if accumulated_values else None,
            "accumulated_median": (
                float(pd.Series(accumulated_values).median()) if accumulated_values else None
            ),
            "accumulated_p25": (
                float(pd.Series(accumulated_values).quantile(0.25)) if accumulated_values else None
            ),
            "accumulated_p75": (
                float(pd.Series(accumulated_values).quantile(0.75)) if accumulated_values else None
            ),
            "collection_mean": sum(collection_values) / len(collection_values) if collection_values else None,
            "collection_median": (
                float(pd.Series(collection_values).median()) if collection_values else None
            ),
            "collection_p25": (
                float(pd.Series(collection_values).quantile(0.25)) if collection_values else None
            ),
            "collection_p75": (
                float(pd.Series(collection_values).quantile(0.75)) if collection_values else None
            ),
            "estimated_mean": sum(estimated_values) / len(estimated_values) if estimated_values else None,
            "estimated_median": (
                float(pd.Series(estimated_values).median()) if estimated_values else None
            ),
            "estimated_p25": (
                float(pd.Series(estimated_values).quantile(0.25)) if estimated_values else None
            ),
            "estimated_p75": (
                float(pd.Series(estimated_values).quantile(0.75)) if estimated_values else None
            ),
        }
    ]
    return pd.DataFrame(rows)


def financial_summary_frame(summaries: dict[str, PortfolioFinancialSummary]) -> pd.DataFrame:
    rows = []
    for name, summary in summaries.items():
        row = {
            "strategy": name,
            "requested_quantity": summary.requested_quantity,
            "unique_quantity": summary.unique_quantity,
            "ticket_size": summary.ticket_size,
            "combination_count": summary.combination_count,
            "ticket_price": summary.ticket_price,
            "total_cost": summary.total_cost,
            "estimated_gross_per_ticket": summary.estimated_gross_per_ticket,
            "estimated_net_per_ticket": summary.estimated_net_per_ticket,
            "estimated_gross_return": summary.estimated_gross_return,
            "estimated_net_return": summary.estimated_net_return,
            "expected_roi": summary.expected_roi,
            "simulated_mean_gross_return": summary.simulated_mean_gross_return,
            "simulated_mean_net_return": summary.simulated_mean_net_return,
            "simulated_median_net_return": summary.simulated_median_net_return,
            "variance_net_return": summary.variance_net_return,
            "std_dev_net_return": summary.std_dev_net_return,
            "probability_any_prize": summary.probability_any_prize,
            "probability_full_loss": summary.probability_full_loss,
            "probability_loss": summary.probability_loss,
            "probability_break_even_or_better": summary.probability_break_even_or_better,
            "value_at_risk_95": summary.value_at_risk_95,
            "expected_shortfall_95": summary.expected_shortfall_95,
            "simulations": summary.simulations,
        }
        for tier in PRIZE_TIERS:
            row[f"probability_tier_{tier}"] = summary.tier_probabilities[tier]
            row[f"expected_gross_tier_{tier}"] = summary.tier_expected_gross[tier]
        rows.append(row)
    return pd.DataFrame(rows)


def financial_sensitivity_frame(
    profile: PrizeProfile,
    *,
    quantity: int = 1,
    ticket_size: int = 15,
) -> pd.DataFrame:
    combination_count = comb(ticket_size, 15) if 15 <= ticket_size <= 20 else 1
    tier_base = {tier: profile.tier_profiles[tier].estimated_payout for tier in PRIZE_TIERS}
    tier_pessimistic = tier_base.copy()
    tier_optimistic = tier_base.copy()

    for tier in (14, 15):
        tier_profile = profile.tier_profiles[tier]
        if tier_profile.recent_p25 is not None:
            tier_pessimistic[tier] = tier_profile.recent_p25
        if tier_profile.recent_p75 is not None:
            tier_optimistic[tier] = tier_profile.recent_p75

    scenarios = {
        "pessimista": tier_pessimistic,
        "base": tier_base,
        "otimista": tier_optimistic,
    }

    rows = []
    for label, payouts in scenarios.items():
        gross_per_ticket = sum(
            exact_match_probability(tier) * payouts[tier] * combination_count
            for tier in PRIZE_TIERS
        )
        net_per_ticket = gross_per_ticket - profile.ticket_price
        total_cost = profile.ticket_price * quantity
        gross_total = gross_per_ticket * quantity
        net_total = net_per_ticket * quantity
        rows.append(
            {
                "scenario": label,
                "quantity": quantity,
                "ticket_price": profile.ticket_price,
                "tier_14_payout": payouts[14],
                "tier_15_payout": payouts[15],
                "gross_per_ticket": gross_per_ticket,
                "net_per_ticket": net_per_ticket,
                "gross_total": gross_total,
                "net_total": net_total,
                "roi_total": (net_total / total_cost) if total_cost else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _resolve_xlsx_destination(path: str | Path, default_stem: str) -> Path:
    destination = Path(path)
    if destination.suffix.lower() == ".xlsx":
        return destination
    if destination.suffix:
        return destination.with_suffix(".xlsx")
    return destination / f"{default_stem}.xlsx"


def _safe_sheet_name(prefix: str, value: str) -> str:
    cleaned = "".join(character if character.isalnum() else "_" for character in value)
    sheet_name = f"{prefix}_{cleaned}" if prefix else cleaned
    sheet_name = sheet_name.strip("_")
    return sheet_name[:31] or "sheet"


def export_analysis_xlsx(
    path: str | Path,
    history: ValidatedHistory,
    evaluations: dict[str, PortfolioEvaluation],
    portfolios: dict[str, tuple[Ticket, ...]] | None = None,
    financial_summaries: dict[str, PortfolioFinancialSummary] | None = None,
    prize_profile: PrizeProfile | None = None,
) -> Path:
    destination = _resolve_xlsx_destination(path, "resumo")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        analysis_summary_frame(history).to_excel(writer, sheet_name="analise", index=False)
        validation_summary_frame(history).to_excel(writer, sheet_name="historico", index=False)
        if portfolios:
            first_portfolio = next(iter(portfolios.values()))
            ticket_size = len(first_portfolio[0]) if first_portfolio else 15
        elif financial_summaries:
            ticket_size = next(iter(financial_summaries.values())).ticket_size
        else:
            ticket_size = 15
        if prize_profile is not None:
            prize_market_frame(history, prize_profile.recent_window).to_excel(
                writer,
                sheet_name="mercado",
                index=False,
            )
            prize_profile_frame(prize_profile).to_excel(writer, sheet_name="premios", index=False)
        frequency_frame(frequency_table(history.draws)).to_excel(writer, sheet_name="frequencias", index=False)
        probability_frame().to_excel(writer, sheet_name="probabilidades", index=False)
        strategy_summary_frame(evaluations).to_excel(writer, sheet_name="estrategias", index=False)
        if financial_summaries is not None and prize_profile is not None:
            financial_summary_frame(financial_summaries).to_excel(writer, sheet_name="financeiro", index=False)
            financial_sensitivity_frame(
                prize_profile,
                quantity=next(iter(evaluations.values())).requested_quantity if evaluations else 1,
                ticket_size=ticket_size,
            ).to_excel(writer, sheet_name="sensibilidade", index=False)

        if history.rejected_rows:
            validation_issues_frame(history.rejected_rows).to_excel(writer, sheet_name="rejeicoes", index=False)

        if portfolios:
            for strategy_name, portfolio in portfolios.items():
                portfolio_frame(portfolio).to_excel(
                    writer,
                    sheet_name=_safe_sheet_name("apostas", strategy_name),
                    index=False,
                )

    return destination


def backtest_detail_frame(rows: Iterable[BacktestRow]) -> pd.DataFrame:
    return pd.DataFrame([asdict(row) for row in rows])


def backtest_summary_frame(report: BacktestReport) -> pd.DataFrame:
    rows = []
    for strategy, summary in report.summaries.items():
        row = {
            "strategy": strategy,
            "requested_quantity": summary.requested_quantity,
            "ticket_size": report.ticket_size,
            "evaluated_draws": summary.evaluated_draws,
            "skipped_draws": summary.skipped_draws,
            "average_training_draws": summary.average_training_draws,
            "mean_best_hit": summary.mean_best_hit,
            "jackpot_hits": summary.jackpot_hits,
            "jackpot_rate": summary.jackpot_rate,
        }
        for threshold in sorted(summary.threshold_any_rates):
            row[f"any_{threshold}"] = summary.threshold_any_rates[threshold]
            row[f"mean_winners_{threshold}"] = summary.threshold_mean_winners[threshold]
        rows.append(row)
    return pd.DataFrame(rows)


def format_history_summary(
    history: ValidatedHistory,
    *,
    chi_square: ChiSquareResult | None = None,
    frequencies: Iterable[FrequencyEntry] | None = None,
) -> str:
    lines = [
        f"Arquivo: {history.source_path}",
        f"Linhas totais: {history.total_rows}",
        f"Sorteios validos: {len(history.draws)}",
        f"Linhas com premios: {len(history.prize_rows)}",
        f"Linhas rejeitadas: {len(history.rejected_rows)}",
    ]
    if history.warnings:
        lines.append("Avisos:")
        lines.extend(f"  - {warning}" for warning in history.warnings)
    if chi_square is not None:
        lines.append(
            f"Chi-quadrado: {chi_square.statistic:.4f} "
            f"(df={chi_square.degrees_of_freedom}, p={chi_square.p_value:.6f})"
        )
    if frequencies is not None:
        top = sorted(frequencies, key=lambda entry: (-entry.count, entry.number))[:5]
        bottom = sorted(frequencies, key=lambda entry: (entry.count, entry.number))[:5]
        lines.append(
            "Top 5: "
            + ", ".join(f"{entry.number}={entry.count}" for entry in top)
        )
        lines.append(
            "Bottom 5: "
            + ", ".join(f"{entry.number}={entry.count}" for entry in bottom)
        )
    return "\n".join(lines)


def format_strategy_summary(name: str, evaluation: PortfolioEvaluation) -> str:
    lines = [
        f"Estrategia: {name}",
        f"Apostas geradas: {evaluation.generated_quantity}",
        f"Apostas unicas: {evaluation.unique_quantity}",
        f"Exposicao por numero: min={evaluation.exposure_min}, max={evaluation.exposure_max}, dp={evaluation.exposure_stdev:.2f}",
        f"Sobreposicao media entre pares: {evaluation.pair_overlap_mean:.2f}",
        f"Sobreposicao maxima entre pares: {evaluation.pair_overlap_max}",
        f"Probabilidade estimada de 15 acertos: {evaluation.jackpot_probability:.8f}",
        f"Media do melhor resultado: {evaluation.best_hit_mean:.3f}",
    ]
    for threshold in sorted(evaluation.threshold_any_rates):
        lines.append(
            f"  >= {threshold}: qualquer aposta={evaluation.threshold_any_rates[threshold]:.3%}, "
            f"media de apostas vencedoras={evaluation.threshold_mean_winners[threshold]:.3f}"
        )
    return "\n".join(lines)


def format_prize_profile_summary(profile: PrizeProfile) -> str:
    lines = [
        "Perfil de premios",
        f"Fonte: {profile.source_path}",
        f"Preço da aposta: {_format_currency(profile.ticket_price)}",
        f"Janela recente: {profile.recent_window}",
    ]
    for tier in PRIZE_TIERS:
        tier_profile = profile.tier_profiles[tier]
        lines.append(
            f"  {tier} acertos: estimado={_format_currency(tier_profile.estimated_payout)}, "
            f"amostra={tier_profile.positive_sample_size}/{tier_profile.sample_size}, "
            f"mediana recente={_format_currency(tier_profile.recent_median)}"
        )
    return "\n".join(lines)


def format_financial_summary(name: str, summary: PortfolioFinancialSummary) -> str:
    lines = [
        f"Analise financeira: {name}",
        f"  Apostas: {summary.requested_quantity} (unicas: {summary.unique_quantity})",
        f"  Tamanho da aposta: {summary.ticket_size} números ({summary.combination_count} combinações oficiais)",
        f"  Custo total: {_format_currency(summary.total_cost)}",
        f"  Esperado por aposta: bruto {_format_currency(summary.estimated_gross_per_ticket)}, "
        f"liquido {_format_currency(summary.estimated_net_per_ticket)}",
        f"  Esperado na carteira: bruto {_format_currency(summary.estimated_gross_return)}, "
        f"liquido {_format_currency(summary.estimated_net_return)}",
        f"  ROI esperado: {_format_percentage(summary.expected_roi)}",
        f"  Simulacao: media liquida {_format_currency(summary.simulated_mean_net_return)}, "
        f"mediana liquida {_format_currency(summary.simulated_median_net_return)}, "
        f"dp {_format_currency(summary.std_dev_net_return)}",
        f"  Risco: qualquer premio {_format_percentage(summary.probability_any_prize)}, "
        f"perda total {_format_percentage(summary.probability_full_loss)}, "
        f"prejuizo {_format_percentage(summary.probability_loss)}, "
        f"empate ou ganho {_format_percentage(summary.probability_break_even_or_better)}",
        f"  VaR 95%: {_format_currency(summary.value_at_risk_95)}, "
        f"ES 95%: {_format_currency(summary.expected_shortfall_95)}",
    ]
    return "\n".join(lines)


def format_backtest_summary(report: BacktestReport) -> str:
    lines = [
        "Backtest walk-forward",
        f"Arquivo: {report.source_path}",
        f"Quantidade por carteira: {report.quantity}",
        f"Tamanho da aposta: {report.ticket_size} números",
        f"Semente: {report.seed}",
        f"Janela historica: {report.window_size if report.window_size is not None else 'expansiva'}",
        f"Passo: {report.step}",
        f"Limite de concursos avaliados: {report.max_test_draws if report.max_test_draws is not None else 'todos'}",
    ]
    total_rows = len(report.rows)
    lines.append(f"Linhas avaliadas: {total_rows}")
    for name, summary in report.summaries.items():
        lines.append("")
        lines.append(f"Estrategia: {name}")
        lines.append(f"  Concursos avaliados: {summary.evaluated_draws}")
        lines.append(f"  Concursos ignorados: {summary.skipped_draws}")
        lines.append(f"  Media de concursos de treino: {summary.average_training_draws:.2f}")
        lines.append(f"  Media do melhor acerto: {summary.mean_best_hit:.3f}")
        lines.append(f"  Jackpot: {summary.jackpot_hits} ({summary.jackpot_rate:.3%})")
        if summary.best_hit_histogram:
            histogram = ", ".join(f"{hits}={count}" for hits, count in summary.best_hit_histogram.items())
            lines.append(f"  Histograma do melhor acerto: {histogram}")
        for threshold in sorted(summary.threshold_any_rates):
            lines.append(
                f"  >= {threshold}: qualquer aposta={summary.threshold_any_rates[threshold]:.3%}, "
                f"media de vencedoras={summary.threshold_mean_winners[threshold]:.3f}"
            )
    return "\n".join(lines)


def export_summary_csv(path: str | Path, evaluations: dict[str, PortfolioEvaluation]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    strategy_summary_frame(evaluations).to_csv(destination, index=False)
    return destination


def export_backtest_csv(path: str | Path, report: BacktestReport) -> tuple[Path, Path]:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.suffix.lower() == ".csv":
        summary_path = destination
        detail_path = destination.with_name(f"{destination.stem}_detalhe.csv")
    else:
        summary_path = destination / "backtest_resumo.csv"
        detail_path = destination / "backtest_detalhe.csv"

    backtest_summary_frame(report).to_csv(summary_path, index=False)
    backtest_detail_frame(report.rows).to_csv(detail_path, index=False)
    return summary_path, detail_path


def export_backtest_xlsx(path: str | Path, report: BacktestReport, history: ValidatedHistory) -> Path:
    destination = _resolve_xlsx_destination(path, "backtest")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        analysis_summary_frame(history).to_excel(writer, sheet_name="analise", index=False)
        validation_summary_frame(history).to_excel(writer, sheet_name="historico", index=False)
        prize_market_frame(history, recent_window=min(100, len(history.prize_rows) or 1)).to_excel(
            writer,
            sheet_name="mercado",
            index=False,
        )
        prize_profile_frame(
            build_prize_profile(
                history,
                recent_window=min(100, len(history.prize_rows) or 1),
            )
        ).to_excel(writer, sheet_name="premios", index=False)
        frequency_frame(frequency_table(history.draws)).to_excel(writer, sheet_name="frequencias", index=False)
        probability_frame().to_excel(writer, sheet_name="probabilidades", index=False)
        backtest_summary_frame(report).to_excel(writer, sheet_name="backtest_resumo", index=False)
        backtest_detail_frame(report.rows).to_excel(writer, sheet_name="backtest_detalhe", index=False)

        if history.rejected_rows:
            validation_issues_frame(history.rejected_rows).to_excel(writer, sheet_name="rejeicoes", index=False)

    return destination
