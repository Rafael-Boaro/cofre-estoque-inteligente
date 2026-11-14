#!/usr/bin/env python3
"""
Executa a suíte de testes do projeto.
Tenta usar pytest se disponível; caso contrário, executa diretamente os módulos de teste.

Uso: python scripts/testar.py
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def main():
    print("[TESTES] Executando suíte de testes...")

    # Tenta rodar via pytest
    try:
        import pytest
        sys.exit(pytest.main(["tests", "-v"]))
    except ImportError:
        pass

    # Fallback: executa os módulos diretamente
    test_files = [
        RAIZ / "tests" / "test_reposicao.py",
        RAIZ / "tests" / "test_tratamento.py",
        RAIZ / "tests" / "test_fefo.py",
        RAIZ / "tests" / "test_assistente.py",
        RAIZ / "tests" / "test_provedores.py",
    ]

    total_passou = 0
    for tf in test_files:
        print(f"\n>> Rodando {tf.name}...")
        res = subprocess.run([sys.executable, str(tf)], capture_output=True, text=True)
        if res.returncode == 0:
            print(res.stdout.strip())
            total_passou += 1
        else:
            print(f"[ERRO] Falha em {tf.name}:")
            print(res.stderr)
            sys.exit(1)

    print(f"\n[OK] Sucesso! Todos os {total_passou} módulos de teste passaram com êxito!")


if __name__ == "__main__":
    main()
