"""
Regras de reposição de estoque.

Calcula ponto de pedido, estoque de segurança, quantidade sugerida
e dias de cobertura para cada medicamento.
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.config import (
    PRAZO_ENTREGA,
    NIVEL_SERVICO_Z,
    DIAS_COBERTURA_ALVO,
    ARQUIVO_SUGESTOES,
)


def calcular_estoque_seguranca(desvio_consumo: float, prazo_entrega: int) -> float:
    """
    Estoque de segurança = z * desvio_padrão * sqrt(prazo_entrega).

    Protege contra variação da demanda durante o lead time.
    """
    return NIVEL_SERVICO_Z * desvio_consumo * np.sqrt(prazo_entrega)


def calcular_ponto_pedido(consumo_medio: float, prazo_entrega: int,
                          estoque_seguranca: float) -> float:
    """
    Ponto de pedido = consumo_médio × prazo_entrega + estoque_segurança.

    Quando o estoque atinge esse nível, é hora de pedir.
    """
    return consumo_medio * prazo_entrega + estoque_seguranca


def calcular_quantidade_sugerida(consumo_medio: float,
                                 dias_cobertura: int = DIAS_COBERTURA_ALVO) -> float:
    """Quantidade sugerida para cobrir o período desejado."""
    return consumo_medio * dias_cobertura


def calcular_dias_cobertura(estoque_atual: float, consumo_medio: float) -> float:
    """Quantos dias o estoque atual cobre com o consumo previsto."""
    if consumo_medio <= 0:
        return float("inf")
    return estoque_atual / consumo_medio


def gerar_sugestoes(
    estoque: pd.DataFrame,
    consumo: pd.DataFrame,
    previsoes: pd.DataFrame,
) -> pd.DataFrame:
    """
    Gera sugestões de compra para cada medicamento.

    Retorna DataFrame com: medicamento, estoque_atual, consumo_medio,
    ponto_pedido, estoque_seguranca, dias_cobertura, qtd_sugerida,
    data_limite_pedido, precisa_comprar.
    """
    sugestoes = []
    hoje = datetime.now().date()

    for med in estoque["medicamento"].unique():
        est_atual = int(estoque[estoque["medicamento"] == med]["estoque_atual"].iloc[0])
        serie_consumo = consumo[consumo["medicamento"] == med]["consumo"]
        consumo_medio = float(serie_consumo.mean()) if len(serie_consumo) > 0 else 0
        desvio = float(serie_consumo.std()) if len(serie_consumo) > 1 else 0

        prazo = PRAZO_ENTREGA.get(med, 5)
        es = calcular_estoque_seguranca(desvio, prazo)
        pp = calcular_ponto_pedido(consumo_medio, prazo, es)
        dias_cob = calcular_dias_cobertura(est_atual, consumo_medio)
        qtd = calcular_quantidade_sugerida(consumo_medio)

        precisa = est_atual <= pp
        # Data limite: hoje + dias_cobertura - prazo_entrega
        dias_ate_pedido = max(0, int(dias_cob) - prazo)
        data_limite = hoje + timedelta(days=dias_ate_pedido)

        sugestoes.append({
            "medicamento": med,
            "estoque_atual": est_atual,
            "consumo_medio_dia": round(consumo_medio, 2),
            "desvio_consumo": round(desvio, 2),
            "estoque_seguranca": round(es, 1),
            "ponto_pedido": round(pp, 1),
            "dias_cobertura": round(dias_cob, 1),
            "qtd_sugerida": int(np.ceil(qtd)),
            "data_limite_pedido": str(data_limite),
            "precisa_comprar": precisa,
        })

    df = pd.DataFrame(sugestoes)

    ARQUIVO_SUGESTOES.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ARQUIVO_SUGESTOES, index=False)
    print(f"[OK] Sugestões de compra salvas em {ARQUIVO_SUGESTOES}")

    return df
