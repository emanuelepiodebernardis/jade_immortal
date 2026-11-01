"""
Installa le VOCI VERE del narratore: Piper (sintesi vocale locale, gratuita, open source) e due voci italiane
(Paola, femminile; Riccardo, maschile). Una volta sola; poi il gioco funziona anche senza Internet.

Uso (dalla cartella del gioco):
    python strumenti/installa_voci.py                 (Piper per il sistema su cui lo lanci)
    python strumenti/installa_voci.py --sistema windows   (scegli tu: windows, linux, mac)

Scarica da GitHub (rhasspy/piper, la versione 2023.11.14-2) e da Hugging Face (rhasspy/piper-voices) nella cartella
«voci/». Circa 90 MB in tutto. Riapri il gioco: il narratore userà queste voci da solo.
"""

from __future__ import annotations

import io
import platform
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOCI = ROOT / "voci"
REL = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/"
HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/"
MODELS = [("paola/medium/", "it_IT-paola-medium"), ("riccardo/x_low/", "it_IT-riccardo-x_low")]
# se Hugging Face non è raggiungibile: la voce maschile ufficiale pubblicata anche su GitHub (Piper v0.0.2)
GH_VOICE = "https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-it-riccardo_fasol-x-low.tar.gz"


def _get(url: str) -> bytes:
    print("  scarico", url)
    req = urllib.request.Request(url, headers={"User-Agent": "jade-immortal"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _piper_archive(forced: str = "") -> str:
    s, m = platform.system(), platform.machine().lower()
    if forced:
        s = {"windows": "Windows", "mac": "Darwin", "macos": "Darwin", "linux": "Linux"}.get(forced.lower(), s)
        m = "x86_64" if forced.lower() != "mac" else m
    if s == "Windows":
        return "piper_windows_amd64.zip"
    if s == "Darwin":
        return "piper_macos_aarch64.tar.gz" if m in ("arm64", "aarch64") else "piper_macos_x64.tar.gz"
    return "piper_linux_aarch64.tar.gz" if m in ("arm64", "aarch64") else "piper_linux_x86_64.tar.gz"


def main() -> int:
    forced = sys.argv[sys.argv.index("--sistema") + 1] if "--sistema" in sys.argv[:-1] else ""
    VOCI.mkdir(exist_ok=True)
    if not any((VOCI / "piper" / n).exists() for n in ("piper", "piper.exe")):
        name = _piper_archive(forced)
        data = _get(REL + name)
        if name.endswith(".zip"):
            zipfile.ZipFile(io.BytesIO(data)).extractall(VOCI)
        else:
            tarfile.open(fileobj=io.BytesIO(data), mode="r:gz").extractall(VOCI, filter="data")
        exe = VOCI / "piper" / "piper"
        if exe.exists():
            exe.chmod(0o755)
    got = 0
    for path, stem in MODELS:
        try:
            for ext in (".onnx", ".onnx.json"):
                f = VOCI / (stem + ext)
                if not f.exists():
                    f.write_bytes(_get(HF + path + stem + ext))
            got += 1
        except Exception as e:                           # noqa: BLE001
            print(f"  (non riesco a scaricare {stem}: {e})")
    if not got and not list(VOCI.glob("it-riccardo*.onnx")):
        print("  Hugging Face non risponde: prendo la voce maschile da GitHub.")
        tarfile.open(fileobj=io.BytesIO(_get(GH_VOICE)), mode="r:gz").extractall(VOCI, filter="data")
    print("Fatto. Le voci sono in", VOCI)
    voci = sorted(f.stem for f in VOCI.glob("*.onnx"))
    print("Voci installate:", ", ".join(voci) or "nessuna")
    print("Riapri il gioco e accendi il narratore (🔈): userà queste voci (le altre restano quelle del browser).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
