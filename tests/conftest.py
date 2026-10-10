"""Configurazione comune dei test.

La narrazione LLM è OPZIONALE: i test devono comportarsi allo stesso modo sia che
in `config/settings.yaml` l'LLM sia acceso, sia che Ollama giri davvero sulla macchina.
Per questo la forziamo spenta in tutta la suite (prima un test risultava "rosso
atteso" quando l'LLM era attivo).
"""

from __future__ import annotations

import pytest

from engine.narrative import llm


@pytest.fixture(autouse=True)
def _llm_disabled(monkeypatch):
    real = llm.load_llm_config

    def _off(path=None):
        cfg = real(path)
        cfg["enabled"] = False
        return cfg

    monkeypatch.setattr(llm, "load_llm_config", _off)
