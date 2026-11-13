"""
Pipeline de tratamento de dados.

Transforma eventos brutos do cofre em:
- Estoque atual por medicamento (considerando entradas e retiradas)
- Série de consumo diário por medicamento
"""
import pandas as pd

from src.config import ARQUIVO_ESTOQUE, ARQUIVO_CONSUMO


def calcular_estoque_atual(eventos: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o estoque atual de cada medicamento.

    Soma as entradas e subtrai as retiradas para cada medicamento.
    Retorna DataFrame com colunas: medicamento, estoque_atual.
    """
    entradas = (
        eventos[eventos["tipo"] == "entrada"]
        .groupby("medicamento")["quantidade"]
        .sum()
    )
    retiradas = (
        eventos[eventos["tipo"] == "retirada"]
        .groupby("medicamento")["quantidade"]
        .sum()
    )
    estoque = (entradas.subtract(retiradas, fill_value=0)).reset_index()
    estoque.columns = ["medicamento", "estoque_atual"]
    estoque["estoque_atual"] = estoque["estoque_atual"].astype(int)
    return estoque


def calcular_consumo_diario(eventos: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o consumo diário por medicamento.

    Agrupa as retiradas por data e medicamento.
    Retorna DataFrame com colunas: data, medicamento, consumo.
    """
    retiradas = eventos[eventos["tipo"] == "retirada"].copy()
    retiradas["data"] = retiradas["timestamp"].dt.date

    consumo = (
        retiradas
        .groupby(["data", "medicamento"])["quantidade"]
        .sum()
        .reset_index()
    )
    consumo.columns = ["data", "medicamento", "consumo"]
    consumo["data"] = pd.to_datetime(consumo["data"])

    # Preenche dias sem consumo com zero para cada medicamento
    medicamentos = consumo["medicamento"].unique()
    datas = pd.date_range(consumo["data"].min(), consumo["data"].max())
    idx = pd.MultiIndex.from_product([datas, medicamentos], names=["data", "medicamento"])
    consumo = (
        consumo.set_index(["data", "medicamento"])
        .reindex(idx, fill_value=0)
        .reset_index()
    )
    return consumo


def executar_pipeline(eventos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Executa o pipeline completo de tratamento.

    Retorna (estoque_atual, consumo_diario) e salva em CSV.
    """
    estoque = calcular_estoque_atual(eventos)
    consumo = calcular_consumo_diario(eventos)

    # Salvar resultados
    ARQUIVO_ESTOQUE.parent.mkdir(parents=True, exist_ok=True)
    estoque.to_csv(ARQUIVO_ESTOQUE, index=False)
    consumo.to_csv(ARQUIVO_CONSUMO, index=False)

    print(f"[OK] Estoque atual salvo em {ARQUIVO_ESTOQUE}")
    print(f"[OK] Consumo diário salvo em {ARQUIVO_CONSUMO}")

    return estoque, consumo
