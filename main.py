import pandas as pd
from collections import Counter
from itertools import combinations
import random

def analyze_and_generate():
    file_path = 'Lotofácil.xlsx'
    
    try:
        # Carregar o arquivo Excel
        # Assume-se que as colunas são Bola1, Bola2, ... Bola15
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        print(f"Arquivo {file_path} não encontrado.")
        return
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        return

    # Identificar colunas das bolas
    ball_cols = [f'Bola{i}' for i in range(1, 16)]
    
    # Verificar se as colunas existem
    missing_cols = [col for col in ball_cols if col not in df.columns]
    if missing_cols:
        print(f"Colunas ausentes no arquivo: {missing_cols}")
        # Tentar encontrar colunas que pareçam ser as bolas se os nomes exatos não existirem?
        # Por enquanto, vamos abortar se não encontrar, ou o usuário pode ajustar.
        return

    all_numbers = []
    past_draws = set()

    # Coletar dados
    print("Analisando dados...")
    for index, row in df.iterrows():
        draw = []
        for col in ball_cols:
            val = row[col]
            # Garantir que é um número inteiro
            try:
                val = int(val)
                draw.append(val)
                all_numbers.append(val)
            except ValueError:
                continue
        
        if len(draw) == 15:
            past_draws.add(tuple(sorted(draw)))

    # 1. Analisar números mais e menos sorteados
    counter = Counter(all_numbers)
    most_common = counter.most_common()
    
    print("\n--- Estatísticas ---")
    print("Números mais sorteados (Top 5):")
    for num, count in most_common[:5]:
        print(f"Número {num}: {count} vezes")
        
    print("\nNúmeros menos sorteados (Bottom 5):")
    for num, count in most_common[-5:]:
        print(f"Número {num}: {count} vezes")

    # 2. Dividir os números em grupos de 3
    # A Lotofácil tem 25 números. Para criar grupos de 3, usamos 24 números.
    # Vamos usar os 24 números mais frequentes para formar os grupos.
    # O número menos frequente ficará de fora desta estratégia.
    
    top_24_numbers = [num for num, count in most_common[:24]]
    
    # Ordenar os números para facilitar a visualização ou manter a ordem de frequência?
    # Vamos misturar um pouco para criar grupos equilibrados ou sequenciais?
    # O pedido foi "Dividir os numeros em grupos de 3".
    # Vamos criar 8 grupos de 3 números.
    
    groups = []
    # Estratégia simples: agrupar sequencialmente da lista de frequência
    for i in range(0, 24, 3):
        group = tuple(sorted(top_24_numbers[i:i+3]))
        groups.append(group)
        
    print("\n--- Grupos Gerados (baseados nos 24 mais frequentes) ---")
    for i, g in enumerate(groups):
        print(f"Grupo {i+1}: {g}")

    # 3. Criar sequência de 21 apostas com 5 desses grupos
    # Combinações de 8 grupos tomados 5 a 5
    # Total de combinações possíveis: 8C5 = 56
    
    combs = list(combinations(groups, 5))
    random.shuffle(combs) # Embaralhar para variar as apostas geradas
    
    generated_bets = []
    
    print("\n--- Gerando Apostas ---")
    count = 0
    for comb in combs:
        if count >= 21:
            break
            
        # Formar a aposta
        bet_numbers = []
        for group in comb:
            bet_numbers.extend(group)
        
        bet_tuple = tuple(sorted(bet_numbers))
        
        # Verificar se já saiu em sorteios anteriores
        if bet_tuple in past_draws:
            continue
            
        # Verificar se já adicionamos esta aposta (embora combinations garanta unicidade de grupos, a ordem não importa)
        if bet_tuple not in generated_bets:
            generated_bets.append(bet_tuple)
            count += 1

    # Exibir as apostas
    print(f"Foram geradas {len(generated_bets)} apostas únicas (que nunca saíram antes):")
    for i, bet in enumerate(generated_bets, 1):
        print(f"Aposta {i:02d}: {bet}")

if __name__ == '__main__':
    analyze_and_generate()
