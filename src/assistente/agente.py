"""
Orquestrador do Assistente de Estoque.

Carrega as regras de negocio do agent.md, gerencia a janela de contexto da
conversa (limite de 6 trocas) e valida restricoes de tamanho de entrada (~500 caracteres).
"""
from pathlib import Path
from typing import Dict, List, Optional

from src.assistente.cliente_llm import RespostaLLM, responder
from src.config import RAIZ

CAMINHO_AGENT_MD = RAIZ / "agent.md"
LIMITE_CARACTERES_PERGUNTA = 500
MAX_MENSAGENS_HISTORICO = 12  # 6 trocas (usuario + assistente)


def carregar_prompt_sistema() -> str:
    """
    Carrega o arquivo agent.md na raiz do projeto.
    Caso o arquivo nao seja encontrado, devolve diretrizes padrao de fallback.
    """
    if CAMINHO_AGENT_MD.exists():
        try:
            return CAMINHO_AGENT_MD.read_text(encoding="utf-8")
        except Exception:
            pass

    return (
        "# Assistente do Cofre Estoque Inteligente\n\n"
        "Voce explica os numeros de estoque, previsao e reposicao calculados pelo sistema. "
        "Use apenas os dados fornecidos no CONTEXTO e nao invente dados."
    )


def sanitizar_pergunta(pergunta: str, max_chars: int = LIMITE_CARACTERES_PERGUNTA) -> str:
    """Limpa espacos e limita o tamanho maximo da pergunta."""
    texto = (pergunta or "").strip()
    if len(texto) > max_chars:
        texto = texto[:max_chars].rstrip()
    return texto


def processar_pergunta(
    pergunta: str,
    historico: List[Dict[str, str]],
    contexto: str,
    provedor: Optional[str] = None,
) -> RespostaLLM:
    """
    Recebe a pergunta do usuario, o historico recente, o contexto dos dados
    e o provedor selecionado, devolvendo a resposta estruturada do assistente.

    Garante:
    - Truncamento da pergunta em no maximo 500 caracteres.
    - Janela deslizante de no maximo 6 trocas anteriores (12 mensagens).
    - Injecao estrita do agent.md e das tabelas contextuais.
    """
    pergunta_limpa = sanitizar_pergunta(pergunta)
    if not pergunta_limpa:
        return RespostaLLM(texto="Por favor, digite uma pergunta sobre o estoque da farmácia.")

    # Filtra as ultimas mensagens para nao ultrapassar 6 trocas (12 mensagens)
    historico_recente = [
        {"role": m["role"], "content": m["content"]}
        for m in (historico or [])
        if m.get("role") in ("user", "assistant") and m.get("content")
    ][-MAX_MENSAGENS_HISTORICO:]

    # Adiciona a pergunta atual
    mensagens_envio = historico_recente + [{"role": "user", "content": pergunta_limpa}]

    prompt_sistema = carregar_prompt_sistema()

    return responder(
        system_prompt=prompt_sistema,
        mensagens=mensagens_envio,
        contexto=contexto,
        provedor=provedor,
    )
