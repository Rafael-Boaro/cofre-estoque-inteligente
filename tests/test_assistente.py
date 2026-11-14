"""
Testes unitarios para o Assistente de Estoque (LLM).

Todos os testes utilizam mocks para garantir que NENHUMA chamada real a APIs
externas seja realizada.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.assistente.agente import (
    carregar_prompt_sistema,
    processar_pergunta,
    sanitizar_pergunta,
)
from src.assistente.cliente_llm import MENSAGEM_INDISPONIVEL, responder, verificar_disponibilidade
from src.assistente.contexto import montar_contexto


class TestCarregamentoAgentMd:
    def test_agent_md_carregado(self):
        """Verifica se as regras do agent.md sao lidas corretamente."""
        prompt = carregar_prompt_sistema()
        assert "Assistente do Cofre Estoque Inteligente" in prompt
        assert "FEFO" in prompt
        assert "CONTEXTO" in prompt
        assert "farmacêutico" in prompt or "farmaceutico" in prompt


class TestMontagemContexto:
    def test_contexto_contem_numeros_das_tabelas(self):
        """O texto do contexto deve conter exatamente os valores calculados pelas tabelas."""
        estoque = pd.DataFrame({
            "medicamento": ["Med Alfa", "Med Beta"],
            "estoque_atual": [15, 40],
        })
        sugestoes = pd.DataFrame({
            "medicamento": ["Med Alfa", "Med Beta"],
            "estoque_atual": [15, 40],
            "consumo_medio_dia": [3.5, 2.0],
            "desvio_consumo": [0.5, 0.2],
            "estoque_seguranca": [10.0, 5.0],
            "ponto_pedido": [25.0, 15.0],
            "dias_cobertura": [4.3, 20.0],
            "qtd_sugerida": [55, 0],
            "data_limite_pedido": ["2026-11-20", "2026-12-15"],
            "precisa_comprar": [True, False],
        })
        saldo_lotes = pd.DataFrame({
            "medicamento": ["Med Alfa"],
            "lote": ["LOTE-999"],
            "validade": [pd.Timestamp(datetime.now().date()) + pd.Timedelta(days=12)],
            "saldo_lote": [14],
        })
        anomalias = pd.DataFrame({
            "data": ["2026-11-10"],
            "medicamento": ["Med Alfa"],
            "consumo": [19],
            "z_score": [3.45],
            "tipo_anomalia": ["pico"],
        })
        previsoes = pd.DataFrame({
            "medicamento": ["Med Alfa"],
            "dia": [1],
            "previsao": [4.8],
            "modelo": ["media_movel"],
        })
        consumo = pd.DataFrame({
            "data": ["2026-11-13"],
            "medicamento": ["Med Alfa"],
            "consumo": [3],
        })

        contexto = montar_contexto(
            estoque=estoque,
            sugestoes=sugestoes,
            saldo_lotes=saldo_lotes,
            anomalias=anomalias,
            previsoes=previsoes,
            consumo=consumo,
        )

        assert "### CONTEXTO (dados de teste simulados)" in contexto
        assert "Data de referencia: 2026-11-13" in contexto
        assert "Med Alfa" in contexto
        assert "Estoque 15 un" in contexto
        assert "Cobertura 4.3 dias" in contexto
        assert "Quantidade sugerida: 55 un" in contexto
        assert "2026-11-20" in contexto
        assert "LOTE-999" in contexto
        assert "Saldo restante: 14 un" in contexto
        assert "3.45" in contexto
        assert "4.8 un/dia" in contexto
        assert "media_movel" in contexto


class TestComportamentoSemChave:
    def test_verificar_disponibilidade_sem_chave(self, monkeypatch):
        """Sem chave configurada, deve apontar indisponibilidade."""
        monkeypatch.setenv("LLM_API_KEY", "")
        with patch("src.assistente.cliente_llm.obter_configuracao", return_value=("anthropic", "claude", "")):
            assert verificar_disponibilidade() is False

    def test_resposta_sem_chave_devolve_mensagem_indisponivel(self, monkeypatch):
        """Sem chave, responder e processar_pergunta devolvem mensagem amigavel."""
        monkeypatch.setenv("LLM_API_KEY", "")
        with patch("src.assistente.cliente_llm.obter_configuracao", return_value=("anthropic", "claude", "")):
            resp = responder("sistema", [{"role": "user", "content": "O que comprar?"}], "contexto")
            assert resp == MENSAGEM_INDISPONIVEL

            resp_proc = processar_pergunta("O que comprar?", [], "contexto")
            assert resp_proc == MENSAGEM_INDISPONIVEL


class TestChamadasComMockLLM:
    def test_chamada_mock_anthropic(self):
        """Garante que a chamada ao provedor Anthropic envia os parametros e devolve o texto."""
        mock_bloco = MagicMock()
        mock_bloco.text = "Sugiro comprar 55 unidades de Med Alfa ate 2026-11-20."

        mock_resposta = MagicMock()
        mock_resposta.content = [mock_bloco]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resposta

        with patch("anthropic.Anthropic", return_value=mock_client):
            with patch(
                "src.assistente.cliente_llm.obter_configuracao",
                return_value=("anthropic", "claude-3-5-sonnet-20241022", "chave-teste-123456"),
            ):
                resultado = responder("prompt sistema", [{"role": "user", "content": "comprar?"}], "contexto")
                assert resultado == "Sugiro comprar 55 unidades de Med Alfa ate 2026-11-20."
                mock_client.messages.create.assert_called_once()

    def test_chamada_mock_openai(self):
        """Garante compatibilidade com OpenAI via mock."""
        mock_choice = MagicMock()
        mock_choice.message.content = "Estoque do lote LOTE-999 vence em 12 dias."

        mock_resposta = MagicMock()
        mock_resposta.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resposta

        with patch("openai.OpenAI", return_value=mock_client):
            with patch(
                "src.assistente.cliente_llm.obter_configuracao",
                return_value=("openai", "gpt-4o-mini", "chave-teste-openai-123456"),
            ):
                resultado = responder("prompt sistema", [{"role": "user", "content": "lote?"}], "contexto")
                assert resultado == "Estoque do lote LOTE-999 vence em 12 dias."
                mock_client.chat.completions.create.assert_called_once()

    def test_tratamento_falha_de_rede_ou_excecao(self):
        """Se a API levantar excecao (timeout, rede, cota), devolve mensagem amigavel."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = ConnectionError("Erro simulado de conexao")

        with patch("anthropic.Anthropic", return_value=mock_client):
            with patch(
                "src.assistente.cliente_llm.obter_configuracao",
                return_value=("anthropic", "claude-3-5-sonnet-20241022", "chave-teste-123456"),
            ):
                resultado = responder("prompt", [{"role": "user", "content": "ola"}], "contexto")
                assert resultado == MENSAGEM_INDISPONIVEL


