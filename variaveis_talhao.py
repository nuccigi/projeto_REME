# variaveis_talhao.py
# Arquivo com os atributos fixos (proximidades e vegetação) de cada ponto/talhão.

import pandas as pd

# === Base dos talhões fornecida ===
dados_talhoes = {
    'Pontos': list(range(1, 101)),
    'Proximidade_Eletrica': [
        1 if i in [2, 3, 14, 15, 26, 27, 28, 36, 37, 45, 46, 58, 59, 64, 63, 66, 65, 69, 70, 80, 81, 77, 68, 75, 76, 74, 89, 91, 92, 90, 73] else 0 for i in range(1, 101)
    ],
    'Proximidade_Moradores': [
        1 if i in [2, 3, 14, 15] else 0 for i in range(1, 101)
    ],
    'Proximidade_Estrada_Municipal': [
        1 if i in [8, 9, 19, 20, 31, 32, 40, 42, 85, 86, 99, 100] else 0 for i in range(1, 101)
    ],
    'Barreira_Natural': [
        1 if i in [] else 0 for i in range(1, 101)
    ],
    'Plantio_Eucalipto': [
        1 if i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 24, 25, 27, 28, 29, 30, 31, 33, 34, 35, 36, 38, 39,
                     40, 41, 42, 43, 44, 45, 47, 48, 50, 52, 54, 56, 57, 58, 59, 62, 63, 64, 69, 72, 73, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 88, 91, 92, 93, 94, 95, 97, 98, 99] else 0 for i in range(1, 101)
    ],
    'Vegetacao_Nativa_Cerrado': [
        1 if i in [7, 17, 23, 41, 49, 26, 37, 46, 53, 51, 96, 67, 71, 74, 61, 66, 55] else 0 for i in range(1, 101)
    ],
    'Vegetacao_Area_Umida': [
        1 if i in [32, 60, 87, 89, 68, 90, 70, 65, 61, 34, 32] else 0 for i in range(1, 101)
    ],
    'Represas_Rios': [
        1 if i in [23, 32, 41, 51, 50, 60, 55, 61, 68, 67, 71, 87, 90, 74, 89, 81, 80, 70, 66, 65] else 0 for i in range(1, 101)
    ]
}

# === Conversão para o formato usado no app ===
# O app espera um dicionário onde cada ponto (ou "talhão") tem suas variáveis booleanas
variaveis_talhao = {}
for i, ponto in enumerate(dados_talhoes['Pontos']):
    variaveis_talhao[str(ponto)] = {
        "eucalipto": bool(dados_talhoes['Plantio_Eucalipto'][i]),
        "area_umida": bool(dados_talhoes['Vegetacao_Area_Umida'][i]),
        "represas_rios": bool(dados_talhoes['Represas_Rios'][i]),
        "estrada": bool(dados_talhoes['Proximidade_Estrada_Municipal'][i]),
        "eletrica": bool(dados_talhoes['Proximidade_Eletrica'][i]),
        "moradores": bool(dados_talhoes['Proximidade_Moradores'][i]),
        "cerrado": bool(dados_talhoes['Vegetacao_Nativa_Cerrado'][i]),
        # barreira natural não é usada nos pesos atuais, mas deixamos como referência
        "barreira_natural": bool(dados_talhoes['Barreira_Natural'][i])
    }

# Agora, 'variaveis_talhao' já está pronto para ser usado no cálculo AHP
