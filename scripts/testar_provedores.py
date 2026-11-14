#!/usr/bin/env python3
"""
Validação operacional de múltiplos provedores de LLM configurados.

Executa uma pergunta curta de validação com o contexto real de estoque para
cada provedor configurado, medindo latência e capturando erros sem expor credenciais.

Uso: python scripts/testar_provedores.py
"""
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.assistente.contexto import montar_contexto
from src.assistente.provedores import provedores_configurados
from src.assistente.cliente_llm import responder


def main() -> int:
    print("=" * 80)
    print("  TESTE DE PROVEDORES DE LLM — COFRE ESTOQUE INTELIGENTE")
    print("=" * 80)

    configurados = provedores_configurados()

    if not configurados:
        print("\n[AVISO] Nenhum provedor de LLM possui chave de API configurada.")
        print("Para testar, configure ao menos um provedor em .streamlit/secrets.toml")
        print("ou como variavel de ambiente (ex: GROQ_API_KEY, GEMINI_API_KEY, etc).\n")
        print("Consulte o arquivo .streamlit/secrets.toml.example para instruções.")
        return 0

    print(f"\n[INFO] {len(configurados)} provedor(es) configurado(s): {', '.join(configurados.keys())}")
    print("[INFO] Montando contexto real a partir das tabelas processadas...")
    contexto = montar_contexto()

    pergunta = "Resuma o estoque em uma frase."
    prompt_sistema = (
        "Voce e o assistente de estoque. Responda em apenas uma frase curta, "
        "baseando-se exclusivamente nos numeros fornecidos no CONTEXTO."
    )

    resultados = []

    print("\nExecutando teste individual por provedor:")
    print("-" * 80)

    for pid, info in configurados.items():
        nome = info["nome"]
        modelo = info["modelo"]
        print(f"\n>> Testando {nome} (modelo: {modelo})...")

        t_inicio = time.perf_counter()
        resposta = responder(
            system_prompt=prompt_sistema,
            mensagens=[{"role": "user", "content": pergunta}],
            contexto=contexto,
            provedor=pid,
        )
        tempo_decorrido = time.perf_counter() - t_inicio

        # Avalia se a resposta veio com sucesso do provedor solicitado
        if resposta.provedor_usado == pid:
            status = "OK"
            detalhe = resposta.texto.replace("\n", " ").strip()
            if len(detalhe) > 60:
                detalhe = detalhe[:57] + "..."
            print(f"   [OK] Resposta em {tempo_decorrido:.2f}s: \"{detalhe}\"")
        else:
            status = "FALHA"
            if resposta.tentativas_falhas:
                detalhe = resposta.tentativas_falhas[0][1]
            else:
                detalhe = "Resposta vazia ou provedor nao acionado"
            print(f"   [FALHA] Motivo: {detalhe} ({tempo_decorrido:.2f}s)")

        resultados.append({
            "provedor": nome,
            "modelo": modelo,
            "tempo": f"{tempo_decorrido:.2f}s",
            "status": status,
            "detalhe": detalhe,
        })

    # Tabela consolidada final
    print("\n" + "=" * 80)
    print("  RESUMO DA DISPONIBILIDADE DOS PROVEDORES")
    print("=" * 80)
    cabecalho = f"{'Provedor':<24} {'Modelo':<30} {'Tempo':<10} {'Status':<8} {'Detalhe'}"
    print(cabecalho)
    print("-" * 80)

    for r in resultados:
        print(
            f"{r['provedor']:<24} "
            f"{r['modelo']:<30} "
            f"{r['tempo']:<10} "
            f"{r['status']:<8} "
            f"{r['detalhe']}"
        )

    print("=" * 80 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
