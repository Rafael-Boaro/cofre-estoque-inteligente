"""
Lógica FEFO (First Expired, First Out) para lotes de medicamentos.

Identifica lotes próximos do vencimento e calcula o saldo
estimado por lote para priorizar a saída dos que vencem antes.
"""
from datetime import datetime, timedelta

import pandas as pd

from src.config import DIAS_ALERTA_VALIDADE


def calcular_saldo_por_lote(eventos: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o saldo estimado de cada lote (entradas - retiradas).

    Retorna DataFrame com: medicamento, lote, validade, saldo_lote.
    """
    entradas = (
        eventos[eventos["tipo"] == "entrada"]
        .groupby(["medicamento", "lote", "validade"])["quantidade"]
        .sum()
        .rename("entradas")
    )
    retiradas = (
        eventos[eventos["tipo"] == "retirada"]
        .groupby(["medicamento", "lote", "validade"])["quantidade"]
        .sum()
        .rename("retiradas")
    )

    saldo = pd.concat([entradas, retiradas], axis=1).fillna(0)
    saldo["saldo_lote"] = (saldo["entradas"] - saldo["retiradas"]).clip(lower=0).astype(int)
    saldo = saldo.reset_index()[["medicamento", "lote", "validade", "saldo_lote"]]
    saldo["validade"] = pd.to_datetime(saldo["validade"])
    return saldo


def ordenar_fefo(saldo_lotes: pd.DataFrame) -> pd.DataFrame:
    """
    Ordena lotes por validade (FEFO): primeiro a vencer sai primeiro.

    Retorna apenas lotes com saldo > 0.
    """
    ativos = saldo_lotes[saldo_lotes["saldo_lote"] > 0].copy()
    return ativos.sort_values(["medicamento", "validade"]).reset_index(drop=True)


def lotes_proximos_vencimento(
    saldo_lotes: pd.DataFrame,
    dias_alerta: int = DIAS_ALERTA_VALIDADE,
) -> pd.DataFrame:
    """
    Filtra lotes que vencem nos próximos `dias_alerta` dias.

    Adiciona coluna `dias_para_vencer`.
    """
    hoje = pd.Timestamp(datetime.now().date())
    limite = hoje + timedelta(days=dias_alerta)

    ativos = saldo_lotes[saldo_lotes["saldo_lote"] > 0].copy()
    ativos["dias_para_vencer"] = (ativos["validade"] - hoje).dt.days

    proximos = ativos[ativos["validade"] <= limite].copy()
    return proximos.sort_values(["dias_para_vencer", "medicamento"]).reset_index(drop=True)


def sugerir_ordem_saida(saldo_lotes: pd.DataFrame, medicamento: str) -> pd.DataFrame:
    """
    Retorna a ordem sugerida de saída para um medicamento (FEFO).

    O farmacêutico deve dispensar primeiro os lotes que aparecem no topo.
    """
    filtrado = saldo_lotes[
        (saldo_lotes["medicamento"] == medicamento) &
        (saldo_lotes["saldo_lote"] > 0)
    ].copy()
    return filtrado.sort_values("validade").reset_index(drop=True)
