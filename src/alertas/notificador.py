"""
Notificador de alertas para fornecedor e dono da farmácia.

Gera mensagens simuladas de pedido de compra e alertas de estoque
e grava em arquivo de log. A interface é projetada para fácil
substituição futura por API real (WhatsApp, e-mail, SMS).
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Protocol

import pandas as pd

from src.config import ARQUIVO_ALERTAS

# Logger dedicado para alertas
logger = logging.getLogger("alertas")


class CanalNotificacao(Protocol):
    """Interface para canais de notificação (WhatsApp, e-mail, etc.)."""

    def enviar(self, destinatario: str, mensagem: str) -> bool: ...


class CanalSimulado:
    """Canal que apenas imprime e loga (simulação para o hackathon)."""

    def enviar(self, destinatario: str, mensagem: str) -> bool:
        """Simula envio imprimindo e retornando True."""
        print(f"[MSG] [{destinatario}] {mensagem}")
        return True


def _configurar_log(caminho: Path = ARQUIVO_ALERTAS) -> logging.FileHandler:
    """Configura handler de arquivo para o logger de alertas."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(str(caminho), encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    if not logger.handlers:
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return handler


def notificar_compras(
    sugestoes: pd.DataFrame,
    canal: CanalNotificacao | None = None,
) -> list[str]:
    """
    Envia alertas de compra para medicamentos que precisam de reposição.

    Retorna lista das mensagens geradas.
    """
    _configurar_log()
    if canal is None:
        canal = CanalSimulado()

    mensagens = []
    compras = sugestoes[sugestoes["precisa_comprar"]]

    if compras.empty:
        msg = "[OK] Nenhum medicamento precisa de reposição no momento."
        canal.enviar("Dono da Farmácia", msg)
        logger.info(msg)
        mensagens.append(msg)
        return mensagens

    for _, row in compras.iterrows():
        msg_fornecedor = (
            f"PEDIDO DE COMPRA: {row['medicamento']} — "
            f"Quantidade: {row['qtd_sugerida']} unidades — "
            f"Entregar até: {row['data_limite_pedido']}"
        )
        msg_dono = (
            f"[ALERTA] {row['medicamento']}: estoque atual {row['estoque_atual']} un. "
            f"(cobre {row['dias_cobertura']} dias). "
            f"Comprar {row['qtd_sugerida']} un. até {row['data_limite_pedido']}."
        )

        canal.enviar("Fornecedor", msg_fornecedor)
        canal.enviar("Dono da Farmácia", msg_dono)
        logger.info(msg_fornecedor)
        logger.info(msg_dono)
        mensagens.extend([msg_fornecedor, msg_dono])

    return mensagens


def notificar_validades(
    lotes_proximos: pd.DataFrame,
    canal: CanalNotificacao | None = None,
) -> list[str]:
    """
    Envia alertas sobre lotes próximos do vencimento (FEFO).

    Retorna lista das mensagens geradas.
    """
    _configurar_log()
    if canal is None:
        canal = CanalSimulado()

    mensagens = []

    if lotes_proximos.empty:
        msg = "[OK] Nenhum lote próximo do vencimento."
        canal.enviar("Dono da Farmácia", msg)
        logger.info(msg)
        mensagens.append(msg)
        return mensagens

    for _, row in lotes_proximos.iterrows():
        msg = (
            f"[VALIDADE PROXIMA] {row['medicamento']} — "
            f"Lote {row['lote']} vence em {row['validade']} "
            f"({row['dias_para_vencer']} dias). "
            f"Saldo no lote: {row['saldo_lote']} un."
        )
        canal.enviar("Dono da Farmácia", msg)
        logger.info(msg)
        mensagens.append(msg)

    return mensagens


def notificar_anomalias(
    anomalias: pd.DataFrame,
    canal: CanalNotificacao | None = None,
) -> list[str]:
    """
    Envia alertas sobre consumo anômalo detectado.

    Retorna lista das mensagens geradas.
    """
    _configurar_log()
    if canal is None:
        canal = CanalSimulado()

    mensagens = []

    if anomalias.empty:
        return mensagens

    for _, row in anomalias.iterrows():
        msg = (
            f"[ANOMALIA] {row['medicamento']} em {row['data']} — "
            f"Consumo {row['consumo']} un. (z-score: {row['z_score']:.1f}). "
            f"Investigar possível desvio."
        )
        canal.enviar("Dono da Farmácia", msg)
        logger.info(msg)
        mensagens.append(msg)

    return mensagens
