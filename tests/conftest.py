"""
Fixtures compartilhadas para a suite de testes.

Isola os testes de qualquer configuracao local presente em
.streamlit/secrets.toml, garantindo que apenas variaveis de ambiente
controladas pelo monkeypatch sejam consideradas.
"""
import os
from unittest.mock import patch

import pytest


def _obter_segredo_sem_streamlit(chave: str, padrao: str = "") -> str:
    """Versao de obter_segredo que ignora st.secrets, lendo apenas os.environ."""
    valor = os.environ.get(chave)
    if valor is not None and str(valor).strip():
        return str(valor).strip()
    return padrao


@pytest.fixture(autouse=True)
def isolar_secrets_do_streamlit():
    """Substitui obter_segredo em provedores e cliente_llm para nao ler st.secrets."""
    with patch("src.assistente.provedores.obter_segredo", side_effect=_obter_segredo_sem_streamlit):
        with patch("src.assistente.cliente_llm.obter_segredo", side_effect=_obter_segredo_sem_streamlit):
            yield
