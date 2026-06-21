# Lotofacil

Ferramenta de análise e geração de carteiras para a Lotofácil.

O projeto está organizado como um pacote Python com:

- leitura e validação da planilha histórica;
- probabilidades exatas da Lotofácil;
- estratégia baseline baseada nas frequências atuais;
- gerador aleatório com semente;
- gerador balanceado por exposição;
- comparação entre estratégias;
- backtest walk-forward com janela de treino configurável;
- análise financeira com preço da aposta configurável, retorno esperado e risco;
- apostas oficiais de 15 a 20 números, conforme a CAIXA;
- exportação em CSV ou XLSX;
- testes automatizados.

## Requisitos

- Python 3.x
- `pandas`
- `openpyxl`

## Instalação

```bash
pip install -r requirements.txt
```

## Como usar

Se a planilha histórica estiver na raiz do projeto, o programa a encontra automaticamente.

```bash
python main.py --quantidade 56 --estrategia comparar --semente 42
```

Também funciona como módulo:

```bash
python -m lotofacil.cli --quantidade 56 --estrategia balanceada --semente 42
```

Para rodar o backtest walk-forward:

```bash
python main.py --backtest --quantidade 56 --estrategia comparar --janela 100 --backtest-max 250
```

Para ajustar a análise financeira:

```bash
python main.py --quantidade 56 --estrategia comparar --preco-aposta 3.50
```

Para escolher o tamanho da aposta oficial:

```bash
python main.py --quantidade 56 --estrategia comparar --numeros-aposta 20
```

## Estratégias disponíveis

- `baseline`: replica a estratégia atual como referência;
- `aleatoria`: gera apostas distintas de forma reprodutível;
- `balanceada`: tenta equilibrar a exposição dos números;
- `comparar`: executa as três estratégias e mostra um resumo lado a lado.

## Opções do CLI

- `--backtest`: ativa o backtest walk-forward.
- `--numeros-aposta`: define quantos números a aposta vai marcar, de 15 a 20.
- `--janela`: controla quantos concursos anteriores entram no treino em cada passo.
- `--backtest-max`: limita quantos concursos serão avaliados no backtest.
- `--preco-aposta`: define o custo unitário usado na análise financeira.
- `--saida` com extensão `.csv`: exporta o resumo em CSV.
- `--saida` com extensão `.xlsx`: exporta um workbook com abas de análise, histórico, prêmios, mercado, frequências, probabilidades, estratégias, financeiro e sensibilidade.

## Saída

O CLI mostra:

- resumo da validação da planilha;
- frequências históricas e teste qui-quadrado;
- probabilidades exatas da Lotofácil;
- tamanho da aposta selecionado e preço oficial correspondente;
- perfil de prêmios recente, custo da aposta e risco da carteira;
- resumo da carteira gerada;
- comparação estimada entre estratégias.

## Tamanhos oficiais de aposta

A CAIXA permite marcar entre 15 e 20 números no volante da Lotofácil. Os preços oficiais são:

- 15 números: R$ 3,50
- 16 números: R$ 56,00
- 17 números: R$ 476,00
- 18 números: R$ 2.856,00
- 19 números: R$ 13.566,00
- 20 números: R$ 54.264,00

Se você informar `--saida resumo.csv`, o resumo das estratégias é exportado em CSV.

Se você informar `--saida resumo.xlsx`, o projeto exporta um workbook com abas de análise, histórico, prêmios, mercado, frequências, probabilidades, estratégias, financeiro e sensibilidade.

## Observações

- A planilha histórica não deve ser versionada no Git.
- O filtro de sorteios passados não aumenta a chance matemática do próximo sorteio.
- Nenhuma estratégia garante prêmio.
