"""
Montagem do contexto estruturado para o Assistente LLM.

Reaproveita as tabelas ja calculadas pelo pipeline e exibidas no painel,
sem recalcular regras ou duplicar a logica de negocio.
"""
from datetime import datetime
from typing import Optional

import pandas as pd

from src.config import (
    DIR_PROCESSED,
    ARQUIVO_ESTOQUE,
    ARQUIVO_CONSUMO,
    ARQUIVO_PREVISOES,
    ARQUIVO_SUGESTOES,
)
from src.diferenciais.fefo import lotes_proximos_vencimento


def montar_contexto(
    estoque: Optional[pd.DataFrame] = None,
    sugestoes: Optional[pd.DataFrame] = None,
    saldo_lotes: Optional[pd.DataFrame] = None,
    anomalias: Optional[pd.DataFrame] = None,
    previsoes: Optional[pd.DataFrame] = None,
    consumo: Optional[pd.DataFrame] = None,
) -> str:
    """
    Gera um texto compacto em Markdown com os dados simulados do painel.

    Inclui:
    - Cabecalho com aviso de dados simulados e data de referencia
    - Estoque atual e dias de cobertura
    - Sugestoes de compra (medicamentos em alerta, quantidade e data limite)
    - Lotes proximos do vencimento (regra FEFO)
    - Anomalias recentes de consumo
    - Resumo da previsao de demanda para os proximos 14 dias
    """
    # Carregamento sob demanda se nao fornecido
    if estoque is None and ARQUIVO_ESTOQUE.exists():
        estoque = pd.read_csv(ARQUIVO_ESTOQUE)
    if sugestoes is None and ARQUIVO_SUGESTOES.exists():
        sugestoes = pd.read_csv(ARQUIVO_SUGESTOES)
    if saldo_lotes is None and (DIR_PROCESSED / "saldo_lotes.csv").exists():
        saldo_lotes = pd.read_csv(DIR_PROCESSED / "saldo_lotes.csv", parse_dates=["validade"])
    if anomalias is None and (DIR_PROCESSED / "anomalias.csv").exists():
        anomalias = pd.read_csv(DIR_PROCESSED / "anomalias.csv", parse_dates=["data"])
    if previsoes is None and ARQUIVO_PREVISOES.exists():
        previsoes = pd.read_csv(ARQUIVO_PREVISOES)
    if consumo is None and ARQUIVO_CONSUMO.exists():
        consumo = pd.read_csv(ARQUIVO_CONSUMO, parse_dates=["data"])

    # Determina data de referencia
    if consumo is not None and not consumo.empty and "data" in consumo.columns:
        data_ref = pd.to_datetime(consumo["data"]).max().strftime("%Y-%m-%d")
    else:
        data_ref = datetime.now().strftime("%Y-%m-%d")

    linhas = [
        "### CONTEXTO (dados de teste simulados)",
        f"Data de referencia: {data_ref}",
        "",
        "#### Estoque Atual e Cobertura",
    ]

    # 1. Estoque Atual e Cobertura
    if sugestoes is not None and not sugestoes.empty:
        for _, row in sugestoes.iterrows():
            med = row.get("medicamento", "Desconhecido")
            est = row.get("estoque_atual", 0)
            cob = row.get("dias_cobertura", 0.0)
            cons_med = row.get("consumo_medio_dia", 0.0)
            pp = row.get("ponto_pedido", 0)
            linhas.append(
                f"- {med}: Estoque {est} un | Cobertura {cob:.1f} dias | "
                f"Consumo medio {cons_med:.1f} un/dia | Ponto de pedido {pp:.0f} un"
            )
    elif estoque is not None and not estoque.empty:
        for _, row in estoque.iterrows():
            med = row.get("medicamento", "Desconhecido")
            est = row.get("estoque_atual", 0)
            linhas.append(f"- {med}: Estoque {est} un")
    else:
        linhas.append("- Dados de estoque nao disponiveis no momento.")

    # 2. Sugestoes de Compra
    linhas.extend(["", "#### Sugestoes de Compra"])
    if sugestoes is not None and not sugestoes.empty and "precisa_comprar" in sugestoes.columns:
        compras = sugestoes[sugestoes["precisa_comprar"]]
        if not compras.empty:
            for _, row in compras.iterrows():
                med = row.get("medicamento", "")
                qtd = row.get("qtd_sugerida", 0)
                limite = row.get("data_limite_pedido", "imediato")
                est = row.get("estoque_atual", 0)
                pp = row.get("ponto_pedido", 0)
                linhas.append(
                    f"- ALERTA DE COMPRA: {med} | Quantidade sugerida: {qtd} un | "
                    f"Data limite: {limite} | Estoque atual: {est} un (abaixo do ponto de pedido: {pp:.0f} un)"
                )
        else:
            linhas.append("- Nenhum medicamento precisa de compra imediata. Todos estao com estoque adequado.")
    else:
        linhas.append("- Sugestoes de compra nao disponiveis.")

    # 3. Lotes Proximos do Vencimento (FEFO)
    linhas.extend(["", "#### Lotes Proximos do Vencimento (Regra FEFO)"])
    if saldo_lotes is not None and not saldo_lotes.empty:
        try:
            proximos = lotes_proximos_vencimento(saldo_lotes)
        except Exception:
            proximos = pd.DataFrame()

        if not proximos.empty:
            for _, row in proximos.iterrows():
                med = row.get("medicamento", "")
                lote = row.get("lote", "")
                val = row.get("validade")
                val_str = pd.to_datetime(val).strftime("%Y-%m-%d") if pd.notna(val) else str(val)
                dias = row.get("dias_para_vencer", 0)
                saldo = row.get("saldo_lote", 0)
                linhas.append(
                    f"- ALERTA FEFO: {med} | Lote: {lote} | Validade: {val_str} | "
                    f"Vence em: {dias} dias | Saldo restante: {saldo} un"
                )
        else:
            linhas.append("- Nenhum lote com vencimento proximo nos proximos 30 dias.")
    else:
        linhas.append("- Informacoes de saldo por lote nao disponiveis.")

    # 4. Anomalias Recentes de Consumo
    linhas.extend(["", "#### Anomalias de Consumo Recentes"])
    if anomalias is not None and not anomalias.empty:
        anomalias_ordenadas = anomalias.sort_values(
            by=["data"] if "data" in anomalias.columns else anomalias.columns[0],
            ascending=False
        ).head(8)
        for _, row in anomalias_ordenadas.iterrows():
            dt = row.get("data")
            dt_str = pd.to_datetime(dt).strftime("%Y-%m-%d") if pd.notna(dt) else str(dt)
            med = row.get("medicamento", "")
            cons = row.get("consumo", 0)
            z = row.get("z_score", 0.0)
            tipo = row.get("tipo_anomalia", "anomalia")
            linhas.append(
                f"- {dt_str} | {med} | Consumo no dia: {cons} un | z-score: {z:.2f} ({tipo})"
            )
    else:
        linhas.append("- Nenhuma anomalia de consumo detectada no historico recente.")

    # 5. Previsao Resumida (Proximos 14 dias)
    linhas.extend(["", "#### Previsao Resumida (Proximos 14 dias)"])
    if previsoes is not None and not previsoes.empty:
        resumo_prev = (
            previsoes.groupby("medicamento")
            .agg(media_prev=("previsao", "mean"), modelo=("modelo", "first"))
            .reset_index()
        )
        for _, row in resumo_prev.iterrows():
            med = row["medicamento"]
            media = row["media_prev"]
            mod = row["modelo"]
            linhas.append(f"- {med}: Previsao media de {media:.1f} un/dia (modelo selecionado: {mod})")
    else:
        linhas.append("- Previsoes de demanda nao disponiveis.")

    return "\n".join(linhas)
