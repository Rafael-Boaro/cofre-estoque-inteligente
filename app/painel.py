#!/usr/bin/env python3
"""
Painel Streamlit — Estoque Inteligente do Cofre Refrigerado.

Tela única com: indicadores-chave, estoque atual, dias de cobertura,
sugestões de compra, lotes próximos do vencimento (FEFO),
gráficos de consumo e previsão, e alertas/anomalias.

Uso: streamlit run app/painel.py
"""
import sys
from pathlib import Path

# Garante import de 'src'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from src.config import DIR_PROCESSED, ARQUIVO_ESTOQUE, ARQUIVO_CONSUMO, ARQUIVO_PREVISOES, ARQUIVO_SUGESTOES

# Tenta usar plotly; fallback para matplotlib
try:
    import plotly.express as px
    import plotly.graph_objects as go
    USA_PLOTLY = True
except ImportError:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    USA_PLOTLY = False

st.set_page_config(
    page_title="Cofre Refrigerado — Estoque Inteligente",
    layout="wide",
)


@st.cache_data
def carregar_dados():
    """Carrega todos os CSVs gerados pelo pipeline."""
    estoque = pd.read_csv(ARQUIVO_ESTOQUE)
    consumo = pd.read_csv(ARQUIVO_CONSUMO, parse_dates=["data"])
    previsoes = pd.read_csv(ARQUIVO_PREVISOES)
    sugestoes = pd.read_csv(ARQUIVO_SUGESTOES)

    saldo_lotes_path = DIR_PROCESSED / "saldo_lotes.csv"
    saldo_lotes = pd.read_csv(saldo_lotes_path, parse_dates=["validade"]) if saldo_lotes_path.exists() else pd.DataFrame()

    anomalias_path = DIR_PROCESSED / "anomalias.csv"
    anomalias = pd.read_csv(anomalias_path, parse_dates=["data"]) if anomalias_path.exists() else pd.DataFrame()

    return estoque, consumo, previsoes, sugestoes, saldo_lotes, anomalias


