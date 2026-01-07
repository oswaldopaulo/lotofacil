# Gerador de Apostas Lotofácil

Este projeto é uma ferramenta de análise e geração de apostas para a Lotofácil, baseada em dados históricos de sorteios.

## Funcionalidades

*   **Análise Estatística:** Lê um arquivo Excel (`Lotofácil.xlsx`) contendo o histórico de sorteios e identifica os números mais e menos sorteados.
*   **Agrupamento Inteligente:** Seleciona os 24 números mais frequentes e os divide em 8 grupos de 3 números.
*   **Geração de Apostas:** Cria combinações de 5 grupos (15 números) para formar apostas.
*   **Filtro de Exclusividade:** Garante que as apostas geradas nunca tenham sido sorteadas anteriormente.
*   **Quantidade Personalizável:** O usuário define quantas apostas deseja gerar.
*   **Detalhamento:** Exibe quais grupos de números foram utilizados para compor cada aposta.

## Pré-requisitos

*   Python 3.x instalado.
*   Arquivo `Lotofácil.xlsx` na raiz do projeto com as colunas `Bola1` até `Bola15`.
    *   **Nota:** Este arquivo não está incluído no repositório por conter dados voláteis. Você deve obter uma versão atualizada (ex: no site da Caixa) e salvá-la na pasta raiz do projeto.

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

3.  O programa solicitará a quantidade de apostas desejada.
4.  Serão exibidas as estatísticas, os grupos formados e as apostas geradas com seus respectivos grupos.

## Créditos

Desenvolvido por: **oswaldo.paulo@gmail.com.br**
