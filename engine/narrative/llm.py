"""
Client LLM (Ollama) per il narrative engine (Fase 9).

GRACEFUL: se l'LLM è disabilitato in config, o Ollama non è raggiungibile, o la
chiamata fallisce, `generate` ritorna None. Il renderer userà allora il fallback
deterministico, così il gioco funziona anche senza LLM.

Usa solo la stdlib (urllib) — nessuna dipendenza extra. Punta a Ollama in locale
sulla macchina dell'utente (es. http://localhost:11434).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

DEFAULTS = {
    "provider": "ollama",
    "model": "qwen3:8b",
    "host": "http://localhost:11434",
    "enabled": False,
}


def load_llm_config(path: Path | str | None = None) -> dict:
    from engine.db import PROJECT_ROOT
    path = Path(path) if path else PROJECT_ROOT / "config" / "settings.yaml"
    cfg = dict(DEFAULTS)
    if not path.exists():
        return cfg
    try:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        llm = data.get("llm", {}) or {}
        cfg.update({k: llm[k] for k in DEFAULTS if k in llm})
    except Exception:
        pass
    return cfg


def is_enabled(cfg: dict | None = None) -> bool:
    cfg = cfg or load_llm_config()
    return bool(cfg.get("enabled"))


def generate(system: str, prompt: str, cfg: dict | None = None,
             timeout: float = 30.0) -> str | None:
    """Chiama Ollama. Ritorna il testo, o None se disabilitato/non raggiungibile."""
    cfg = cfg or load_llm_config()
    if not cfg.get("enabled"):
        return None
    url = cfg["host"].rstrip("/") + "/api/generate"
    body = json.dumps({
        "model": cfg["model"],
        "system": system,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = (data.get("response") or "").strip()
        return text or None
    except Exception:
        return None
