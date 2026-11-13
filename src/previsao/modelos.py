"""
Modelos de previsão de demanda.

Implementa média móvel e suavização exponencial simples
para prever o consumo futuro de cada medicamento.

Nota: SES implementada manualmente para evitar dependência
externa de statsmodels no protótipo.
"""
import numpy as np
import pandas as pd

from src.config import JANELA_MEDIA_MOVEL, ALPHA_SUAVIZACAO, HORIZONTE_PREVISAO


def media_movel(serie: pd.Series, janela: int = JANELA_MEDIA_MOVEL,
                horizonte: int = HORIZONTE_PREVISAO) -> np.ndarray:
    """
    Previsão por média móvel simples.

    Usa os últimos `janela` valores para prever os próximos `horizonte` dias.
    A previsão é constante (repete a última média).
    """
    if len(serie) < janela:
        media = serie.mean()
    else:
        media = serie.iloc[-janela:].mean()
    return np.full(horizonte, media)


def suavizacao_exponencial(serie: pd.Series, alpha: float = ALPHA_SUAVIZACAO,
                           horizonte: int = HORIZONTE_PREVISAO) -> np.ndarray:
    """
    Previsão por suavização exponencial simples (SES).

    Implementação manual: s_t = alpha * y_t + (1 - alpha) * s_{t-1}
    A previsão para os próximos períodos é o último nível suavizado.
    """
    if len(serie) < 1:
        return np.full(horizonte, 0.0)

    valores = serie.values.astype(float)

    # Inicialização: primeiro valor da série
    nivel = valores[0]

    # Atualização recursiva
    for t in range(1, len(valores)):
        nivel = alpha * valores[t] + (1 - alpha) * nivel

    # Previsão: repete o último nível
    previsao = np.full(horizonte, max(nivel, 0.0))
    return previsao


def prever_demanda(consumo: pd.DataFrame,
                   horizonte: int = HORIZONTE_PREVISAO) -> pd.DataFrame:
    """
    Gera previsões para todos os medicamentos usando o melhor modelo.

    Utiliza a avaliação de modelos (do módulo avaliacao) para escolher
    o melhor por medicamento.

    Retorna DataFrame com: medicamento, dia (1..horizonte), previsao, modelo.
    """
    from src.previsao.avaliacao import escolher_melhor_modelo

    resultados = []
    for med in consumo["medicamento"].unique():
        serie = consumo[consumo["medicamento"] == med]["consumo"].reset_index(drop=True)
        melhor = escolher_melhor_modelo(serie)

        if melhor == "media_movel":
            prev = media_movel(serie, horizonte=horizonte)
        else:
            prev = suavizacao_exponencial(serie, horizonte=horizonte)

        for dia, valor in enumerate(prev, 1):
            resultados.append({
                "medicamento": med,
                "dia": dia,
                "previsao": round(float(valor), 2),
                "modelo": melhor,
            })

    return pd.DataFrame(resultados)
