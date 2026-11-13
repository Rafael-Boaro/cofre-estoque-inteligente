# Cofre Estoque Inteligente

> Sistema de controle de estoque inteligente para cofre refrigerado de medicamentos de alto custo — **Hackathon Connect 7.0**

## O Problema

Farmácias que trabalham com medicamentos refrigerados de alto custo enfrentam:
- **Rupturas de estoque** por falta de previsibilidade
- **Perdas por validade** quando lotes vencem sem serem usados
- **Compras emergenciais** com custo elevado de frete
- **Controle manual** propenso a erros

## A Solução

Um sistema que integra o cofre refrigerado ao controle de estoque, com:

1. **Baixa automática** a cada retirada do cofre
2. **Previsão de demanda** por medicamento (média móvel + suavização exponencial)
3. **Sugestões de compra** inteligentes (ponto de pedido + estoque de segurança)
4. **Alertas** para o fornecedor (quando e quanto comprar) e para o dono da farmácia
5. **Controle FEFO** (First Expired, First Out) — lote que vence primeiro sai primeiro
6. **Detecção de anomalias** no consumo (possíveis desvios ou mudanças de demanda)
7. **Painel visual** para tomada de decisão

## Início Rápido

### 1. Criar ambiente virtual

```bash
cd cofre-estoque-inteligente
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Gerar dados simulados

```bash
python scripts/gerar_dados.py
```

### 4. Rodar o pipeline completo

```bash
python scripts/rodar_pipeline.py
```

### 5. Abrir o painel

```bash
streamlit run app/painel.py
```

## Estrutura do Projeto

```
cofre-estoque-inteligente/
├── README.md                    # Este arquivo
├── requirements.txt             # Dependências Python
├── .gitignore
├── data/
│   ├── raw/                     # Eventos simulados (CSV + SQLite)
│   └── processed/               # Estoque, consumo, previsões, sugestões
├── src/
│   ├── config.py                # Parâmetros centralizados
│   ├── coleta/
│   │   ├── simulador_cofre.py   # Gera eventos realistas
│   │   └── armazenamento.py     # Leitura/escrita CSV e SQLite
│   ├── tratamento/
│   │   └── pipeline.py          # Eventos → estoque + consumo diário
│   ├── previsao/
│   │   ├── modelos.py           # Média móvel e suavização exponencial
│   │   └── avaliacao.py         # Backtest e seleção do melhor modelo
│   ├── reposicao/
│   │   └── regras.py            # Ponto de pedido, estoque de segurança
│   ├── alertas/
│   │   └── notificador.py       # Mensagens simuladas (pronto para API real)
│   └── diferenciais/
│       ├── fefo.py              # First Expired, First Out
│       └── anomalias.py         # Detecção de consumo fora do padrão
├── app/
│   └── painel.py                # Painel Streamlit
├── scripts/
│   ├── gerar_dados.py           # Gera dados e salva em data/raw
│   └── rodar_pipeline.py        # Executa todo o fluxo
├── tests/
│   ├── test_reposicao.py
│   ├── test_tratamento.py
│   └── test_fefo.py
└── docs/
    └── arquitetura.md           # Documentação técnica
```

## Tecnologias

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| Dados | Pandas, NumPy |
| Previsão | statsmodels (SES) |
| Visualização | Plotly |
| Painel | Streamlit |
| Armazenamento | CSV + SQLite |
| Testes | pytest |

## Testes

```bash
pytest tests/ -v
```

## Licença

Projeto desenvolvido para o Hackathon Connect 7.0.
