"""
Avaliação e comparação de modelos de previsão.

Faz backtest simples (train/test split) e compara
média móvel vs. suavização exponencial usando MAE e MAPE.
"""
import numpy as np
import pandas as pd

from src.previsao.modelos import media_movel, suavizacao_exponencial
from src.config import JANELA_MEDIA_MOVEL


def _mae(real: np.ndarray, previsto: np.ndarray) -> float:
    """Erro absoluto médio."""
    return float(np.mean(np.abs(real - previsto)))


def _mape(real: np.ndarray, previsto: np.ndarray) -> float:
    """Erro percentual absoluto médio (evita divisão por zero)."""
    mascara = real > 0
    if mascara.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((real[mascara] - previsto[mascara]) / real[mascara])) * 100)


def backtest(serie: pd.Series, proporcao_treino: float = 0.8) -> dict:
    """
    Faz backtest de ambos os modelos na série.

    Divide em treino/teste, prevê o período de teste
    e retorna métricas de cada modelo.
    """
    n = len(serie)
    corte = int(n * proporcao_treino)

    if corte < JANELA_MEDIA_MOVEL or (n - corte) < 2:
        # Série muito curta para backtest confiável
        return {
            "media_movel": {"mae": float("inf"), "mape": float("inf")},
            "suavizacao_exponencial": {"mae": float("inf"), "mape": float("inf")},
        }

    treino = serie.iloc[:corte]
    teste = serie.iloc[corte:].values
    horizonte = len(teste)

    prev_mm = media_movel(treino, horizonte=horizonte)
    prev_ses = suavizacao_exponencial(treino, horizonte=horizonte)

    return {
        "media_movel": {
            "mae": _mae(teste, prev_mm),
            "mape": _mape(teste, prev_mm),
        },
        "suavizacao_exponencial": {
            "mae": _mae(teste, prev_ses),
            "mape": _mape(teste, prev_ses),
        },
    }


def escolher_melhor_modelo(serie: pd.Series) -> str:
    """
    Escolhe o modelo com menor MAE no backtest.

    Retorna 'media_movel' ou 'suavizacao_exponencial'.
    """
    resultados = backtest(serie)
    mae_mm = resultados["media_movel"]["mae"]
    mae_ses = resultados["suavizacao_exponencial"]["mae"]

    if mae_ses <= mae_mm:
        return "suavizacao_exponencial"
    return "media_movel"
