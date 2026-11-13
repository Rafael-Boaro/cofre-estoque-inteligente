#!/usr/bin/env python3
"""
Gera dados simulados do cofre refrigerado e salva em data/raw.

Uso: python scripts/gerar_dados.py
"""
import sys
from pathlib import Path

# Garante que o import de 'src' funcione a partir de qualquer diretório
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.coleta.simulador_cofre import gerar_eventos
from src.coleta.armazenamento import salvar_csv, salvar_sqlite


def main() -> None:
    print("[INFO] Gerando eventos simulados do cofre refrigerado...")
    eventos = gerar_eventos(seed=42)

    print(f"   -> {len(eventos)} eventos gerados para {eventos['medicamento'].nunique()} medicamentos")
    print(f"   -> Periodo: {eventos['timestamp'].min().date()} a {eventos['timestamp'].max().date()}")

    salvar_csv(eventos)
    salvar_sqlite(eventos)

    print("\nResumo por tipo:")
    print(eventos.groupby("tipo")["quantidade"].agg(["count", "sum"]).to_string())
    print("\n[OK] Dados gerados com sucesso!")


if __name__ == "__main__":
    main()
