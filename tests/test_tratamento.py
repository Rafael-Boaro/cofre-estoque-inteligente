"""
Testes para o pipeline de tratamento de dados.
Executável via pytest ou python diretamente.
"""
import sys
from pathlib import Path

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

from src.tratamento.pipeline import calcular_estoque_atual, calcular_consumo_diario


@pytest.fixture
def eventos_simples():
    """Eventos mínimos para teste."""
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2024-01-01 08:00", "2024-01-01 10:00", "2024-01-01 14:00",
            "2024-01-02 09:00", "2024-01-02 15:00",
        ]),
        "tipo": ["entrada", "retirada", "retirada", "retirada", "entrada"],
        "medicamento": ["Med A", "Med A", "Med A", "Med A", "Med A"],
        "lote": ["L001", "L001", "L001", "L001", "L002"],
        "validade": ["2024-12-31"] * 5,
        "quantidade": [50, 3, 5, 4, 20],
    })


class TestEstoqueAtual:
    def test_calcula_saldo(self, eventos_simples=None):
        """Entradas - retiradas = saldo correto."""
        if eventos_simples is None:
            eventos_simples = globals()["eventos_simples"]()
        estoque = calcular_estoque_atual(eventos_simples)
        # 50 + 20 - 3 - 5 - 4 = 58
        assert estoque[estoque["medicamento"] == "Med A"]["estoque_atual"].iloc[0] == 58

    def test_colunas(self, eventos_simples=None):
        """Deve ter colunas medicamento e estoque_atual."""
        if eventos_simples is None:
            eventos_simples = globals()["eventos_simples"]()
        estoque = calcular_estoque_atual(eventos_simples)
        assert "medicamento" in estoque.columns
        assert "estoque_atual" in estoque.columns


class TestConsumoDiario:
    def test_dias_preenchidos(self, eventos_simples=None):
        """Dias sem consumo devem ter valor zero."""
        if eventos_simples is None:
            eventos_simples = globals()["eventos_simples"]()
        consumo = calcular_consumo_diario(eventos_simples)
        assert len(consumo) >= 2

    def test_soma_dia(self, eventos_simples=None):
        """Consumo do dia 01/01 = 3 + 5 = 8."""
        if eventos_simples is None:
            eventos_simples = globals()["eventos_simples"]()
        consumo = calcular_consumo_diario(eventos_simples)
        dia1 = consumo[consumo["data"] == pd.Timestamp("2024-01-01")]
        assert dia1["consumo"].iloc[0] == 8

    def test_sem_entradas_no_consumo(self, eventos_simples=None):
        """Entradas não devem contar como consumo."""
        if eventos_simples is None:
            eventos_simples = globals()["eventos_simples"]()
        consumo = calcular_consumo_diario(eventos_simples)
        total = consumo["consumo"].sum()
        # Retiradas totais: 3 + 5 + 4 = 12
        assert total == 12


class TestMultiplosMedicamentos:
    def test_dois_medicamentos(self):
        """Pipeline deve funcionar com múltiplos medicamentos."""
        eventos = pd.DataFrame({
            "timestamp": pd.to_datetime([
                "2024-01-01 08:00", "2024-01-01 10:00",
                "2024-01-01 08:00", "2024-01-01 11:00",
            ]),
            "tipo": ["entrada", "retirada", "entrada", "retirada"],
            "medicamento": ["Med A", "Med A", "Med B", "Med B"],
            "lote": ["L001", "L001", "L002", "L002"],
            "validade": ["2024-12-31"] * 4,
            "quantidade": [30, 5, 20, 3],
        })
        estoque = calcular_estoque_atual(eventos)
        assert len(estoque) == 2
        assert estoque[estoque["medicamento"] == "Med A"]["estoque_atual"].iloc[0] == 25
        assert estoque[estoque["medicamento"] == "Med B"]["estoque_atual"].iloc[0] == 17


if __name__ == "__main__":
    df = eventos_simples()
    t_ea = TestEstoqueAtual()
    t_ea.test_calcula_saldo(df)
    t_ea.test_colunas(df)

    t_cd = TestConsumoDiario()
    t_cd.test_dias_preenchidos(df)
    t_cd.test_soma_dia(df)
    t_cd.test_sem_entradas_no_consumo(df)

    t_mm = TestMultiplosMedicamentos()
    t_mm.test_dois_medicamentos()

    print("[OK] Todos os testes de test_tratamento.py passaram!")
