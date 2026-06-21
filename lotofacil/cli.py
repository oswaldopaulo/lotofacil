from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .backtest import walk_forward_backtest
from .data import HistoryValidationError, load_history
from .financial import build_prize_profile, compare_portfolios_financially
from .portfolio import (
    compare_portfolios,
    generate_baseline_portfolio,
    generate_balanced_portfolio,
    generate_random_portfolio,
)
from .probability import probability_at_least
from .reporting import (
    export_analysis_xlsx,
    export_backtest_csv,
    export_backtest_xlsx,
    export_summary_csv,
    format_backtest_summary,
    format_history_summary,
    format_financial_summary,
    format_prize_profile_summary,
    format_strategy_summary,
)
from .probability import (
    DEFAULT_BET_SIZE,
    MAX_BET_SIZE,
    MIN_BET_SIZE,
    official_ticket_price,
    ticket_size_to_jackpot_odds,
    ticket_size_to_jackpot_probability,
)
from .statistics import chi_square_uniform_test, frequency_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lotofacil",
        description="Analise historica e geracao de carteiras para a Lotofacil.",
    )
    parser.add_argument("--arquivo", default=None, help="Caminho da planilha .xlsx")
    parser.add_argument("--quantidade", type=int, default=56, help="Quantidade de apostas")
    parser.add_argument(
        "--estrategia",
        choices=("baseline", "aleatoria", "balanceada", "comparar"),
        default="comparar",
        help="Estrategia de geracao",
    )
    parser.add_argument(
        "--numeros-aposta",
        type=int,
        choices=tuple(range(MIN_BET_SIZE, MAX_BET_SIZE + 1)),
        default=DEFAULT_BET_SIZE,
        help="Quantidade de números por aposta (15 a 20)",
    )
    parser.add_argument("--semente", type=int, default=42, help="Semente aleatoria")
    parser.add_argument("--simulacoes", type=int, default=5000, help="Quantidade de sorteios simulados")
    parser.add_argument(
        "--preco-aposta",
        type=float,
        default=None,
        help="Preco por aposta usado na analise financeira (sobrescreve o valor oficial)",
    )
    parser.add_argument("--saida", default=None, help="Caminho para exportar resumo em CSV ou XLSX")
    parser.add_argument("--backtest", action="store_true", help="Executa backtest walk-forward")
    parser.add_argument("--backtest-max", type=int, default=250, help="Limite de concursos avaliados no backtest")
    parser.add_argument("--janela", type=int, default=100, help="Janela historica sugerida")
    parser.add_argument("--passo-backtest", type=int, default=1, help="Passo entre concursos no backtest")
    parser.add_argument("--peso-11", type=float, default=1.0, help="Peso para cobertura de 11 acertos")
    parser.add_argument("--peso-12", type=float, default=1.0, help="Peso para cobertura de 12 acertos")
    parser.add_argument("--peso-13", type=float, default=1.0, help="Peso para cobertura de 13 acertos")
    return parser