class TestRegrasDoAgente:
    def test_truncamento_pergunta_longa(self):
        """Perguntas com mais de 500 caracteres devem ser truncadas."""
        pergunta_longa = "a" * 600
        sanitizada = sanitizar_pergunta(pergunta_longa, max_chars=500)
        assert len(sanitizada) == 500

    def test_janela_historico_seis_trocas(self):
        """Historico deve ser limitado as ultimas 6 trocas (12 mensagens)."""
        historico_longo = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(20)
        ]

        with patch("src.assistente.agente.responder") as mock_responder:
            mock_responder.return_value = "resposta ok"
            processar_pergunta("pergunta nova", historico_longo, "contexto")

            # Verifica mensagens passadas ao responder
            args, kwargs = mock_responder.call_args
            mensagens_enviadas = kwargs.get("mensagens") or args[1]
            # 12 mensagens do historico + 1 mensagem nova = 13
            assert len(mensagens_enviadas) == 13
            assert mensagens_enviadas[-1]["content"] == "pergunta nova"


class TestFatosPrecalculadosERanking:
    def test_contexto_contem_vacina_especial_f_no_primeiro_lugar_ranking(self):
        """O contexto deve conter 'Vacina Especial F' e 4,59 (ou 4.59) no primeiro lugar do ranking de anomalias."""
        anomalias = pd.DataFrame({
            "data": ["2026-09-01", "2026-09-02", "2026-09-03"],
            "medicamento": ["Vacina Especial F", "Anticorpo Monoclonal D", "Imunobiológico C"],
            "consumo": [18, 5, 7],
            "z_score": [4.586328, 4.122003, 3.412388],
            "tipo_anomalia": ["pico", "pico", "pico"],
        })
        contexto = montar_contexto(anomalias=anomalias)

        assert "FATOS PRÉ-CALCULADOS" in contexto
        assert "Vacina Especial F" in contexto
        assert "4.59" in contexto or "4,59" in contexto

        # Verifica que Vacina Especial F está no primeiro lugar do ranking / tabela de anomalias
        pos_vacina = contexto.find("Vacina Especial F")
        pos_anticorpo = contexto.find("Anticorpo Monoclonal D")
        pos_imuno = contexto.find("Imunobiológico C")
        assert pos_vacina != -1
        assert pos_vacina < pos_anticorpo < pos_imuno

        # Verifica na secao de anomalias por z-score decrescente
        linhas_contexto = contexto.split("\n")
        idx_secao = next(i for i, l in enumerate(linhas_contexto) if "Anomalias de Consumo" in l)
        primeira_linha_anomalia = next(l for l in linhas_contexto[idx_secao:] if l.startswith("- 2026-"))
        assert "Vacina Especial F" in primeira_linha_anomalia
        assert "4.59" in primeira_linha_anomalia or "4,59" in primeira_linha_anomalia
        assert "18 un" in primeira_linha_anomalia

    def test_fatos_precalculados_batem_com_dataframes_do_painel(self):
        """Os fatos pré-calculados em Python devem bater exatamente com os DataFrames do painel."""
        estoque = pd.DataFrame({
            "medicamento": ["Med Alfa", "Med Beta", "Med Gama"],
            "estoque_atual": [10, 50, 0],
        })
        sugestoes = pd.DataFrame({
            "medicamento": ["Med Alfa", "Med Beta", "Med Gama"],
            "estoque_atual": [10, 50, 0],
            "consumo_medio_dia": [2.0, 5.0, 4.0],
            "desvio_consumo": [0.5, 1.0, 0.8],
            "estoque_seguranca": [5.0, 10.0, 8.0],
            "ponto_pedido": [15.0, 25.0, 20.0],
            "dias_cobertura": [5.0, 10.0, 0.0],
            "qtd_sugerida": [30, 0, 60],
            "data_limite_pedido": ["2026-11-18", "2026-12-01", "2026-11-14"],
            "precisa_comprar": [True, False, True],
        })
        saldo_lotes = pd.DataFrame({
            "medicamento": ["Med Beta", "Med Alfa"],
            "lote": ["LOTE-B2", "LOTE-A1"],
            "validade": [
                pd.Timestamp(datetime.now().date()) + pd.Timedelta(days=40),
                pd.Timestamp(datetime.now().date()) + pd.Timedelta(days=15),
            ],
            "saldo_lote": [50, 10],
        })
        anomalias = pd.DataFrame({
            "data": ["2026-10-01", "2026-11-01", "2026-09-15"],
            "medicamento": ["Med Alfa", "Med Gama", "Med Beta"],
            "consumo": [12, 25, 18],
            "z_score": [2.8, 4.25, 3.5],
            "tipo_anomalia": ["pico", "pico", "pico"],
        })
        consumo = pd.DataFrame({
            "data": ["2026-11-01", "2026-11-02"],
            "medicamento": ["Med Gama", "Med Beta"],
            "consumo": [25, 6],
        })

        contexto = montar_contexto(
            estoque=estoque,
            sugestoes=sugestoes,
            saldo_lotes=saldo_lotes,
            anomalias=anomalias,
            consumo=consumo,
        )

        # 1. Maior anomalia: Med Gama, z_score 4.25, data 2026-11-01
        assert "Maior anomalia (maior z-score): Med Gama em 2026-11-01" in contexto
        assert "4.25" in contexto

        # 2. Maior consumo diário: Med Gama (25 un)
        assert "Maior consumo diário registrado: Med Gama em 2026-11-01 (25 un)" in contexto

        # 3. Top anomalias por z-score tem Med Gama em 1º, Med Beta em 2º, Med Alfa em 3º
        pos_gama = contexto.find("1. Med Gama")
        pos_beta = contexto.find("2. Med Beta")
        pos_alfa = contexto.find("3. Med Alfa")
        assert pos_gama != -1 and pos_beta != -1 and pos_alfa != -1
        assert pos_gama < pos_beta < pos_alfa

        # 4. Medicamentos que precisam de compra: Med Gama (60 un) e Med Alfa (30 un)
        assert "Med Gama: comprar 60 un até 2026-11-14" in contexto
        assert "Med Alfa: comprar 30 un até 2026-11-18" in contexto
        assert "Med Beta: comprar" not in contexto

        # 5. Lote com vencimento mais próximo: LOTE-A1 (15 dias)
        assert "LOTE-A1" in contexto
        assert "vence em 15 dias" in contexto

        # 6. Menor e maior cobertura
        assert "Menor cobertura em dias: Med Gama (0.0 dias" in contexto
        assert "Maior cobertura em dias: Med Beta (10.0 dias" in contexto

    def test_lista_truncada_traz_aviso(self):
        """Se a lista for truncada por limite, o contexto deve conter o aviso 'mostrando os N principais de M'."""
        anomalias = pd.DataFrame({
            "data": [f"2026-10-{i:02d}" for i in range(1, 13)],
            "medicamento": [f"Med {i}" for i in range(1, 13)],
            "consumo": list(range(10, 22)),
            "z_score": [round(2.0 + i * 0.2, 2) for i in range(1, 13)],
            "tipo_anomalia": ["pico"] * 12,
        })

        # Com limite=5 em 12 anomalias -> traz o aviso
        contexto_truncado = montar_contexto(anomalias=anomalias, limite_anomalias=5)
        assert "mostrando os 5 principais de 12" in contexto_truncado

        # Sem limite (tabela completa) -> NÃO traz o aviso
        contexto_completo = montar_contexto(anomalias=anomalias)
        assert "mostrando os" not in contexto_completo

    def test_regra_ranking_no_agent_md(self):
        """Verifica se agent.md contem explicitamente a regra sobre perguntas de ranking e fatos pre-calculados."""
        prompt = carregar_prompt_sistema()
        regra_esperada = (
            "Para perguntas de maior, menor ou ranking, use os FATOS PRÉ-CALCULADOS "
            "ou a tabela ordenada que vier no contexto e cite o valor exato. "
            "Não compare números por conta própria. Se o contexto não tiver a informação, "
            "diga que não tem."
        )
        assert regra_esperada in prompt
