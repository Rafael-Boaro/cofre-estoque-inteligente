"""
Testes para o módulo de reposição de estoque.
Executável via pytest ou python diretamente.
"""
import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        def approx(expected, rel=1e-6, abs=None):
            class ApproxVal:
                def __eq__(self, actual):
                    return math.isclose(actual, expected, rel_tol=rel)
                def __repr__(self):
                    return f"approx({expected})"
            return ApproxVal()
        @staticmethod
        def fixture(func):
            return func
    pytest = _MockPytest()

import numpy as np
import pandas as pd

from src.reposicao.regras import (
    calcular_estoque_seguranca,
    calcular_ponto_pedido,
    calcular_quantidade_sugerida,
    calcular_dias_cobertura,
    gerar_sugestoes,
)


class TestEstoqueSeguranca:
    def test_valor_positivo(self):
        """Estoque de segurança deve ser positivo com desvio > 0."""
        es = calcular_estoque_seguranca(desvio_consumo=2.0, prazo_entrega=5)
        assert es > 0

    def test_proporcional_ao_desvio(self):
        """Dobrar o desvio deve dobrar o estoque de segurança."""
        es1 = calcular_estoque_seguranca(desvio_consumo=1.0, prazo_entrega=5)
        es2 = calcular_estoque_seguranca(desvio_consumo=2.0, prazo_entrega=5)
        assert pytest.approx(es2, rel=1e-6) == es1 * 2

    def test_desvio_zero(self):
        """Sem variação, estoque de segurança deve ser zero."""
        es = calcular_estoque_seguranca(desvio_consumo=0.0, prazo_entrega=5)
        assert es == 0.0


class TestPontoPedido:
    def test_formula(self):
        """Ponto de pedido = consumo_medio * prazo + estoque_seguranca."""
        pp = calcular_ponto_pedido(consumo_medio=5.0, prazo_entrega=3, estoque_seguranca=10.0)
        assert pp == 5.0 * 3 + 10.0

    def test_sem_seguranca(self):
        """Sem estoque de segurança, PP = consumo * prazo."""
        pp = calcular_ponto_pedido(consumo_medio=4.0, prazo_entrega=7, estoque_seguranca=0.0)
        assert pp == 28.0


class TestQuantidadeSugerida:
    def test_cobertura_14_dias(self):
        """Com consumo 5/dia e 14 dias de cobertura, sugerir 70."""
        qtd = calcular_quantidade_sugerida(consumo_medio=5.0, dias_cobertura=14)
        assert qtd == 70.0


class TestDiasCobertura:
    def test_calculo_simples(self):
        """100 unidades com consumo 5/dia = 20 dias."""
        dias = calcular_dias_cobertura(estoque_atual=100, consumo_medio=5.0)
        assert dias == 20.0

    def test_consumo_zero(self):
        """Consumo zero deve retornar infinito."""
        dias = calcular_dias_cobertura(estoque_atual=50, consumo_medio=0.0)
        assert dias == float("inf")


class TestGerarSugestoes:
    def test_retorna_dataframe_correto(self):
        """Deve retornar DataFrame com colunas esperadas."""
        estoque = pd.DataFrame({
            "medicamento": ["Med A", "Med B"],
            "estoque_atual": [10, 100],
        })
        consumo = pd.DataFrame({
            "data": pd.date_range("2024-01-01", periods=60).tolist() * 2,
            "medicamento": ["Med A"] * 60 + ["Med B"] * 60,
            "consumo": [3] * 60 + [2] * 60,
        })
        previsoes = pd.DataFrame({
            "medicamento": ["Med A"] * 14 + ["Med B"] * 14,
            "dia": list(range(1, 15)) * 2,
            "previsao": [3.0] * 14 + [2.0] * 14,
            "modelo": ["media_movel"] * 28,
        })

        sugestoes = gerar_sugestoes(estoque, consumo, previsoes)

        assert "precisa_comprar" in sugestoes.columns
        assert len(sugestoes) == 2
        med_a = sugestoes[sugestoes["medicamento"] == "Med A"].iloc[0]
        assert bool(med_a["precisa_comprar"]) is True


if __name__ == "__main__":
    t_es = TestEstoqueSeguranca()
    t_es.test_valor_positivo()
    t_es.test_proporcional_ao_desvio()
    t_es.test_desvio_zero()

    t_pp = TestPontoPedido()
    t_pp.test_formula()
    t_pp.test_sem_seguranca()

    t_qs = TestQuantidadeSugerida()
    t_qs.test_cobertura_14_dias()

    t_dc = TestDiasCobertura()
    t_dc.test_calculo_simples()
    t_dc.test_consumo_zero()

    t_gs = TestGerarSugestoes()
    t_gs.test_retorna_dataframe_correto()

    print("[OK] Todos os testes de test_reposicao.py passaram!")
