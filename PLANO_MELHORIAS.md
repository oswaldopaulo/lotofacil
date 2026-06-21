# Plano de Melhorias — Gerador de Apostas Lotofácil

## 1. Objetivo

Evoluir o projeto para um gerador de carteiras de apostas:

- confiável na leitura e validação dos dados;
- estatisticamente auditável;
- capaz de comparar estratégias sem utilizar dados futuros;
- focado em diversificação e cobertura de resultados;
- reproduzível e coberto por testes automatizados.

O projeto não deve afirmar que frequências históricas aumentam a probabilidade de um sorteio futuro sem evidência fora da amostra. Em um sorteio uniforme e independente, todas as combinações de 15 números têm a mesma probabilidade de 15 acertos.

## 2. Diagnóstico de referência

- Base analisada: 3.716 concursos válidos.
- Espaço amostral: `C(25, 15) = 3.268.760` combinações.
- Uma aposta simples: chance de 15 acertos de `1 em 3.268.760`.
- 56 apostas distintas: chance de 15 acertos de aproximadamente `1 em 58.371`.
- A estratégia atual cria somente 56 combinações a partir de oito grupos fixos.
- Um número é totalmente excluído e os demais aparecem em 35 das 56 apostas.
- A elevada sobreposição entre apostas reduz a cobertura de resultados de 11 a 13 acertos.
- Frequências históricas apresentaram dispersão relevante, mas os testes sequenciais não demonstraram vantagem preditiva robusta.

## 3. Prioridades

### P0 — Integridade e arquitetura

#### 3.1 Separar responsabilidades

Dividir o código atual em componentes pequenos e testáveis:

```text
lotofacil/
├── __init__.py
├── data.py          # leitura e validação do histórico
├── statistics.py    # frequências, testes e backtests
├── probability.py   # probabilidades combinatórias
├── portfolio.py     # geração e otimização das apostas
├── reporting.py     # saída textual, CSV e Excel
└── cli.py           # interface de linha de comando
tests/
├── test_data.py
├── test_statistics.py
├── test_probability.py
└── test_portfolio.py
```

Critérios de aceitação:

- nenhuma função mistura entrada do usuário, cálculo e impressão;
- regras centrais podem ser chamadas sem interação pelo terminal;
- erros de dados geram mensagens específicas e acionáveis.

#### 3.2 Validar a planilha

Validar antes de calcular frequências:

- presença das colunas `Bola1` até `Bola15`;
- exatamente 15 números por concurso;
- valores inteiros entre 1 e 25;
- ausência de números repetidos no mesmo concurso;
- ausência de concursos e sorteios duplicados;
- validade e ordenação das datas;
- continuidade dos números dos concursos;
- relatório de linhas rejeitadas.

Critérios de aceitação:

- uma linha inválida nunca influencia as frequências;
- o programa informa concurso, coluna e motivo de cada rejeição;
- a base atual passa integralmente pela validação.

#### 3.3 Criar testes automatizados

Cobrir inicialmente:

- probabilidades conhecidas da Lotofácil;
- validação de valores ausentes, duplicados e fora da faixa;
- geração da quantidade solicitada de apostas distintas;
- impossibilidade de gerar apostas com menos ou mais de 15 números;
- reprodutibilidade com a mesma semente;
- cálculo de exposição e interseção entre apostas;
- limite e comportamento para solicitações acima da capacidade da estratégia.

Meta inicial: cobertura mínima de 80% sobre a lógica de domínio.

### P1 — Estatística e backtesting

#### 3.4 Implementar um modelo nulo

Usar o sorteio uniforme como referência obrigatória:

- probabilidade marginal esperada de cada número: `15/25 = 60%`;
- distribuição hipergeométrica dos acertos;
- probabilidades exatas de 11, 12, 13, 14 e 15 acertos;
- intervalos de confiança das frequências observadas;
- correção para múltiplas comparações ao analisar 25 números.

Toda estratégia deve ser comparada com esse modelo.

#### 3.5 Criar backtest walk-forward

Para cada concurso de teste:

1. utilizar somente concursos anteriores;
2. ajustar ou selecionar a estratégia;
3. gerar a carteira;
4. avaliar contra o concurso seguinte;
5. registrar acertos, cobertura, custo e premiações.

Comparar pelo menos:

- apostas aleatórias distintas;
- frequência histórica acumulada;
- frequência em janelas móveis de 100 e 300 concursos;
- frequência com decaimento temporal;
- estimativas bayesianas suavizadas em direção a 60%;
- carteira otimizada somente para diversificação.

Critérios de aceitação:

- nenhum dado futuro participa da geração;
- semente e parâmetros são registrados;
- resultados incluem intervalo de confiança;
- conclusões consideram múltiplos testes e diferentes períodos.

#### 3.6 Evitar sobreajuste

- separar períodos de desenvolvimento e validação final;
- não alterar a estratégia depois de observar o resultado da validação final;
- registrar previamente métricas e hipóteses;
- exigir repetição do resultado em períodos diferentes;
- não promover uma estratégia por um único valor de `p` abaixo de 5%.

### P1 — Otimização da carteira

#### 3.7 Remover os grupos fixos como estratégia principal

Manter a implementação atual apenas como estratégia de comparação. A nova estratégia deve permitir que todos os 25 números participem da carteira.

