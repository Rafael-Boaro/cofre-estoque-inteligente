# Cofre Estoque Inteligente

Sistema de controle de estoque inteligente para cofre refrigerado de medicamentos de alto custo com previsao de demanda, reposicao automatizada e regras FEFO. Projeto desenvolvido no ambito do Hackathon Connect 7.0.

## Apresentacao do Projeto

A apresentacao oficial com a proposta conceitual, modelo de negocio e arquitetura da solucao esta disponivel no arquivo PDF do repositorio:

- [Apresentacao do Projeto (PDF)](./Cofre%20Estoque%20Inteligente.pdf)

## Visao Geral

### O Problema
Farmacias e hospitais que gerenciam medicamentos refrigerados de alto custo (como insulinas especiais, imunobiologicos e canetas GLP-1) enfrentam desafios criticos na cadeia de suprimentos:
- Rupturas de estoque por falta de previsibilidade de demanda.
- Perdas financeiras decorrentes do vencimento de lotes armazenados.
- Compras emergenciais com custos elevados de frete e risco de desabastecimento.
- Falhas decorrentes de controles manuais e registros descentralizados.

### A Solucao
Integracao entre o cofre refrigerado inteligente e o sistema de gestao de estoque:
- Baixa automatica a cada evento de retirada ou abastecimento do cofre.
- Previsao de demanda baseada no historico de consumo diario (Media Movel e Suavizacao Exponencial Simples).
- Sugestoes automaticas de reposicao considerando ponto de pedido e estoque de seguranca com nivel de servico estipulado.
- Controle rigoroso FEFO (First Expired, First Out) para priorizar lotes com menor prazo de validade.
- Deteccao de anomalias estatisticas no consumo diario via z-score.
- Painel analitico para tomada de decisao operacional e gerencial.

## Funcionalidades

- Registro e simulacao de eventos de cofre (entradas e retiradas com lote e validade).
- Processamento e agregacao de dados de estoque atual e consumo historico.
- Selecao automatica do melhor modelo de previsao por medicamento via backtesting (menor MAPE).
- Calculo de ponto de pedido, estoque de seguranca e dias de cobertura.
- Deteccao preventiva de lotes proximos do vencimento (30 dias).
- Deteccao de anomalias de consumo para investigacao de perdas ou picos incomuns.
- Simulacao de disparos de alertas para fornecedores e gestores.
- Painel visual interativo em Streamlit com graficos analiticos.

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| Manipulacao e Analise de Dados | Pandas, NumPy |
| Modelagem e Previsao | statsmodels (SimpleExpSmoothing) |
| Interface e Dashboard | Streamlit |
| Visualizacao de Graficos | Plotly |
| Armazenamento Local | CSV e SQLite |
| Suite de Testes | pytest |

## Estrutura do Projeto

```
cofre-estoque-inteligente/
|-- Cofre Estoque Inteligente.pdf # Apresentacao do projeto
|-- README.md                    # Documentacao principal
|-- requirements.txt             # Dependencias do projeto
|-- .gitignore                   # Regras de exclusao Git
|-- .gitattributes               # Normalizacao de quebras de linha e binarios
|-- data/
|   |-- raw/                     # Eventos brutos simulados (CSV e SQLite)
|   |   `-- eventos_cofre.csv    # Dados de exemplo de eventos
|   `-- processed/               # Dados processados pelo pipeline
|       |-- estoque_atual.csv    # Saldo consolidado por medicamento
|       |-- consumo_diario.csv   # Serie temporal de consumo diario
|       |-- previsoes.csv        # Projecao de demanda para 14 dias
|       |-- sugestoes_compra.csv # Ponto de pedido e quantidade sugerida
|       |-- saldo_lotes.csv      # Posicao de estoque por lote e validade
|       `-- anomalias.csv        # Registros de anomalias detectadas
|-- src/
|   |-- config.py                # Parametros globais e caminhos
|   |-- coleta/
|   |   |-- simulador_cofre.py   # Gerador de eventos sinteticos
|   |   `-- armazenamento.py     # Operacoes de persistencia CSV/SQLite
|   |-- tratamento/
|   |   `-- pipeline.py          # Consolidacao de eventos em estoque e consumo
|   |-- previsao/
|   |   |-- modelos.py           # Algoritmos de previsao de series temporais
|   |   `-- avaliacao.py         # Selecao de modelos por MAPE
|   |-- reposicao/
|   |   `-- regras.py            # Calculo de estoque de seguranca e reposicao
|   |-- alertas/
|   |   `-- notificador.py       # Gerador de notificacoes operacionais
|   `-- diferenciais/
|       |-- fefo.py              # Logica de ordenacao FEFO e validade
|       `-- anomalias.py         # Inferencia estatistica de anomalias
|-- app/
|   `-- painel.py                # Aplicacao web Streamlit
|-- scripts/
|   |-- gerar_dados.py           # Script para geracao de dados simulados
|   |-- rodar_pipeline.py        # Script de execucao do pipeline completo
|   `-- testar.py                # Executor auxiliar da suite de testes
|-- tests/
|   |-- test_fefo.py             # Testes unitarios de regras FEFO
|   |-- test_reposicao.py        # Testes unitarios de reposicao
|   `-- test_tratamento.py       # Testes unitarios do pipeline de tratamento
`-- docs/
    `-- arquitetura.md           # Especificacao tecnica de arquitetura
```

## Instalacao e Execucao

### Clonar o Repositorio

```bash
git clone https://github.com/Rafael-Boaro/cofre-estoque-inteligente.git
cd cofre-estoque-inteligente
```

### No Linux (Ubuntu / Linux Mint) - Bash

```bash
# 1. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Gerar dados simulados (opcional se usar os dados de exemplo incluidos)
python scripts/gerar_dados.py

# 4. Executar o pipeline de tratamento e previsao
python scripts/rodar_pipeline.py

# 5. Iniciar o painel analitico
streamlit run app/painel.py
```

### No Windows - PowerShell

```powershell
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Gerar dados simulados (opcional se usar os dados de exemplo incluidos)
python scripts/gerar_dados.py

# 4. Executar o pipeline de tratamento e previsao
python scripts/rodar_pipeline.py

# 5. Iniciar o painel analitico
streamlit run app/painel.py
```

## Decisoes Tecnicas

- **Persistencia em CSV e SQLite**: O simulador grava tanto em arquivos CSV (para facilitar inspecao e interoperabilidade) quanto em SQLite, simulando uma estrutura relacional pronta para conexao com bancos corporativos.
- **Previsao Adaptativa**: Utilizacao de Media Movel e Suavizacao Exponencial Simples (SES via `statsmodels`), avaliadas via backtesting com selecao automatica do menor erro (MAPE) para cada medicamento individualmente.
- **Algoritmo FEFO**: O consumo e a saida fisica de medicamentos priorizam os lotes com prazo de expiracao mais curto, mitigando o risco de perda por vencimento de itens refrigerados de alto valor.
- **Deteccao de Anomalias Estatistica**: Metodo de z-score aplicado ao historico de consumo diario para identificar variacoes bruscas decorrentes de desvios, furtos ou surtos de demanda.
- **Painel Interativo em Streamlit**: Interface rapida para exibicao de metricas operacionais (dias de cobertura, recomendacoes de compra e alertas criticos) sem complexidade de infraestrutura de frontend.

## Testes

Para executar a suite de testes automatizados com o ambiente virtual ativo:

```bash
python scripts/testar.py
```

## Licenca

Projeto desenvolvido sob a licenca MIT. Consulte o arquivo [LICENSE](./LICENSE) para mais detalhes.
