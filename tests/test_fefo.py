"""
Testes para o módulo FEFO (First Expired, First Out).
Executável via pytest ou python diretamente.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        def fixture(func):
            return func
    pytest = _MockPytest()

import pandas as pd

from src.diferenciais.fefo import (
    calcular_saldo_por_lote,
    ordenar_fefo,
    lotes_proximos_vencimento,
    sugerir_ordem_saida,
)


@pytest.fixture
def eventos_lotes():
    """Eventos com múltiplos lotes e validades."""
    hoje = datetime.now()
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2024-01-01 08:00", "2024-01-01 08:00",
            "2024-01-15 10:00", "2024-01-15 10:00",
        ]),
        "tipo": ["entrada", "entrada", "retirada", "retirada"],
        "medicamento": ["Med A", "Med A", "Med A", "Med A"],
        "lote": ["L001", "L002", "L001", "L002"],
        "validade": [
            (hoje + timedelta(days=10)).strftime("%Y-%m-%d"),  # vence em 10 dias
            (hoje + timedelta(days=90)).strftime("%Y-%m-%d"),  # vence em 90 dias
            (hoje + timedelta(days=10)).strftime("%Y-%m-%d"),
            (hoje + timedelta(days=90)).strftime("%Y-%m-%d"),
        ],
        "quantidade": [30, 20, 5, 3],
    })


class TestSaldoPorLote:
    def test_calcula_saldo(self, eventos_lotes=None):
        """Saldo = entradas - retiradas por lote."""
        if eventos_lotes is None:
            eventos_lotes = globals()["eventos_lotes"]()
        saldo = calcular_saldo_por_lote(eventos_lotes)
        l001 = saldo[saldo["lote"] == "L001"]["saldo_lote"].iloc[0]
        l002 = saldo[saldo["lote"] == "L002"]["saldo_lote"].iloc[0]
        assert l001 == 25  # 30 - 5
        assert l002 == 17  # 20 - 3

    def test_saldo_nao_negativo(self, eventos_lotes=None):
        """Saldo nunca deve ser negativo."""
        if eventos_lotes is None:
            eventos_lotes = globals()["eventos_lotes"]()
        saldo = calcular_saldo_por_lote(eventos_lotes)
        assert (saldo["saldo_lote"] >= 0).all()


class TestOrdenarFefo:
    def test_ordem_por_validade(self, eventos_lotes=None):
        """Lote que vence antes deve aparecer primeiro."""
        if eventos_lotes is None:
            eventos_lotes = globals()["eventos_lotes"]()
        saldo = calcular_saldo_por_lote(eventos_lotes)
        ordenado = ordenar_fefo(saldo)
        validades = ordenado["validade"].tolist()
        assert validades == sorted(validades)


class TestLotesProximosVencimento:
    def test_detecta_lote_proximo(self, eventos_lotes=None):
        """Lote que vence em 10 dias deve ser detectado com alerta de 30 dias."""
        if eventos_lotes is None:
            eventos_lotes = globals()["eventos_lotes"]()
        saldo = calcular_saldo_por_lote(eventos_lotes)
        proximos = lotes_proximos_vencimento(saldo, dias_alerta=30)
        assert len(proximos) >= 1
        assert "L001" in proximos["lote"].values

    def test_nao_detecta_lote_distante(self, eventos_lotes=None):
        """Lote que vence em 90 dias não deve ser detectado com alerta de 30 dias."""
        if eventos_lotes is None:
            eventos_lotes = globals()["eventos_lotes"]()
        saldo = calcular_saldo_por_lote(eventos_lotes)
        proximos = lotes_proximos_vencimento(saldo, dias_alerta=30)
        assert "L002" not in proximos["lote"].values


class TestSugerirOrdemSaida:
    def test_ordem_fefo(self, eventos_lotes=None):
        """Deve sugerir primeiro o lote com validade mais próxima."""
        if eventos_lotes is None:
            eventos_lotes = globals()["eventos_lotes"]()
        saldo = calcular_saldo_por_lote(eventos_lotes)
        ordem = sugerir_ordem_saida(saldo, "Med A")
        assert len(ordem) == 2
        assert ordem.iloc[0]["lote"] == "L001"  # vence antes


if __name__ == "__main__":
    df = eventos_lotes()
    t_sl = TestSaldoPorLote()
    t_sl.test_calcula_saldo(df)
    t_sl.test_saldo_nao_negativo(df)

    t_of = TestOrdenarFefo()
    t_of.test_ordem_por_validade(df)

    t_pv = TestLotesProximosVencimento()
    t_pv.test_detecta_lote_proximo(df)
    t_pv.test_nao_detecta_lote_distante(df)

    t_so = TestSugerirOrdemSaida()
    t_so.test_ordem_fefo(df)

    print("[OK] Todos os testes de test_fefo.py passaram!")
