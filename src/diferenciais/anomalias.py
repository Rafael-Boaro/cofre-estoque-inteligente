"""
Detecção de anomalias no consumo de medicamentos.

Utiliza z-score para identificar dias com consumo fora do padrão,
indicando possíveis desvios, erros ou mudanças súbitas de demanda.
"""
import pandas as pd
import numpy as np


def detectar_anomalias_zscore(
    consumo: pd.DataFrame,
    limiar: float = 2.5,
) -> pd.DataFrame:
    """
    Detecta dias com consumo anômalo usando z-score.

    Para cada medicamento, calcula a média e desvio padrão do consumo
    e marca como anomalia os dias cujo z-score excede o limiar.

    Retorna DataFrame com: data, medicamento, consumo, z_score, tipo_anomalia.
    """
    anomalias = []

    for med in consumo["medicamento"].unique():
        serie = consumo[consumo["medicamento"] == med].copy()
        media = serie["consumo"].mean()
        desvio = serie["consumo"].std()

        if desvio == 0 or pd.isna(desvio):
            continue

        serie["z_score"] = (serie["consumo"] - media) / desvio
        serie["tipo_anomalia"] = serie["z_score"].apply(
            lambda z: "pico" if z > limiar else ("queda" if z < -limiar else None)
        )

        anormais = serie[serie["tipo_anomalia"].notna()].copy()
        if not anormais.empty:
            anormais = anormais[["data", "medicamento", "consumo", "z_score", "tipo_anomalia"]]
            anomalias.append(anormais)

    if not anomalias:
        return pd.DataFrame(columns=["data", "medicamento", "consumo", "z_score", "tipo_anomalia"])

    return pd.concat(anomalias, ignore_index=True)


def detectar_anomalias_iqr(
    consumo: pd.DataFrame,
    fator: float = 1.5,
) -> pd.DataFrame:
    """
    Detecta anomalias usando o método IQR (interquartil).

    Alternativa ao z-score, mais robusta a distribuições assimétricas.
    """
    anomalias = []

    for med in consumo["medicamento"].unique():
        serie = consumo[consumo["medicamento"] == med].copy()
        q1 = serie["consumo"].quantile(0.25)
        q3 = serie["consumo"].quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            continue

        limite_inf = q1 - fator * iqr
        limite_sup = q3 + fator * iqr

        serie["fora_do_padrao"] = (serie["consumo"] < limite_inf) | (serie["consumo"] > limite_sup)
        serie["z_score"] = (serie["consumo"] - serie["consumo"].mean()) / serie["consumo"].std()
        serie["tipo_anomalia"] = serie.apply(
            lambda r: "pico" if r["fora_do_padrao"] and r["consumo"] > limite_sup
            else ("queda" if r["fora_do_padrao"] and r["consumo"] < limite_inf else None),
            axis=1,
        )

        anormais = serie[serie["tipo_anomalia"].notna()].copy()
        if not anormais.empty:
            anormais = anormais[["data", "medicamento", "consumo", "z_score", "tipo_anomalia"]]
            anomalias.append(anormais)

    if not anomalias:
        return pd.DataFrame(columns=["data", "medicamento", "consumo", "z_score", "tipo_anomalia"])

    return pd.concat(anomalias, ignore_index=True)
