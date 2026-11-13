"""
Simulador de eventos do cofre refrigerado.

Gera eventos realistas de entrada e retirada de medicamentos
com sazonalidade semanal, picos aleatórios, múltiplos lotes,
validades escalonadas e controle FEFO na retirada para manter
o estoque físico sempre consistente (sem saldo negativo).
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict

import numpy as np
import pandas as pd

from src.config import MEDICAMENTOS, DIAS_HISTORICO


def _criar_catalogo_lotes(medicamento: str, data_referencia: datetime) -> List[Dict]:
    """Cria múltiplos lotes escalonados para um medicamento ao longo do histórico."""
    prefixo = medicamento.replace(" ", "")[:5].upper()
    # Para Imunobiológico e Vacina Especial, o lote 4 recebe validade mais próxima (15 a 25 dias)
    # simulando lotes de campanha/biológicos que precisam de atenção FEFO
    if medicamento in {"Imunobiológico C", "Vacina Especial F"}:
        val_lote4 = (data_referencia + timedelta(days=random.randint(14, 26))).strftime("%Y-%m-%d")
    else:
        val_lote4 = (data_referencia + timedelta(days=random.randint(120, 240))).strftime("%Y-%m-%d")

    lotes = [
        {"lote": f"L{prefixo}-001", "validade": (data_referencia - timedelta(days=random.randint(5, 15))).strftime("%Y-%m-%d")},
        {"lote": f"L{prefixo}-002", "validade": (data_referencia + timedelta(days=random.randint(30, 60))).strftime("%Y-%m-%d")},
        {"lote": f"L{prefixo}-003", "validade": (data_referencia + timedelta(days=random.randint(70, 110))).strftime("%Y-%m-%d")},
        {"lote": f"L{prefixo}-004", "validade": val_lote4},
    ]
    return lotes


def gerar_eventos(
    seed: int = 42,
    dias: int = DIAS_HISTORICO,
    medicamentos: List[str] = None,
) -> pd.DataFrame:
    """
    Gera DataFrame com eventos simulados do cofre refrigerado.

    Cada linha representa uma entrada ou retirada com:
    timestamp, tipo, medicamento, lote, validade, quantidade.

    Características da simulação:
    - Base de consumo diário calibrada para medicamentos de alto custo
    - Sazonalidade semanal (dias úteis têm maior saída; fins de semana menor)
    - Picos aleatórios (~5% dos dias simulando alta demanda pontual)
    - Entradas periódicas de reposição com lotes escalonados
    - Consumo seguindo FEFO (dispensa primeiro o lote mais próximo do vencimento)
    - Estoque físico nunca negativo (o cofre só libera unidades existentes)
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)

    if medicamentos is None:
        medicamentos = MEDICAMENTOS

    base_consumo = {
        "Caneta GLP-1 A": 4,
        "Insulina Basal B": 6,
        "Imunobiológico C": 2,
        "Anticorpo Monoclonal D": 1,
        "Hormônio de Crescimento E": 3,
        "Vacina Especial F": 5,
    }

    # Medicamentos configurados intencionalmente para ficarem com estoque baixo no fim dos 90 dias
    # para gerar alertas claros de reposição para o gestor e fornecedor
    meds_estoque_baixo = {"Caneta GLP-1 A", "Insulina Basal B", "Vacina Especial F"}

    hoje = datetime.now()
    data_inicio = hoje - timedelta(days=dias)
    eventos = []

    # Estrutura para rastrear saldo físico em tempo real por medicamento e por lote
    catalogo_lotes = {med: _criar_catalogo_lotes(med, hoje) for med in medicamentos}
    estoque_por_lote = {med: {} for med in medicamentos}

    # 1. Estoque inicial no Dia 0 (distribuído entre lote 001 e 002)
    for med in medicamentos:
        base = base_consumo.get(med, 3)
        lote1 = catalogo_lotes[med][0]
        lote2 = catalogo_lotes[med][1]

        # Quantidade inicial proporcional ao consumo (~15 a 20 dias de cobertura inicial)
        qtd_lote1 = max(5, int(base * 6))
        qtd_lote2 = max(10, int(base * 10))

        estoque_por_lote[med][lote1["lote"]] = {
            "validade": lote1["validade"],
            "saldo": qtd_lote1,
        }
        estoque_por_lote[med][lote2["lote"]] = {
            "validade": lote2["validade"],
            "saldo": qtd_lote2,
        }

        eventos.append({
            "timestamp": data_inicio.strftime("%Y-%m-%d 07:30:00"),
            "tipo": "entrada",
            "medicamento": med,
            "lote": lote1["lote"],
            "validade": lote1["validade"],
            "quantidade": qtd_lote1,
        })
        eventos.append({
            "timestamp": data_inicio.strftime("%Y-%m-%d 07:45:00"),
            "tipo": "entrada",
            "medicamento": med,
            "lote": lote2["lote"],
            "validade": lote2["validade"],
            "quantidade": qtd_lote2,
        })

    # 2. Simulação dia a dia ao longo dos 90 dias
    for dia in range(dias):
        data_atual = data_inicio + timedelta(days=dia)
        dia_semana = data_atual.weekday()

        # Reposições periódicas a cada 14 dias
        # Para os medicamentos de estoque baixo, não repõe nos últimos 18 dias
        if dia > 0 and dia % 14 == 0:
            for med in medicamentos:
                eh_baixo = med in meds_estoque_baixo
                nos_ultimos_dias = (dias - dia) <= 18

                if eh_baixo and nos_ultimos_dias:
                    # Não recebe entrega nos últimos dias -> forçando o estoque a entrar em ponto de pedido
                    continue

                base = base_consumo.get(med, 3)
                # Seleciona lote novo (lote 003 ou 004 conforme avança no tempo)
                idx_lote = 2 if dia < 45 else 3
                lote_info = catalogo_lotes[med][idx_lote]
                qtd_reposicao = int(base * 14 * rng.uniform(0.9, 1.15))

                if lote_info["lote"] not in estoque_por_lote[med]:
                    estoque_por_lote[med][lote_info["lote"]] = {
                        "validade": lote_info["validade"],
                        "saldo": 0,
                    }
                estoque_por_lote[med][lote_info["lote"]]["saldo"] += qtd_reposicao

                eventos.append({
                    "timestamp": data_atual.strftime("%Y-%m-%d 07:00:00"),
                    "tipo": "entrada",
                    "medicamento": med,
                    "lote": lote_info["lote"],
                    "validade": lote_info["validade"],
                    "quantidade": qtd_reposicao,
                })

        # Retiradas diárias (dispensa aos pacientes)
        for med in medicamentos:
            base = base_consumo.get(med, 3)
            fator_semana = 1.0 if dia_semana < 5 else 0.45
            fator_pico = 2.4 if rng.random() < 0.05 else 1.0

            demanda = int(rng.poisson(base * fator_semana * fator_pico))
            if demanda <= 0:
                continue

            # Retira seguindo a ordem FEFO dos lotes ativos com saldo > 0
            lotes_ativos = [
                (lote_id, info)
                for lote_id, info in estoque_por_lote[med].items()
                if info["saldo"] > 0
            ]
            lotes_ativos.sort(key=lambda x: x[1]["validade"])

            demanda_restante = demanda
            for lote_id, info in lotes_ativos:
                if demanda_restante <= 0:
                    break

                qtd_retirar = min(info["saldo"], demanda_restante)
                if qtd_retirar <= 0:
                    continue

                info["saldo"] -= qtd_retirar
                demanda_restante -= qtd_retirar

                hora = int(rng.integers(8, 20))
                minuto = int(rng.integers(0, 60))
                ts = data_atual.replace(hour=hora, minute=minuto)

                eventos.append({
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "tipo": "retirada",
                    "medicamento": med,
                    "lote": lote_id,
                    "validade": info["validade"],
                    "quantidade": qtd_retirar,
                })

    df = pd.DataFrame(eventos)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df
