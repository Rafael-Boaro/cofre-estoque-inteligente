"""
Cliente de comunicação com múltiplos provedores de LLM.

Gerencia o ciclo de requisições, timeouts curtos, fallbacks automáticos em caso
de falhas e garante que nenhuma credencial seja exposta em logs ou telas.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.assistente.provedores import (
    obter_credenciais_provedor,
    obter_segredo,
    ordem_de_tentativa,
    provedores_configurados,
)

logger = logging.getLogger(__name__)

MENSAGEM_INDISPONIVEL = "Assistente indisponível no momento. O painel continua funcionando."
TIMEOUT_PADRAO_SEGUNDOS = 15.0
MAX_TOKENS_PADRAO = 400


class RespostaLLM(str):
    """
    Representação da resposta do assistente.
    Herda de str para compatibilidade total com strings simples e interfaces Streamlit,
    adicionando metadados sobre o provedor e histórico de fallbacks.
    """

    texto: str
    provedor_usado: Optional[str]
    modelo_usado: Optional[str]
    fallback_ocorreu: bool
    tentativas_falhas: List[Tuple[str, str]]

    def __new__(
        cls,
        texto: str,
        provedor_usado: Optional[str] = None,
        modelo_usado: Optional[str] = None,
        fallback_ocorreu: bool = False,
        tentativas_falhas: Optional[List[Tuple[str, str]]] = None,
    ):
        obj = super().__new__(cls, texto)
        obj.texto = texto
        obj.provedor_usado = provedor_usado
        obj.modelo_usado = modelo_usado
        obj.fallback_ocorreu = fallback_ocorreu
        obj.tentativas_falhas = tentativas_falhas or []
        return obj


def obter_configuracao() -> Tuple[str, str, str]:
    """
    Função utilitária de compatibilidade reversa.
    Retorna (provedor, modelo, chave) do primeiro provedor ativo.
    """
    ordem = ordem_de_tentativa()
    if not ordem:
        prov_legado = obter_segredo("LLM_PROVIDER", "anthropic").lower()
        mod_legado = obter_segredo("LLM_MODEL", "claude-3-5-sonnet-20241022")
        chave_legada = obter_segredo("LLM_API_KEY", "")
        return (prov_legado, mod_legado, chave_legada)

    pid = ordem[0]
    creds = obter_credenciais_provedor(pid)
    if creds:
        return (pid, creds["modelo"], creds["api_key"])
    return ("anthropic", "claude-3-5-sonnet-20241022", "")


def verificar_disponibilidade() -> bool:
    """Verifica se há ao menos um provedor com chave válida configurada."""
    _, _, chave = obter_configuracao()
    if not chave or chave.startswith("sua-chave"):
        return False
    return bool(provedores_configurados() or len(chave) > 5)


def _identificar_motivo_erro(exc: Exception) -> str:
    """Classifica o erro de forma padronizada sem expor segredos ou chaves."""
    nome = type(exc).__name__
    msg = str(exc).lower()
    status_code = getattr(exc, "status_code", None)

    if "auth" in nome.lower() or status_code == 401 or "authentication" in msg or "invalid_api_key" in msg:
        return "chave de API inválida ou não autorizada (401)"
    if "rate" in nome.lower() or "quota" in msg or status_code == 429:
        return "limite de taxa ou cota excedida (429)"
    if "timeout" in nome.lower() or isinstance(exc, TimeoutError):
        return "tempo limite de resposta esgotado"
    if status_code and 500 <= status_code < 600:
        return f"serviço do provedor temporariamente instável ({status_code})"
    if "connection" in nome.lower():
        return "falha de conexão com o endpoint do provedor"
    return f"erro operacional ({nome})"


def responder(
    system_prompt: str,
    mensagens: List[Dict[str, str]],
    contexto: str,
    provedor: Optional[str] = None,
) -> RespostaLLM:
    """
    Envia a conversa para o LLM utilizando a ordem de tentativa configurada.
    Em caso de falha transitória ou chave inválida, realiza fallback automático
    para os próximos provedores disponíveis.
    """
    ordem = ordem_de_tentativa(provedor_preferido=provedor)

    # Compatibilidade com mocks em testes que possam alterar apenas obter_configuracao()
    creds_legadas: Optional[Dict[str, Any]] = None
    if not ordem:
        leg_prov, leg_mod, leg_chave = obter_configuracao()
        if leg_chave:
            ordem = [leg_prov]
            creds_legadas = {
                "id": leg_prov,
                "nome": leg_prov,
                "tipo_cliente": "anthropic" if leg_prov == "anthropic" else "openai",
                "base_url": None if leg_prov == "anthropic" else "https://api.openai.com/v1",
                "api_key": leg_chave,
                "modelo": leg_mod,
            }

    if not ordem:
        logger.info("Nenhum provedor de LLM configurado. Assistente indisponível.")
        return RespostaLLM(texto=MENSAGEM_INDISPONIVEL, provedor_usado=None)

    prompt_sistema_completo = f"{system_prompt.strip()}\n\n{contexto.strip()}"
    tentativas_falhas: List[Tuple[str, str]] = []

    for pid in ordem:
        info_provedor = creds_legadas if creds_legadas and creds_legadas["id"] == pid else obter_credenciais_provedor(pid)
        if not info_provedor or not info_provedor.get("api_key"):
            continue

        try:
            texto = _chamar_provedor(info_provedor, prompt_sistema_completo, mensagens)
            if texto:
                houve_fallback = len(tentativas_falhas) > 0
                return RespostaLLM(
                    texto=texto,
                    provedor_usado=pid,
                    modelo_usado=info_provedor.get("modelo"),
                    fallback_ocorreu=houve_fallback,
                    tentativas_falhas=tentativas_falhas,
                )
        except Exception as exc:
            motivo = _identificar_motivo_erro(exc)
            # Nunca registrar chave ou conteúdo sensível em logs
            logger.warning(
                "Falha ao chamar provedor '%s' (modelo: %s): %s",
                pid,
                info_provedor.get("modelo"),
                motivo,
            )
            tentativas_falhas.append((pid, motivo))

    # Se todos os provedores da ordem falharem
    logger.error("Todos os provedores configurados falharam na tentativa de resposta.")
    return RespostaLLM(
        texto=MENSAGEM_INDISPONIVEL,
        provedor_usado=None,
        fallback_ocorreu=len(tentativas_falhas) > 1,
        tentativas_falhas=tentativas_falhas,
    )


def _chamar_provedor(
    info_provedor: Dict[str, Any],
    prompt_sistema: str,
    mensagens: List[Dict[str, str]],
) -> str:
    """Direciona a chamada para o SDK correspondente ao provedor."""
    tipo = info_provedor.get("tipo_cliente", "openai")
    if tipo == "anthropic":
        return _chamar_anthropic(info_provedor, prompt_sistema, mensagens)
    return _chamar_openai_compativel(info_provedor, prompt_sistema, mensagens)


def _chamar_anthropic(
    info_provedor: Dict[str, Any],
    prompt_sistema: str,
    mensagens: List[Dict[str, str]],
) -> str:
    """Executa requisição ao SDK da Anthropic."""
    import anthropic

    client = anthropic.Anthropic(
        api_key=info_provedor["api_key"],
        timeout=TIMEOUT_PADRAO_SEGUNDOS,
    )

    payload_mensagens = [
        {"role": m["role"], "content": m["content"]}
        for m in mensagens
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]

    if not payload_mensagens:
        return ""

    modelo = str(info_provedor["modelo"]).split(" (")[0].strip()

    resposta = client.messages.create(
        model=modelo,
        max_tokens=MAX_TOKENS_PADRAO,
        system=prompt_sistema,
        messages=payload_mensagens,
    )

    if hasattr(resposta, "content") and resposta.content:
        bloco = resposta.content[0]
        return getattr(bloco, "text", str(bloco)).strip()
    return ""


def _chamar_openai_compativel(
    info_provedor: Dict[str, Any],
    prompt_sistema: str,
    mensagens: List[Dict[str, str]],
) -> str:
    """Executa requisição via SDK OpenAI para endpoints próprios ou compatíveis."""
    import openai

    kwargs: Dict[str, Any] = {
        "api_key": info_provedor["api_key"],
        "timeout": TIMEOUT_PADRAO_SEGUNDOS,
    }

    if info_provedor.get("base_url"):
        kwargs["base_url"] = info_provedor["base_url"]

    # Identificadores de aplicacao recomendados para OpenRouter
    if info_provedor.get("id") == "openrouter":
        kwargs["default_headers"] = {
            "HTTP-Referer": "https://github.com/Rafael-Boaro/cofre-estoque-inteligente",
            "X-Title": "Cofre Estoque Inteligente",
        }

    client = openai.OpenAI(**kwargs)

    payload_mensagens: List[Dict[str, Any]] = [
        {"role": "system", "content": prompt_sistema}
    ]

    for m in mensagens:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            payload_mensagens.append({"role": m["role"], "content": m["content"]})

    if len(payload_mensagens) <= 1:
        return ""

    modelo = str(info_provedor["modelo"]).split(" (")[0].strip()

    resposta = client.chat.completions.create(
        model=modelo,
        max_tokens=MAX_TOKENS_PADRAO,
        messages=payload_mensagens,
    )

    if resposta.choices and resposta.choices[0].message:
        return (resposta.choices[0].message.content or "").strip()
    return ""
