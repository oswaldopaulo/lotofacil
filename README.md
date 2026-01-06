# Gerador de Apostas Lotofácil

Este projeto é uma ferramenta de análise e geração de apostas para a Lotofácil, baseada em dados históricos de sorteios.

## Funcionalidades

*   **Análise Estatística:** Lê um arquivo Excel (`Lotofácil.xlsx`) contendo o histórico de sorteios e identifica os números mais e menos sorteados.
*   **Agrupamento Inteligente:** Seleciona os 24 números mais frequentes e os divide em 8 grupos de 3 números.
*   **Geração de Apostas:** Cria combinações de 5 grupos (15 números) para formar apostas.
*   **Filtro de Exclusividade:** Garante que as apostas geradas nunca tenham sido sorteadas anteriormente.
*   **Saída:** Gera uma lista de 21 sugestões de apostas otimizadas.

## Pré-requisitos

*   Python 3.x instalado.
*   Arquivo `Lotofácil.xlsx` na raiz do projeto com as colunas `Bola1` até `Bola15`.

## Instalação

1.  Clone ou baixe este repositório.
2.  Abra o terminal na pasta do projeto.
3.  Instale as dependências necessárias executando o seguinte comando:

```bash
pip install -r requirements.txt
```

## Como Usar

1.  Certifique-se de que o arquivo `Lotofácil.xlsx` está atualizado e presente na pasta do projeto.
2.  Execute o script principal:

```bash
python main.py
```

3.  O programa exibirá no console as estatísticas dos números e a lista de 21 apostas geradas.

## Créditos

Desenvolvido por: **oswaldo.paulo@gmail.com.br**
