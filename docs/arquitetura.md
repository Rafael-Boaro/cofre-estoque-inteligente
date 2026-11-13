# Arquitetura — Cofre Estoque Inteligente

## Diagrama do Fluxo

```
┌─────────────────────────────────────────────────────────────────┐
│                    COFRE REFRIGERADO                             │
│  (evento: medicamento, lote, validade, quantidade, timestamp)   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   1. COLETA DE DADOS  │
                │   CSV / SQLite        │
                │   simulador_cofre.py  │
                │   armazenamento.py    │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   2. TRATAMENTO       │
                │   pipeline.py         │
                │   • Estoque atual     │
                │   • Consumo diário    │
                └───────────┬───────────┘
                            │
                    ┌───────┴───────┐
                    ▼               ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ 3. PREVISÃO      │  │  DIFERENCIAIS    │
        │ modelos.py       │  │  fefo.py         │
        │ avaliacao.py     │  │  anomalias.py    │
        │ • Média móvel    │  │  • FEFO          │
        │ • Suav. expon.   │  │  • Z-score       │
        └────────┬─────────┘  └────────┬─────────┘
                 │                     │
                 └──────────┬──────────┘
                            ▼
                ┌───────────────────────┐
                │   4. REPOSIÇÃO        │
                │   regras.py           │
                │   • Ponto de pedido   │
                │   • Est. segurança    │
                │   • Qtd. sugerida     │
                │   • Dias de cobertura │
                └───────────┬───────────┘
                            │
                    ┌───────┴───────┐
                    ▼               ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ 5. ALERTAS       │  │  6. PAINEL       │
        │ notificador.py   │  │  painel.py       │
        │ • Fornecedor     │  │  • KPIs          │
        │ • Dono farmácia  │  │  • Gráficos      │
        │ (WhatsApp/e-mail │  │  • Sugestões     │
        │  simulados)      │  │  • FEFO/Anomal.  │
        └──────────────────┘  └──────────────────┘
```

## Explicação de Cada Camada

### 1. Coleta de Dados
- **Simulador** (`simulador_cofre.py`): gera 90 dias de eventos realistas para 6 medicamentos, com sazonalidade semanal (maior consumo em dias úteis), picos aleatórios (~5% dos dias), múltiplos lotes com validades diferentes, e reposições periódicas.
- **Armazenamento** (`armazenamento.py`): abstrai leitura/escrita em CSV e SQLite. Trocar para PostgreSQL requer alterar apenas este módulo.

### 2. Tratamento
- **Pipeline** (`pipeline.py`): transforma os eventos brutos em duas tabelas:
  - **Estoque atual**: soma entradas − retiradas por medicamento
  - **Consumo diário**: total de retiradas por dia por medicamento, preenchendo dias sem movimento com zero

### 3. Motor de Previsão
- **Modelos** (`modelos.py`): implementa duas abordagens:
  - **Média Móvel Simples**: usa os últimos N dias para estimar a demanda futura (previsão constante)
  - **Suavização Exponencial Simples (SES)**: dá mais peso aos dados recentes via fator alpha
- **Avaliação** (`avaliacao.py`): backtest com split 80/20 temporal. Compara MAE e MAPE dos dois modelos e escolhe o melhor por medicamento.

### 4. Regras de Reposição
- **Estoque de segurança**: `z × desvio_padrão × √prazo_entrega` (z = 1,65 para 95% de nível de serviço)
- **Ponto de pedido**: `consumo_médio × prazo_entrega + estoque_segurança`
- **Quantidade sugerida**: `consumo_médio × dias_cobertura_alvo`
- **Data limite**: quando o estoque projetado atinge o ponto de pedido menos o prazo de entrega

### 5. Alertas
- Interface `CanalNotificacao` com método `enviar(destinatario, mensagem)`. A implementação atual (`CanalSimulado`) imprime e grava em log. Para integrar WhatsApp/e-mail, basta criar uma nova classe que implemente a mesma interface.

### 6. Painel Streamlit
- Tela única com: KPIs no topo, gráficos de estoque e cobertura, tabela de sugestões de compra, lotes FEFO, gráfico de consumo+previsão por medicamento, anomalias detectadas.

## Diferenciais

### FEFO (First Expired, First Out)
Rastreia o saldo por lote e ordena pela validade. Alerta sobre lotes que vencem nos próximos 30 dias para evitar perdas.

### Detecção de Anomalias
Z-score sobre a série de consumo diário de cada medicamento. Consumos com z > 2.5 são marcados como pico; z < -2.5 como queda. Ajuda a identificar desvios, fraudes ou mudanças bruscas de demanda.

---

## Do Protótipo à Produção

### Banco de Dados
- **Hoje**: CSV + SQLite (protótipo, zero custo)
- **Produção**: PostgreSQL ou MySQL com esquema normalizado (tabelas `medicamentos`, `lotes`, `eventos`, `previsoes`)
- **Migração**: alterar apenas `armazenamento.py` para usar SQLAlchemy

### Coleta de Dados
- **Hoje**: simulador + CSV
- **Produção**: API REST (FastAPI) ou MQTT para receber eventos em tempo real do cofre. Cada abertura/fechamento gera um evento automaticamente.

### Alertas
- **Hoje**: print + log
- **Produção**: integração com API de WhatsApp Business (ex.: Twilio) e/ou e-mail via SendGrid/SES. A interface `CanalNotificacao` foi projetada para essa troca.

### Previsão
- **Hoje**: média móvel + SES (baseline)
- **Produção**: Prophet, ARIMA ou LSTM para capturar sazonalidade mensal, feriados e tendências de longo prazo. O módulo `avaliacao.py` já faz backtest comparativo.

### Orquestração
- **Hoje**: script manual (`rodar_pipeline.py`)
- **Produção**: Airflow ou Prefect executando o pipeline diariamente, com alertas de falha.

### Generalização
O sistema não depende de medicamentos. A mesma arquitetura serve para:
- Cosméticos refrigerados
- Alimentos perecíveis (redes de restaurantes)
- Vacinas em clínicas e UBS
- Qualquer estoque com restrição de temperatura e validade

### Viabilidade Financeira
- **Custo do protótipo**: zero (Python + SQLite + Streamlit Cloud gratuito)
- **Custo em produção**: ~R$50–200/mês (PostgreSQL gerenciado + VPS + API WhatsApp) — muito inferior ao custo de uma única ruptura ou perda por validade de um medicamento de alto custo (R$500–5.000+/unidade).
