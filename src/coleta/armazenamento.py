"""
Armazenamento de eventos em CSV e SQLite.

Funções para salvar e ler os eventos do cofre nos dois formatos,
facilitando a troca futura por um banco de produção.
"""
import sqlite3
from pathlib import Path

import pandas as pd

from src.config import ARQUIVO_EVENTOS, ARQUIVO_DB


def salvar_csv(df: pd.DataFrame, caminho: Path = ARQUIVO_EVENTOS) -> None:
    """Salva DataFrame de eventos em CSV."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False)
    print(f"[OK] Eventos salvos em {caminho} ({len(df)} registros)")


def carregar_csv(caminho: Path = ARQUIVO_EVENTOS) -> pd.DataFrame:
    """Carrega eventos de um CSV."""
    df = pd.read_csv(caminho, parse_dates=["timestamp"])
    return df


def salvar_sqlite(df: pd.DataFrame, caminho: Path = ARQUIVO_DB) -> None:
    """Salva DataFrame de eventos em SQLite."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(caminho))
    df.to_sql("eventos", conn, if_exists="replace", index=False)
    conn.close()
    print(f"[OK] Eventos salvos em {caminho} (SQLite)")


def carregar_sqlite(caminho: Path = ARQUIVO_DB) -> pd.DataFrame:
    """Carrega eventos do SQLite."""
    conn = sqlite3.connect(str(caminho))
    df = pd.read_sql("SELECT * FROM eventos", conn, parse_dates=["timestamp"])
    conn.close()
    return df
