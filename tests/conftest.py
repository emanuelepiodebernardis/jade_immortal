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


@pytest.fixture(autouse=True)
def _npc_bodies_neutral(monkeypatch):
    """I corpi leggendari degli NPC (+20% in combattimento) sono assegnati per mondo: nei test che
    confrontano le forze li neutralizziamo; i test dei corpi chiamano npc_body direttamente."""
    from engine.systems import body_absorb
    monkeypatch.setattr(body_absorb, "npc_mult", lambda conn, npc_id: 1.0)
