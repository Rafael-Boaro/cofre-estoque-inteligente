"""
Registro e gerenciamento de múltiplos provedores de LLM.

Suporta Anthropic, OpenAI, Groq, Gemini, OpenRouter e endpoints compatíveis com OpenAI.
Chaves e modelos são obtidos de st.secrets ou variáveis de ambiente.
"""
import os
from typing import Any, Dict, List, Optional

# Registro central de provedores suportados.
# Modelos padrões marcados com aviso de confirmação na documentação oficial.
REGISTRO_PROVEDORES: Dict[str, Dict[str, Any]] = {
    "anthropic": {
        "nome": "Anthropic (Claude)",
        "tipo_cliente": "anthropic",
        "base_url": None,
        "var_chave": "ANTHROPIC_API_KEY",
        "var_modelo": "ANTHROPIC_MODEL",
        "modelo_padrao": "claude-3-5-sonnet-20241022",
        "aviso_modelo": "confirme na documentação oficial",
        "var_base_url": None,
    },
    "openai": {
        "nome": "OpenAI (GPT)",
        "tipo_cliente": "openai",
        "base_url": "https://api.openai.com/v1",
        "var_chave": "OPENAI_API_KEY",
        "var_modelo": "OPENAI_MODEL",
        "modelo_padrao": "gpt-4o-mini",
        "aviso_modelo": "confirme na documentação oficial",
        "var_base_url": None,
    },
    "groq": {
        "nome": "Groq",
        "tipo_cliente": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "var_chave": "GROQ_API_KEY",
        "var_modelo": "GROQ_MODEL",
        "modelo_padrao": "llama-3.3-70b-versatile",
        "aviso_modelo": "confirme na documentação oficial",
        "var_base_url": None,
    },
    "gemini": {
        "nome": "Google Gemini (OpenAI compatível)",
        "tipo_cliente": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "var_chave": "GEMINI_API_KEY",
        "var_modelo": "GEMINI_MODEL",
        "modelo_padrao": "gemini-2.5-flash",
        "aviso_modelo": "confirme na documentação oficial",
        "var_base_url": None,
    },
    "openrouter": {
        "nome": "OpenRouter",
        "tipo_cliente": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "var_chave": "OPENROUTER_API_KEY",
        "var_modelo": "OPENROUTER_MODEL",
        "modelo_padrao": "meta-llama/llama-3.3-70b-instruct",
        "aviso_modelo": "confirme na documentação oficial",
        "var_base_url": None,
    },
    "compativel": {
        "nome": "Compatível com OpenAI (Ollama / Local)",
        "tipo_cliente": "openai",
        "base_url": "http://localhost:11434/v1",
        "var_chave": "LLM_API_KEY",
        "var_modelo": "LLM_MODEL",
        "modelo_padrao": "llama3",
        "aviso_modelo": "confirme na documentação oficial",
        "var_base_url": "LLM_BASE_URL",
    },
}


def obter_segredo(chave: str, padrao: str = "") -> str:
    """
    Recupera um valor de configuração com prioridade:
    1. st.secrets (se executando no Streamlit)
    2. os.environ (variáveis de ambiente do sistema)
    3. Valor padrão
    """
    try:
        import streamlit as st

        if hasattr(st, "secrets") and chave in st.secrets:
            valor = st.secrets[chave]
            if valor is not None:
                return str(valor).strip()
    except Exception:
        pass

    valor_env = os.environ.get(chave)
    if valor_env is not None and str(valor_env).strip():
        return str(valor_env).strip()

    return padrao


def obter_credenciais_provedor(pid: str) -> Optional[Dict[str, Any]]:
    """
    Retorna os parâmetros de configuração de um provedor específico se sua chave estiver presente.
    Garante compatibilidade reversa com as variáveis legadas (LLM_API_KEY, LLM_MODEL, LLM_PROVIDER).
    """
    pid = (pid or "").strip().lower()
    if pid not in REGISTRO_PROVEDORES:
        return None

    info = REGISTRO_PROVEDORES[pid]
    chave = obter_segredo(info["var_chave"])
    modelo = obter_segredo(info["var_modelo"])

    # Compatibilidade reversa: se variaveis especificas nao existirem, verifica LLM_API_KEY / LLM_MODEL
    provedor_legado = obter_segredo("LLM_PROVIDER", "").lower()
    if not chave:
        # Se for o provedor compativel ou se LLM_PROVIDER apontar para este provedor (ou padrao anthropic)
        if pid == "compativel" and obter_segredo("LLM_BASE_URL"):
            chave = obter_segredo("LLM_API_KEY")
        elif provedor_legado == pid:
            chave = obter_segredo("LLM_API_KEY")
        elif not provedor_legado and pid == "anthropic":
            chave = obter_segredo("LLM_API_KEY")

    if not chave or chave.startswith("sua-chave") or chave == "sua-chave-aqui":
        return None

    # Modelo configurado ou fallback para o padrao
    if not modelo:
        if (provedor_legado == pid or (not provedor_legado and pid == "anthropic")) and obter_segredo("LLM_MODEL"):
            modelo = obter_segredo("LLM_MODEL")
        else:
            modelo = info["modelo_padrao"]

    # Base URL (permite customizacao via secret de base_url quando aplicavel)
    base_url = info["base_url"]
    if info.get("var_base_url"):
        base_url = obter_segredo(info["var_base_url"], base_url or "")

    return {
        "id": pid,
        "nome": info["nome"],
        "tipo_cliente": info["tipo_cliente"],
        "base_url": base_url,
        "api_key": chave,
        "modelo": modelo,
    }


def provedores_configurados() -> Dict[str, Dict[str, Any]]:
    """
    Retorna um dicionário apenas com os provedores que possuem chave de API configurada.
    """
    configurados = {}
    for pid in REGISTRO_PROVEDORES:
        creds = obter_credenciais_provedor(pid)
        if creds:
            configurados[pid] = creds
    return configurados


def ordem_de_tentativa(provedor_preferido: Optional[str] = None) -> List[str]:
    """
    Calcula a lista ordenada de provedores a tentar, sem duplicatas.
    Prioridade:
    1. Provedor preferido (se especificado pelo usuario e configurado)
    2. Provedor principal configurado em LLM_PROVIDER (se configurado)
    3. Provedores definidos em LLM_FALLBACKS (lista separada por virgula)
    4. Demais provedores configurados disponiveis
    """
    disponiveis = provedores_configurados()
    if not disponiveis:
        return []

    ordem: List[str] = []

    # 1. Provedor preferido explícito
    if provedor_preferido:
        pref = provedor_preferido.strip().lower()
        if pref in disponiveis and pref not in ordem:
            ordem.append(pref)

    # 2. Provedor principal configurado no secret/env
    provedor_principal = obter_segredo("LLM_PROVIDER", "").lower()
    if provedor_principal in disponiveis and provedor_principal not in ordem:
        ordem.append(provedor_principal)

    # 3. Fallbacks configurados
    fallbacks_raw = obter_segredo("LLM_FALLBACKS", "")
    if fallbacks_raw:
        for f in fallbacks_raw.split(","):
            f_clean = f.strip().lower()
            if f_clean in disponiveis and f_clean not in ordem:
                ordem.append(f_clean)

    # 4. Demais provedores configurados que ainda não estão na ordem
    for pid in REGISTRO_PROVEDORES:
        if pid in disponiveis and pid not in ordem:
            ordem.append(pid)

    return ordem