def _build_portfolios(history, quantity: int, ticket_size: int, seed: int, strategy: str, pair_weight: float):
    forbidden = history.ticket_set()
    if strategy == "baseline":
        return {
            "baseline": generate_baseline_portfolio(
                history,
                quantity,
                ticket_size=ticket_size,
                seed=seed,
                forbidden_tickets=forbidden,
            )
        }
    if strategy == "aleatoria":
        return {
            "aleatoria": generate_random_portfolio(
                quantity,
                ticket_size=ticket_size,
                seed=seed,
                forbidden_tickets=forbidden,
            )
        }
    if strategy == "balanceada":
        return {
            "balanceada": generate_balanced_portfolio(
                quantity,
                ticket_size=ticket_size,
                seed=seed,
                forbidden_tickets=forbidden,
                pair_weight=pair_weight,
            )
        }

    return {
        "baseline": generate_baseline_portfolio(
            history,
            quantity,
            ticket_size=ticket_size,
            seed=seed,
            forbidden_tickets=forbidden,
        ),
        "aleatoria": generate_random_portfolio(
            quantity,
            ticket_size=ticket_size,
            seed=seed + 1,
            forbidden_tickets=forbidden,
        ),
        "balanceada": generate_balanced_portfolio(
            quantity,
            ticket_size=ticket_size,
            seed=seed + 2,
            forbidden_tickets=forbidden,
            pair_weight=pair_weight,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        history = load_history(args.arquivo, strict=False)
    except (FileNotFoundError, HistoryValidationError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    frequencies = frequency_table(history.draws)
    chi_square = chi_square_uniform_test(history.draws)
    print(format_history_summary(history, chi_square=chi_square, frequencies=frequencies))
    ticket_size = args.numeros_aposta
    ticket_price = args.preco_aposta if args.preco_aposta is not None else official_ticket_price(ticket_size)
    print(f"Tamanho da aposta selecionado: {ticket_size} números")
    print(f"Preço usado na análise financeira: R$ {ticket_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    print(f"Probabilidade de 15 acertos em uma aposta de {ticket_size} números: {ticket_size_to_jackpot_probability(ticket_size):.10f}")
    print(f"Odds de 15 acertos em uma aposta de {ticket_size} números: {ticket_size_to_jackpot_odds(ticket_size):.2f} em 1")
    print(f"Probabilidade de pelo menos 11 acertos em uma aposta: {probability_at_least(11):.8f}")

    prize_profile = build_prize_profile(history, ticket_price=ticket_price)
    print()
    print(format_prize_profile_summary(prize_profile))

    pair_weight = 0.15 * max(0.25, (args.peso_11 + args.peso_12 + args.peso_13) / 3.0)
    if args.backtest:
        strategies = ("baseline", "aleatoria", "balanceada") if args.estrategia == "comparar" else (args.estrategia,)
        report = walk_forward_backtest(
            history,
            args.quantidade,
            ticket_size=ticket_size,
            seed=args.semente,
            window=args.janela,
            step=args.passo_backtest,
            strategies=strategies,
            pair_weight=pair_weight,
            max_test_draws=args.backtest_max if args.backtest_max > 0 else None,
        )
        print()
        print(format_backtest_summary(report))
        if args.saida:
            destination = Path(args.saida)
            if destination.suffix.lower() == ".xlsx":
                xlsx_path = export_backtest_xlsx(destination, report, history)
                print()
                print(f"Resumo exportado para {xlsx_path}")
            else:
                summary_path, detail_path = export_backtest_csv(destination, report)
                print()
                print(f"Resumo exportado para {summary_path}")
                print(f"Detalhe exportado para {detail_path}")
    else:
        portfolios = _build_portfolios(history, args.quantidade, ticket_size, args.semente, args.estrategia, pair_weight)
        evaluations = compare_portfolios(portfolios, sample_draw_count=args.simulacoes, seed=args.semente)
        prize_profile, financial_evaluations = compare_portfolios_financially(
            portfolios,
            history,
            ticket_price=ticket_price,
            simulations=args.simulacoes,
            seed=args.semente,
            prize_profile=prize_profile,
        )

        for name, evaluation in evaluations.items():
            print()
            print(format_strategy_summary(name, evaluation))
            if name in financial_evaluations:
                print()
                print(format_financial_summary(name, financial_evaluations[name]))

        if args.saida:
            destination = Path(args.saida)
            if destination.suffix.lower() == ".xlsx":
                xlsx_path = export_analysis_xlsx(
                    destination,
                    history,
                    evaluations,
                    portfolios,
                    financial_summaries=financial_evaluations,
                    prize_profile=prize_profile,
                )
                print()
                print(f"Resumo exportado para {xlsx_path}")
            elif destination.suffix.lower() == ".csv":
                export_summary_csv(destination, evaluations)
                print()
                print(f"Resumo exportado para {destination}")
            else:
                destination.mkdir(parents=True, exist_ok=True)
                export_summary_csv(destination / "resumo.csv", evaluations)
                print()
                print(f"Resumo exportado para {destination / 'resumo.csv'}")

    if history.rejected_rows:
        print()
        print("Linhas rejeitadas:")
        for issue in history.rejected_rows[:20]:
            print(
                f"- linha {issue.row_number}, concurso {issue.contest}, "
                f"{issue.field}: {issue.message}"
            )

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
