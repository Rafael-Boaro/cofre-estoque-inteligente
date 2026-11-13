"""
Configurações globais do sistema de estoque inteligente.

Centraliza caminhos, parâmetros de previsão, prazos de entrega
e níveis de serviço para fácil ajuste.
"""
from pathlib import Path

# ── Caminhos ──────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_PROCESSED = RAIZ / "data" / "processed"
ARQUIVO_EVENTOS = DIR_RAW / "eventos_cofre.csv"
ARQUIVO_DB = DIR_RAW / "eventos_cofre.db"
ARQUIVO_ESTOQUE = DIR_PROCESSED / "estoque_atual.csv"
ARQUIVO_CONSUMO = DIR_PROCESSED / "consumo_diario.csv"
ARQUIVO_PREVISOES = DIR_PROCESSED / "previsoes.csv"
ARQUIVO_SUGESTOES = DIR_PROCESSED / "sugestoes_compra.csv"
ARQUIVO_ALERTAS = DIR_PROCESSED / "alertas.log"

# ── Medicamentos refrigerados de alto custo ───────────────
MEDICAMENTOS = [
    "Caneta GLP-1 A",
    "Insulina Basal B",
    "Imunobiológico C",
    "Anticorpo Monoclonal D",
    "Hormônio de Crescimento E",
    "Vacina Especial F",
]

# ── Prazo de entrega do fornecedor (dias) ─────────────────
PRAZO_ENTREGA = {
    "Caneta GLP-1 A": 5,
    "Insulina Basal B": 3,
    "Imunobiológico C": 7,
    "Anticorpo Monoclonal D": 7,
    "Hormônio de Crescimento E": 4,
    "Vacina Especial F": 5,
}

# ── Parâmetros de previsão e reposição ────────────────────
JANELA_MEDIA_MOVEL = 7          # dias para a média móvel
ALPHA_SUAVIZACAO = 0.3          # fator de suavização exponencial
HORIZONTE_PREVISAO = 14         # dias a prever
NIVEL_SERVICO_Z = 1.65          # z-score para ~95 % de nível de serviço
DIAS_COBERTURA_ALVO = 14        # dias de estoque desejado

# ── Simulador ────────────────────────────────────────────
DIAS_HISTORICO = 90             # dias de dados simulados
ESTOQUE_INICIAL = 60            # unidades de cada medicamento no dia 0
DIAS_ALERTA_VALIDADE = 30       # alerta de lotes vencendo em até N dias