def main():
    st.title("Cofre Refrigerado — Estoque Inteligente")
    st.caption("Controle de estoque, previsão de demanda e sugestões de reposição para medicamentos refrigerados de alto custo.")

    try:
        estoque, consumo, previsoes, sugestoes, saldo_lotes, anomalias = carregar_dados()
    except FileNotFoundError:
        st.error(
            "Dados não encontrados. Execute antes:\n\n"
            "```bash\npython scripts/gerar_dados.py\npython scripts/rodar_pipeline.py\n```"
        )
        return

    # ── KPIs no topo ──────────────────────────────────────
    st.markdown("---")
    precisam_comprar = sugestoes[sugestoes["precisa_comprar"]]
    total_medicamentos = len(estoque)
    total_estoque = int(estoque["estoque_atual"].sum())
    media_cobertura = sugestoes["dias_cobertura"].replace(float("inf"), None).mean()
    qtd_alerta = len(precisam_comprar)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total em Estoque", f"{total_estoque} un.")
    col2.metric("Medicamentos", total_medicamentos)
    col3.metric("Cobertura Média", f"{media_cobertura:.0f} dias" if pd.notna(media_cobertura) else "—")
    col4.metric("Alertas de Compra", qtd_alerta, delta=f"-{qtd_alerta}" if qtd_alerta > 0 else None, delta_color="inverse")

    st.markdown("---")

    # ── Estoque Atual + Dias de Cobertura ─────────────────
    st.subheader("Estoque Atual e Dias de Cobertura")

    col_est, col_cob = st.columns(2)

    with col_est:
        if USA_PLOTLY:
            fig_est = px.bar(
                estoque.sort_values("estoque_atual"),
                x="estoque_atual",
                y="medicamento",
                orientation="h",
                title="Estoque Atual (unidades)",
                color="estoque_atual",
                color_continuous_scale="RdYlGn",
            )
            fig_est.update_layout(showlegend=False, coloraxis_showscale=False, height=350)
            st.plotly_chart(fig_est, use_container_width=True)
        else:
            fig, ax = plt.subplots(figsize=(6, 3.5))
            dados = estoque.sort_values("estoque_atual")
            colors = plt.cm.RdYlGn(dados["estoque_atual"] / dados["estoque_atual"].max())
            ax.barh(dados["medicamento"], dados["estoque_atual"], color=colors)
            ax.set_xlabel("Unidades")
            ax.set_title("Estoque Atual (unidades)")
            plt.tight_layout()
            st.pyplot(fig)

    with col_cob:
        sug_plot = sugestoes.copy()
        sug_plot["dias_cobertura_plot"] = sug_plot["dias_cobertura"].clip(upper=60)
        sug_plot["cor"] = sug_plot["precisa_comprar"].map({True: "Comprar", False: "OK"})

        if USA_PLOTLY:
            fig_cob = px.bar(
                sug_plot.sort_values("dias_cobertura_plot"),
                x="dias_cobertura_plot",
                y="medicamento",
                orientation="h",
                title="Dias de Cobertura",
                color="cor",
                color_discrete_map={"Comprar": "#EF553B", "OK": "#00CC96"},
            )
            fig_cob.update_layout(xaxis_title="Dias", legend_title="Status", height=350)
            st.plotly_chart(fig_cob, use_container_width=True)
        else:
            fig, ax = plt.subplots(figsize=(6, 3.5))
            dados = sug_plot.sort_values("dias_cobertura_plot")
            cores = ["#EF553B" if c else "#00CC96" for c in dados["precisa_comprar"]]
            ax.barh(dados["medicamento"], dados["dias_cobertura_plot"], color=cores)
            ax.set_xlabel("Dias")
            ax.set_title("Dias de Cobertura")
            plt.tight_layout()
            st.pyplot(fig)

    # ── Sugestões de Compra ────────────────────────────────
    st.subheader("Sugestões de Compra")
    if not precisam_comprar.empty:
        st.dataframe(
            precisam_comprar[[
                "medicamento", "estoque_atual", "consumo_medio_dia",
                "ponto_pedido", "dias_cobertura", "qtd_sugerida", "data_limite_pedido"
            ]].style.format({
                "consumo_medio_dia": "{:.1f}",
                "ponto_pedido": "{:.0f}",
                "dias_cobertura": "{:.1f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("Todos os medicamentos com estoque adequado!")

    # ── FEFO — Lotes próximos do vencimento ────────────────
    st.subheader("Lotes Próximos do Vencimento (FEFO)")
    if not saldo_lotes.empty:
        from src.diferenciais.fefo import lotes_proximos_vencimento
        proximos = lotes_proximos_vencimento(saldo_lotes)
        if not proximos.empty:
            st.warning(f"Atenção: {len(proximos)} lote(s) com vencimento nos próximos 30 dias")
            proximos_display = proximos.copy()
            proximos_display["validade"] = proximos_display["validade"].dt.strftime("%d/%m/%Y")
            st.dataframe(
                proximos_display[["medicamento", "lote", "validade", "dias_para_vencer", "saldo_lote"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("Nenhum lote com vencimento próximo.")
    else:
        st.info("Dados de lotes não disponíveis.")

    st.markdown("---")

    # ── Consumo Histórico e Previsão ───────────────────────
    st.subheader("Consumo Histórico e Previsão")

    medicamento_sel = st.selectbox(
        "Selecione o medicamento:",
        sorted(consumo["medicamento"].unique()),
    )

    serie_med = consumo[consumo["medicamento"] == medicamento_sel].copy()
    prev_med = previsoes[previsoes["medicamento"] == medicamento_sel].copy()

    # Montar datas de previsão
    ultima_data = serie_med["data"].max()
    prev_med["data"] = [ultima_data + pd.Timedelta(days=d) for d in prev_med["dia"]]

    if USA_PLOTLY:
        fig_serie = go.Figure()
        fig_serie.add_trace(go.Scatter(
            x=serie_med["data"], y=serie_med["consumo"],
            mode="lines", name="Consumo real",
            line=dict(color="#636EFA"),
        ))
        fig_serie.add_trace(go.Scatter(
            x=prev_med["data"], y=prev_med["previsao"],
            mode="lines+markers",
            name=f"Previsão ({prev_med['modelo'].iloc[0] if len(prev_med) > 0 else '?'})",
            line=dict(color="#EF553B", dash="dash"),
        ))
        if not anomalias.empty:
            anom_med = anomalias[anomalias["medicamento"] == medicamento_sel]
            if not anom_med.empty:
                fig_serie.add_trace(go.Scatter(
                    x=anom_med["data"], y=anom_med["consumo"],
                    mode="markers", name="Anomalia",
                    marker=dict(color="red", size=10, symbol="x"),
                ))
        fig_serie.update_layout(
            title=f"Consumo e Previsão — {medicamento_sel}",
            xaxis_title="Data", yaxis_title="Unidades / dia", height=400,
        )
        st.plotly_chart(fig_serie, use_container_width=True)
    else:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(serie_med["data"], serie_med["consumo"], label="Consumo real", color="#636EFA")
        modelo_nome = prev_med["modelo"].iloc[0] if len(prev_med) > 0 else "?"
        ax.plot(prev_med["data"], prev_med["previsao"], "--", label=f"Previsão ({modelo_nome})", color="#EF553B")
        if not anomalias.empty:
            anom_med = anomalias[anomalias["medicamento"] == medicamento_sel]
            if not anom_med.empty:
                ax.scatter(anom_med["data"], anom_med["consumo"], color="red", marker="x", s=80, label="Anomalia", zorder=5)
        ax.set_title(f"Consumo e Previsão — {medicamento_sel}")
        ax.set_xlabel("Data")
        ax.set_ylabel("Unidades / dia")
        ax.legend()
        plt.tight_layout()
        st.pyplot(fig)

    # ── Anomalias detectadas ───────────────────────────────
    st.subheader("Anomalias Detectadas")
    if not anomalias.empty:
        st.dataframe(
            anomalias.sort_values("z_score", ascending=False).style.format({
                "z_score": "{:.2f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("Nenhuma anomalia detectada no período.")

    # ── Tabela completa de estoque ─────────────────────────
    st.subheader("Visão Geral Completa")
    st.dataframe(
        sugestoes.style.format({
            "consumo_medio_dia": "{:.1f}",
            "desvio_consumo": "{:.1f}",
            "estoque_seguranca": "{:.0f}",
            "ponto_pedido": "{:.0f}",
            "dias_cobertura": "{:.1f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # ── Assistente do estoque ──────────────────────────────
    st.markdown("---")
    st.subheader("Assistente do estoque")
    st.caption("Assistente com dados de teste. Ele explica os números do painel e não substitui o farmacêutico.")

    from src.assistente.cliente_llm import verificar_disponibilidade, MENSAGEM_INDISPONIVEL
    from src.assistente.contexto import montar_contexto
    from src.assistente.agente import processar_pergunta
    from src.assistente.provedores import provedores_configurados

    if "mensagens_chat" not in st.session_state:
        st.session_state.mensagens_chat = []
    if "contador_perguntas" not in st.session_state:
        st.session_state.contador_perguntas = 0

    provs_disponiveis = provedores_configurados()

    if not provs_disponiveis:
        st.info(MENSAGEM_INDISPONIVEL)
    else:
        # Seletor de Modelo de IA no topo da seção
        opcoes_nomes = ["Automático"] + [info["nome"] for info in provs_disponiveis.values()]
        mapa_nomes = {info["nome"]: pid for pid, info in provs_disponiveis.items()}

        col_sel, _ = st.columns([1, 2])
        with col_sel:
            escolha_nome = st.selectbox(
                "Modelo de IA:",
                options=opcoes_nomes,
                index=0,
                help="Selecione o provedor de IA desejado. 'Automático' utiliza a ordem de tentativa com fallback automático.",
            )

        provedor_selecionado = None if escolha_nome == "Automático" else mapa_nomes.get(escolha_nome)

        contexto_markdown = montar_contexto(
            estoque=estoque,
            sugestoes=sugestoes,
            saldo_lotes=saldo_lotes,
            anomalias=anomalias,
            previsoes=previsoes,
            consumo=consumo,
        )

        st.markdown("**Perguntas prontas:**")
        col_b1, col_b2, col_b3 = st.columns(3)
        pergunta_pronta = None

        if col_b1.button("O que preciso comprar?", use_container_width=True):
            pergunta_pronta = "O que preciso comprar?"
        if col_b2.button("Algum lote perto de vencer?", use_container_width=True):
            pergunta_pronta = "Algum lote perto de vencer?"
        if col_b3.button("Resuma a situação do estoque", use_container_width=True):
            pergunta_pronta = "Resuma a situação do estoque"

        for msg in st.session_state.mensagens_chat:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("role") == "assistant" and msg.get("provedor"):
                    st.caption(f"Provedor: {msg['provedor']}")

        if st.session_state.contador_perguntas >= 15:
            st.warning("Limite de 15 perguntas por sessão atingido.")
            pergunta_digitada = None
        else:
            pergunta_digitada = st.chat_input("Digite sua dúvida sobre o estoque...")

        pergunta_a_enviar = pergunta_pronta or pergunta_digitada

        if pergunta_a_enviar:
            if st.session_state.contador_perguntas >= 15:
                st.warning("Limite de 15 perguntas por sessão atingido.")
            else:
                st.session_state.contador_perguntas += 1
                st.session_state.mensagens_chat.append({"role": "user", "content": pergunta_a_enviar})
                with st.chat_message("user"):
                    st.write(pergunta_a_enviar)

                with st.chat_message("assistant"):
                    with st.spinner("Consultando dados do estoque..."):
                        resposta = processar_pergunta(
                            pergunta=pergunta_a_enviar,
                            historico=st.session_state.mensagens_chat[:-1],
                            contexto=contexto_markdown,
                            provedor=provedor_selecionado,
                        )
                        texto_resposta = resposta.texto if hasattr(resposta, "texto") else str(resposta)
                        st.write(texto_resposta)

                        legenda_prov = None
                        prov_usado = getattr(resposta, "provedor_usado", None)
                        if prov_usado:
                            info_p = provs_disponiveis.get(prov_usado)
                            nome_p = info_p["nome"] if info_p else prov_usado
                            if getattr(resposta, "fallback_ocorreu", False):
                                nome_p += " (fallback)"
                            legenda_prov = nome_p
                            st.caption(f"Provedor: {legenda_prov}")

                st.session_state.mensagens_chat.append({
                    "role": "assistant",
                    "content": texto_resposta,
                    "provedor": legenda_prov,
                })

    # ── Rodapé ─────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        "**Cofre Estoque Inteligente** — Hackathon Connect 7.0 | "
        "Dados simulados para demonstração | "
        "Previsão por média móvel e suavização exponencial"
    )


if __name__ == "__main__":
    main()