Para 56 apostas existem 840 posições numéricas. A exposição equilibrada ideal é:

```text
840 / 25 = 33,6 aparições por número
```

Logo, cada número deve aparecer preferencialmente 33 ou 34 vezes, salvo quando um modelo validado justificar outro peso.

#### 3.8 Criar função objetivo configurável

O otimizador deve considerar:

- equilíbrio da exposição individual;
- equilíbrio da exposição de pares e trincas;
- menor interseção excessiva entre apostas;
- maior número de resultados distintos cobertos para 11, 12 e 13 acertos;
- quantidade, custo e preferência de risco do usuário.

Exemplo conceitual:

```text
pontuação =
    peso_11 * cobertura_11
  + peso_12 * cobertura_12
  + peso_13 * cobertura_13
  - penalidade_exposição
  - penalidade_sobreposição
```

Implementações candidatas:

- seleção gulosa por ganho marginal de cobertura;
- busca local;
- simulated annealing;
- algoritmo genético;
- programação inteira, caso o custo computacional seja aceitável.

#### 3.9 Avaliar a carteira no espaço amostral

Para carteiras pequenas ou médias, enumerar as 3.268.760 combinações possíveis e calcular:

- probabilidade de pelo menos uma aposta com 11+ acertos;
- probabilidade de pelo menos uma aposta com 12+, 13+, 14+ e 15;
- quantidade esperada de apostas premiadas;
- distribuição do melhor resultado da carteira;
- exposição por número, par e trinca;
- histograma de interseções entre apostas.

Critérios de aceitação:

- a carteira otimizada não pode ter cobertura inferior à aleatória nas métricas selecionadas;
- a probabilidade de 15 acertos deve ser apresentada como função da quantidade de apostas distintas, sem atribuí-la à frequência histórica;
- a comparação deve usar o mesmo número de apostas e o mesmo custo.

### P2 — Reprodutibilidade e experiência de uso

#### 3.10 Adicionar interface de linha de comando

Parâmetros sugeridos:

```text
--arquivo
--quantidade
--estrategia
--semente
--janela
--peso-11
--peso-12
--peso-13
--saida
```

Exemplo:

```bash
python -m lotofacil.cli --quantidade 56 --estrategia cobertura --semente 42
```

#### 3.11 Gerar relatórios

Oferecer saída em terminal e CSV/Excel contendo:

- apostas geradas;
- estratégia e parâmetros;
- semente aleatória;
- exposição de cada número;
- interseção entre apostas;
- probabilidades da carteira;
- comparação com uma referência aleatória;
- concurso mais recente utilizado.

#### 3.12 Melhorar mensagens e documentação

- explicar que números atrasados não ficam mais prováveis;
- diferenciar probabilidade de jackpot de cobertura de prêmios menores;
- documentar que o filtro de resultados anteriores não melhora as chances;
- incluir exemplos reproduzíveis;
- alinhar o README com a saída real do programa.

### P3 — Valor esperado e atualização de dados

#### 3.13 Adicionar análise econômica

Permitir que o usuário informe o preço da aposta e estimar:

- custo total da carteira;
- retorno bruto histórico por faixa;
- valor esperado estimado;
- variância e risco de perda total;
- sensibilidade a prêmio acumulado e rateio.

Usar mediana e distribuição dos prêmios recentes, não apenas a média histórica, pois inflação, arrecadação e regras podem mudar.

#### 3.14 Automatizar atualização da base

- importar dados de fonte oficial;
- registrar data e origem da atualização;
- impedir regressão para uma base mais antiga;
- validar concursos novos antes de incorporá-los;
- manter a planilha fora do Git, mas documentar claramente como obtê-la.

## 4. Métricas de sucesso

O projeto será considerado melhorado quando:

- todos os testes passarem de forma automatizada;
- a mesma semente produzir exatamente a mesma carteira;
- bases inválidas forem rejeitadas antes da análise;
- a carteira tiver exposição próxima de 33/34 aparições por número em 56 jogos;
- a cobertura de 11–13 acertos superar consistentemente a estratégia atual;
- backtests não apresentarem vazamento de dados futuros;
- resultados estatísticos incluírem referência aleatória e incerteza;
- documentação não sugerir garantia ou vantagem não comprovada.

## 5. Ordem recomendada de execução

1. Criar validação da base e testes de integridade.
2. Separar a lógica em módulos e remover interação direta das funções centrais.
3. Implementar probabilidades exatas e métricas de carteira.
4. Reproduzir a estratégia atual como baseline testável.
5. Implementar gerador aleatório diversificado.
6. Criar otimizador de cobertura.
7. Implementar backtest walk-forward.
8. Adicionar CLI, relatórios e semente.
9. Adicionar análise econômica.
10. Automatizar atualização dos dados.

## 6. Primeiro marco sugerido

Entregar uma versão inicial contendo:

- carregamento e validação da planilha;
- probabilidades exatas;
- estratégia atual preservada como baseline;
- gerador aleatório com semente;
- gerador balanceado por exposição;
- comparação de cobertura entre as três estratégias;
- testes automatizados para os módulos principais.

Esse marco já permitirá demonstrar, de maneira reproduzível, a diferença entre selecionar números por frequência e construir uma carteira realmente diversificada.
