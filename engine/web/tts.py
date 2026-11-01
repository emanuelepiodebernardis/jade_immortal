"""
LE VOCI VERE (Aggiornamento 83) — sintesi vocale di qualità, in locale, con Piper (facoltativa).

Se nella cartella del gioco c'è `voci/` con l'eseguibile di Piper e i modelli italiani (li scarica
`python strumenti/installa_voci.py`), il narratore usa queste voci invece di quelle del browser: suonano come un
audiolibro. Senza la cartella non cambia nulla.

  stato()                       {"attivo": bool, "voci": {"m": nome, "f": nome}}
  sintetizza(testo, genere, velocita) -> bytes WAV (con una piccola cache su disco)

Nessuna rete: Piper gira sul tuo computer.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOCI = ROOT / "voci"
CACHE = VOCI / "cache"
MAX_CHARS = 600


def _exe() -> str | None:
    for name in ("piper.exe", "piper"):
        for p in (VOCI / "piper" / name, VOCI / name):
            if p.is_file():
                return str(p)
    return shutil.which("piper")


def _models() -> dict[str, Path]:
    out: dict[str, Path] = {}
    if not VOCI.is_dir():
        return out
    for f in sorted(VOCI.glob("*.onnx")):
        n = f.stem.lower()
        if not (n.startswith("it_it") or n.startswith("it-")):
            continue
        g = "f" if any(x in n for x in ("paola", "female", "donna")) else "m"
        out.setdefault(g, f)
    return out


def stato() -> dict:
    exe, m = _exe(), _models()
    return {"attivo": bool(exe and m), "voci": {g: p.stem for g, p in m.items()}}


def sintetizza(testo: str, genere: str = "m", velocita: float = 1.0) -> bytes | None:
    exe, models = _exe(), _models()
    if not exe or not models:
        return None
    testo = " ".join((testo or "").split())[:MAX_CHARS]
    if not testo:
        return None
    model = models.get("f" if genere == "f" else "m")
    if model is None:
        return None                                      # quella voce non c'è: il narratore usa quella del browser
    velocita = max(0.6, min(1.8, float(velocita or 1.0)))
    key = hashlib.sha1(f"{model.name}|{velocita:.2f}|{testo}".encode("utf-8")).hexdigest()
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{key}.wav"
    if out.is_file():
        return out.read_bytes()
    tmp = CACHE / f"{key}.tmp.wav"
    try:
        subprocess.run([exe, "--model", str(model), "--output_file", str(tmp), "--length_scale", f"{1.0 / velocita:.3f}"],
                       input=testo.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=30, check=True)
        os.replace(tmp, out)
        _trim_cache()
        return out.read_bytes()
    except Exception:                                    # noqa: BLE001 — senza voce si torna a quelle del browser
        try:
            tmp.unlink()
        except OSError:
            pass
        return None


def _trim_cache(limit: int = 400) -> None:
    files = sorted(CACHE.glob("*.wav"), key=lambda p: p.stat().st_mtime)
    for p in files[:-limit]:
        try:
            p.unlink()
        except OSError:
            pass
