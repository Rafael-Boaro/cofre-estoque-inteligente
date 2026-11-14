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
    limite_anomalias: Optional[int] = None,
    limite_estoque: Optional[int] = None,
    limite_sugestoes: Optional[int] = None,
    limite_lotes: Optional[int] = None,
) -> str:
    """
    Gera um texto compacto em Markdown com os dados simulados do painel.

    Inclui:
    - Cabecalho com aviso de dados simulados e data de referencia
    - FATOS PRÉ-CALCULADOS em Python (rankings, maiores/menores picos, compras e validade)
    - Estoque atual e dias de cobertura
    - Sugestoes de compra (medicamentos em alerta, quantidade e data limite)
    - Lotes proximos do vencimento (regra FEFO)
    - Anomalias de consumo completas e ordenadas por z-score decrescente
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
        "#### FATOS PRÉ-CALCULADOS",
    ]

    # ── FATOS PRÉ-CALCULADOS (calculados em Python para evitar que o LLM ordene ou compare números) ──
    # A. Maior anomalia (maior z-score)
    anomalias_ordenadas = pd.DataFrame()
    if anomalias is not None and not anomalias.empty:
        col_sort = "z_score" if "z_score" in anomalias.columns else anomalias.columns[0]
        anomalias_ordenadas = anomalias.sort_values(by=col_sort, ascending=False).copy()
        primeira_anom = anomalias_ordenadas.iloc[0]
        med_z = primeira_anom.get("medicamento", "")
        dt_z = (
            pd.to_datetime(primeira_anom.get("data")).strftime("%Y-%m-%d")
            if pd.notna(primeira_anom.get("data"))
            else str(primeira_anom.get("data"))
        )
        z_val = float(primeira_anom.get("z_score", 0.0))
        cons_z = int(primeira_anom.get("consumo", 0))
        tipo_z = primeira_anom.get("tipo_anomalia", "pico")
        linhas.append(
            f"- Maior anomalia (maior z-score): {med_z} em {dt_z} (z-score: {z_val:.2f}, consumo: {cons_z} un, tipo: {tipo_z})"
        )
    else:
        linhas.append("- Maior anomalia (maior z-score): nenhuma anomalia registrada.")

    # B. Maior consumo diário
    if consumo is not None and not consumo.empty and "consumo" in consumo.columns:
        idx_max_c = consumo["consumo"].idxmax()
        row_max_c = consumo.loc[idx_max_c]
        med_c = row_max_c.get("medicamento", "")
        dt_c = (
            pd.to_datetime(row_max_c.get("data")).strftime("%Y-%m-%d")
            if pd.notna(row_max_c.get("data"))
            else str(row_max_c.get("data"))
        )
        qtd_c = int(row_max_c.get("consumo", 0))
        linhas.append(f"- Maior consumo diário registrado: {med_c} em {dt_c} ({qtd_c} un)")
    elif not anomalias_ordenadas.empty and "consumo" in anomalias_ordenadas.columns:
        row_max_c = anomalias_ordenadas.sort_values("consumo", ascending=False).iloc[0]
        med_c = row_max_c.get("medicamento", "")
        dt_c = (
            pd.to_datetime(row_max_c.get("data")).strftime("%Y-%m-%d")
            if pd.notna(row_max_c.get("data"))
            else str(row_max_c.get("data"))
        )
        qtd_c = int(row_max_c.get("consumo", 0))
        linhas.append(f"- Maior consumo diário registrado: {med_c} em {dt_c} ({qtd_c} un)")
    else:
        linhas.append("- Maior consumo diário registrado: dados não disponíveis.")

    # C. Top 5 anomalias por z-score
    if not anomalias_ordenadas.empty:
        top5 = anomalias_ordenadas.head(5)
        linhas.append("- Top 5 de anomalias por z-score:")
        for rank, (_, row) in enumerate(top5.iterrows(), 1):
            dt = row.get("data")
            dt_str = pd.to_datetime(dt).strftime("%Y-%m-%d") if pd.notna(dt) else str(dt)
            med = row.get("medicamento", "")
            cons = int(row.get("consumo", 0))
            z = float(row.get("z_score", 0.0))
            tipo = row.get("tipo_anomalia", "anomalia")
            linhas.append(f"  {rank}. {med} em {dt_str}: {cons} un, z-score {z:.2f} ({tipo})")
    else:
        linhas.append("- Top 5 de anomalias por z-score: nenhuma anomalia registrada.")

    # D. Medicamentos que precisam de compra agora
    if sugestoes is not None and not sugestoes.empty and "precisa_comprar" in sugestoes.columns:
        compras = sugestoes[sugestoes["precisa_comprar"]].copy()
        if not compras.empty:
            if "dias_cobertura" in compras.columns:
                compras = compras.sort_values("dias_cobertura")
            linhas.append(f"- Medicamentos que precisam de compra agora ({len(compras)} item(ns)):")
            for _, row in compras.iterrows():
                med = row.get("medicamento", "")
                qtd = int(row.get("qtd_sugerida", 0))
                limite = row.get("data_limite_pedido", "imediato")
                est = int(row.get("estoque_atual", 0))
                cob = float(row.get("dias_cobertura", 0.0))
                pp = float(row.get("ponto_pedido", 0.0))
                linhas.append(
                    f"  * {med}: comprar {qtd} un até {limite} (estoque atual: {est} un, ponto de pedido: {pp:.0f} un, cobertura: {cob:.1f} dias)"
                )
        else:
            linhas.append("- Medicamentos que precisam de compra agora: nenhum (todos com estoque adequado).")
    else:
        linhas.append("- Medicamentos que precisam de compra agora: dados não disponíveis.")

    # E. Lote com vencimento mais próximo
    lote_mais_prox = None
    if saldo_lotes is not None and not saldo_lotes.empty:
        col_saldo = "saldo_lote" if "saldo_lote" in saldo_lotes.columns else saldo_lotes.columns[-1]
        ativos = saldo_lotes[saldo_lotes[col_saldo] > 0].copy()
        if not ativos.empty and "validade" in ativos.columns:
            ativos["validade_dt"] = pd.to_datetime(ativos["validade"])
            ativos_ord = ativos.sort_values("validade_dt")
            lote_mais_prox = ativos_ord.iloc[0]
            med_l = lote_mais_prox.get("medicamento", "")
            cod_l = lote_mais_prox.get("lote", "")
            val_str = lote_mais_prox["validade_dt"].strftime("%Y-%m-%d")
            saldo_rem = int(lote_mais_prox.get(col_saldo, 0))
            hoje_dt = pd.Timestamp(datetime.now().date())
            dias_venc = int((lote_mais_prox["validade_dt"] - hoje_dt).days)
            linhas.append(
                f"- Lote com vencimento mais próximo: {med_l} | Lote: {cod_l} | "
                f"Validade: {val_str} (vence em {dias_venc} dias, saldo restante: {saldo_rem} un)"
            )
        else:
            linhas.append("- Lote com vencimento mais próximo: nenhum lote com saldo restante em estoque.")
    else:
        linhas.append("- Lote com vencimento mais próximo: dados de lotes não disponíveis.")

    # F. Medicamento com menor e maior cobertura em dias
    if sugestoes is not None and not sugestoes.empty and "dias_cobertura" in sugestoes.columns:
        sug_cob = sugestoes.sort_values("dias_cobertura")
        menor = sug_cob.iloc[0]
        maior = sug_cob.iloc[-1]
        med_menor = menor.get("medicamento", "")
        cob_menor = float(menor.get("dias_cobertura", 0.0))
        est_menor = int(menor.get("estoque_atual", 0))
        med_maior = maior.get("medicamento", "")
        cob_maior = float(maior.get("dias_cobertura", 0.0))
        est_maior = int(maior.get("estoque_atual", 0))
        linhas.append(f"- Menor cobertura em dias: {med_menor} ({cob_menor:.1f} dias, estoque atual: {est_menor} un)")
        linhas.append(f"- Maior cobertura em dias: {med_maior} ({cob_maior:.1f} dias, estoque atual: {est_maior} un)")
    else:
        linhas.append("- Cobertura de estoque: dados não disponíveis.")

    # ── 1. Estoque Atual e Cobertura ──────────────────────────────────────────
    linhas.extend(["", "#### Estoque Atual e Cobertura"])
    if sugestoes is not None and not sugestoes.empty:
        total_est = len(sugestoes)
        exibir_est = sugestoes
        if limite_estoque is not None and limite_estoque < total_est:
            exibir_est = sugestoes.head(limite_estoque)
            linhas.append(f"(mostrando os {limite_estoque} principais de {total_est})")
        for _, row in exibir_est.iterrows():
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
        total_est = len(estoque)
        exibir_est = estoque
        if limite_estoque is not None and limite_estoque < total_est:
            exibir_est = estoque.head(limite_estoque)
            linhas.append(f"(mostrando os {limite_estoque} principais de {total_est})")
        for _, row in exibir_est.iterrows():
            med = row.get("medicamento", "Desconhecido")
            est = row.get("estoque_atual", 0)
            linhas.append(f"- {med}: Estoque {est} un")
    else:
        linhas.append("- Dados de estoque nao disponiveis no momento.")

    # ── 2. Sugestoes de Compra ────────────────────────────────────────────────
    linhas.extend(["", "#### Sugestoes de Compra"])
    if sugestoes is not None and not sugestoes.empty and "precisa_comprar" in sugestoes.columns:
        compras = sugestoes[sugestoes["precisa_comprar"]]
        if not compras.empty:
            total_comp = len(compras)
            exibir_comp = compras
            if limite_sugestoes is not None and limite_sugestoes < total_comp:
                exibir_comp = compras.head(limite_sugestoes)
                linhas.append(f"(mostrando os {limite_sugestoes} principais de {total_comp})")
            for _, row in exibir_comp.iterrows():
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

    # ── 3. Lotes Proximos do Vencimento (FEFO) ────────────────────────────────
    linhas.extend(["", "#### Lotes Proximos do Vencimento (Regra FEFO)"])
    if saldo_lotes is not None and not saldo_lotes.empty:
        try:
            proximos = lotes_proximos_vencimento(saldo_lotes)
        except Exception:
            proximos = pd.DataFrame()

        if not proximos.empty:
            total_lotes = len(proximos)
            exibir_lotes = proximos
            if limite_lotes is not None and limite_lotes < total_lotes:
                exibir_lotes = proximos.head(limite_lotes)
                linhas.append(f"(mostrando os {limite_lotes} principais de {total_lotes})")
            for _, row in exibir_lotes.iterrows():
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

    # ── 4. Anomalias de Consumo (Ordenadas por z-score decrescente) ───────────
    linhas.extend(["", "#### Anomalias de Consumo (por z-score decrescente)"])
    if not anomalias_ordenadas.empty:
        total_anom = len(anomalias_ordenadas)
        if limite_anomalias is not None and limite_anomalias < total_anom:
            anomalias_exibidas = anomalias_ordenadas.head(limite_anomalias)
            linhas.append(f"(mostrando os {limite_anomalias} principais de {total_anom})")
        else:
            anomalias_exibidas = anomalias_ordenadas

        for _, row in anomalias_exibidas.iterrows():
            dt = row.get("data")
            dt_str = pd.to_datetime(dt).strftime("%Y-%m-%d") if pd.notna(dt) else str(dt)
            med = row.get("medicamento", "")
            cons = int(row.get("consumo", 0))
            z = float(row.get("z_score", 0.0))
            tipo = row.get("tipo_anomalia", "anomalia")
            linhas.append(
                f"- {dt_str} | {med} | Consumo no dia: {cons} un | z-score: {z:.2f} ({tipo})"
            )
    else:
        linhas.append("- Nenhuma anomalia de consumo detectada no historico recente.")

    # ── 5. Previsao Resumida (Proximos 14 dias) ───────────────────────────────
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
