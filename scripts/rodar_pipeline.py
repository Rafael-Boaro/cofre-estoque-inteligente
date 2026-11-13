#!/usr/bin/env python3
"""
Executa o pipeline completo: tratamento → previsão → reposição → alertas.

Uso: python scripts/rodar_pipeline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.coleta.armazenamento import carregar_csv
from src.tratamento.pipeline import executar_pipeline
from src.previsao.modelos import prever_demanda
from src.reposicao.regras import gerar_sugestoes
from src.diferenciais.fefo import calcular_saldo_por_lote, lotes_proximos_vencimento
from src.diferenciais.anomalias import detectar_anomalias_zscore
from src.alertas.notificador import notificar_compras, notificar_validades, notificar_anomalias
from src.config import ARQUIVO_PREVISOES, DIR_PROCESSED


def main() -> None:
    print("=" * 60)
    print("  PIPELINE DE ESTOQUE INTELIGENTE — COFRE REFRIGERADO")
    print("=" * 60)

    # 1. Carregar eventos
    print("\n[1/7] Carregando eventos do cofre...")
    eventos = carregar_csv()
    print(f"   -> {len(eventos)} eventos carregados")

    # 2. Tratamento
    print("\n[2/7] Executando tratamento de dados...")
    estoque, consumo = executar_pipeline(eventos)
    print(f"   -> Estoque calculado para {len(estoque)} medicamentos")
    print(f"   -> Consumo diário: {len(consumo)} registros")

    # 3. Previsão
    print("\n[3/7] Gerando previsões de demanda...")
    previsoes = prever_demanda(consumo)
    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    previsoes.to_csv(ARQUIVO_PREVISOES, index=False)
    print(f"   -> Previsões geradas para {previsoes['medicamento'].nunique()} medicamentos")
    print(f"   -> Modelos escolhidos:")
    for med in previsoes["medicamento"].unique():
        modelo = previsoes[previsoes["medicamento"] == med]["modelo"].iloc[0]
        print(f"     * {med}: {modelo}")

    # 4. Reposição
    print("\n[4/7] Calculando sugestões de reposição...")
    sugestoes = gerar_sugestoes(estoque, consumo, previsoes)
    print("\n   Resumo das sugestões:")
    for _, row in sugestoes.iterrows():
        status = "[COMPRAR]" if row["precisa_comprar"] else "[OK]     "
        print(
            f"     {status} {row['medicamento']}: "
            f"estoque={row['estoque_atual']}, "
            f"cobertura={row['dias_cobertura']} dias, "
            f"sugestão={row['qtd_sugerida']} un."
        )

    # 5. FEFO — Lotes próximos do vencimento
    print("\n[5/7] Verificando lotes próximos do vencimento (FEFO)...")
    saldo_lotes = calcular_saldo_por_lote(eventos)
    proximos = lotes_proximos_vencimento(saldo_lotes)
    if not proximos.empty:
        print(f"   -> {len(proximos)} lote(s) com vencimento próximo:")
        for _, row in proximos.iterrows():
            print(
                f"     [ALERTA] {row['medicamento']} — Lote {row['lote']} "
                f"vence em {row['dias_para_vencer']} dias (saldo: {row['saldo_lote']} un.)"
            )
    else:
        print("   -> Nenhum lote com vencimento próximo.")

    # Salvar saldo de lotes para o painel
    saldo_lotes.to_csv(DIR_PROCESSED / "saldo_lotes.csv", index=False)

    # 6. Anomalias
    print("\n[6/7] Detectando anomalias de consumo...")
    anomalias = detectar_anomalias_zscore(consumo)
    if not anomalias.empty:
        anomalias.to_csv(DIR_PROCESSED / "anomalias.csv", index=False)
        print(f"   -> {len(anomalias)} anomalia(s) detectada(s)")
    else:
        print("   -> Nenhuma anomalia detectada.")

    # 7. Alertas
    print("\n[7/7] Enviando alertas simulados...")
    print("-" * 40)
    notificar_compras(sugestoes)
    notificar_validades(proximos)
    notificar_anomalias(anomalias)
    print("-" * 40)

    print("\n" + "=" * 60)
    print("  [OK] PIPELINE CONCLUIDO COM SUCESSO!")
    print("=" * 60)
    print(f"\n  Arquivos gerados em: {DIR_PROCESSED}/")
    print("  Para visualizar: streamlit run app/painel.py")


if __name__ == "__main__":
    main()
