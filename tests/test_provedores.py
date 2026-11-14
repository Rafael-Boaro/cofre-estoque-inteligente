"""
Testes unitários para múltiplos provedores de LLM e mecanismo de fallback.

Garante ausência de chamadas externas reais e validação rigorosa de segurança
(nenhuma chave vazada em erros ou mensagens).
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.assistente.cliente_llm import MENSAGEM_INDISPONIVEL, responder
from src.assistente.provedores import (
    REGISTRO_PROVEDORES,
    obter_credenciais_provedor,
    ordem_de_tentativa,
    provedores_configurados,
)


class TestConfiguracaoProvedores:
    def test_apenas_provedores_com_chave_aparecem(self, monkeypatch):
        """(a) Só provedores com chave configurada devem aparecer em provedores_configurados()."""
        # Limpa todas as chaves do ambiente
        for info in REGISTRO_PROVEDORES.values():
            monkeypatch.delenv(info["var_chave"], raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)

        # Configura apenas Groq e Gemini
        monkeypatch.setenv("GROQ_API_KEY", "chave-groq-teste")
        monkeypatch.setenv("GEMINI_API_KEY", "chave-gemini-teste")

        configurados = provedores_configurados()
        assert "groq" in configurados
        assert "gemini" in configurados
        assert "anthropic" not in configurados
        assert "openai" not in configurados
        assert "openrouter" not in configurados
        assert len(configurados) == 2

    def test_ordem_de_tentativa_respeita_principal_e_fallbacks_sem_duplicar(self, monkeypatch):
        """(b) A ordem de tentativa respeita principal + fallbacks sem repetir provedores."""
        for info in REGISTRO_PROVEDORES.values():
            monkeypatch.delenv(info["var_chave"], raising=False)

        monkeypatch.setenv("GROQ_API_KEY", "chave-groq")
        monkeypatch.setenv("GEMINI_API_KEY", "chave-gemini")
        monkeypatch.setenv("OPENAI_API_KEY", "chave-openai")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-anthropic")

        monkeypatch.setenv("LLM_PROVIDER", "groq")
        # Fornece duplicatas na lista de fallbacks
        monkeypatch.setenv("LLM_FALLBACKS", "gemini,openai,groq,gemini")

        ordem = ordem_de_tentativa()
        # Deve iniciar com o principal (groq), seguido pelos fallbacks sem duplicar
        assert ordem[0] == "groq"
        assert ordem[1] == "gemini"
        assert ordem[2] == "openai"
        assert ordem[3] == "anthropic"
        assert len(ordem) == len(set(ordem))

    def test_ordem_com_provedor_preferido(self, monkeypatch):
        """Se o usuário selecionar um provedor no seletor, ele deve vir primeiro."""
        monkeypatch.setenv("GROQ_API_KEY", "k1")
        monkeypatch.setenv("OPENAI_API_KEY", "k2")
        monkeypatch.setenv("LLM_PROVIDER", "groq")

        ordem = ordem_de_tentativa(provedor_preferido="openai")
        assert ordem[0] == "openai"
        assert "groq" in ordem


class TestFallbackETratamentoDeErros:
    def test_fallback_acontece_quando_primeiro_falha_por_limite_de_taxa(self, monkeypatch):
        """(c) O fallback acontece quando o primeiro provedor falha por limite de taxa (429)."""
        monkeypatch.setenv("GROQ_API_KEY", "chave-groq")
        monkeypatch.setenv("GEMINI_API_KEY", "chave-gemini")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("LLM_FALLBACKS", "gemini")

        class MockRateLimitError(Exception):
            status_code = 429

        def mock_chamada(info_provedor, prompt_sistema, mensagens):
            if info_provedor["id"] == "groq":
                raise MockRateLimitError("Rate limit exceeded 429")
            if info_provedor["id"] == "gemini":
                return "Resposta atendida pelo Gemini com sucesso."
            return ""

        with patch("src.assistente.cliente_llm._chamar_provedor", side_effect=mock_chamada):
            resposta = responder("prompt", [{"role": "user", "content": "ola"}], "contexto")

            assert resposta.provedor_usado == "gemini"
            assert resposta.fallback_ocorreu is True
            assert len(resposta.tentativas_falhas) == 1
            assert resposta.tentativas_falhas[0][0] == "groq"
            assert "limite de taxa" in resposta.tentativas_falhas[0][1]
            assert "Resposta atendida pelo Gemini" in resposta.texto

    def test_mensagem_final_indisponivel_quando_todos_falham(self, monkeypatch):
        """(d) A mensagem final é a de indisponibilidade quando todos os provedores falham."""
        monkeypatch.setenv("GROQ_API_KEY", "chave-groq")
        monkeypatch.setenv("GEMINI_API_KEY", "chave-gemini")
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("LLM_FALLBACKS", "gemini")

        with patch(
            "src.assistente.cliente_llm._chamar_provedor",
            side_effect=RuntimeError("Falha de infraestrutura"),
        ):
            resposta = responder("prompt", [{"role": "user", "content": "ola"}], "contexto")

            assert resposta.texto == MENSAGEM_INDISPONIVEL
            assert resposta.provedor_usado is None
            assert len(resposta.tentativas_falhas) == 2

    def test_nenhuma_saida_de_erro_contem_valor_da_chave(self, monkeypatch):
        """(e) Nenhuma saída de erro ou motivo de falha deve conter o valor da chave secreta."""
        chave_secreta = "sk-SEGREDO-ULTRA-CONFIDENCIAL-123456789"
        monkeypatch.setenv("GROQ_API_KEY", chave_secreta)
        monkeypatch.setenv("LLM_PROVIDER", "groq")

        # Exceção que simula o SDK vazando a chave na mensagem de erro original
        with patch(
            "src.assistente.cliente_llm._chamar_provedor",
            side_effect=Exception(f"Unauthorized token: {chave_secreta}"),
        ):
            resposta = responder("prompt", [{"role": "user", "content": "ola"}], "contexto")

            assert chave_secreta not in resposta.texto
            for pid, motivo in resposta.tentativas_falhas:
                assert chave_secreta not in motivo
                assert chave_secreta not in pid
