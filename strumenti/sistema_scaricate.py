"""Sposta le immagini scaricate dal generatore (Download/<cartella>__<nome>.jpg) nelle cartelle del gioco,
tagliando il logo del generatore in basso a destra. Uso: python strumenti/sistema_scaricate.py <cartella Download>"""
import sys
from pathlib import Path
from PIL import Image

src = Path(sys.argv[1])
root = Path(__file__).resolve().parents[1] / "immagini"
for f in sorted(src.glob("*__*.jpg")):
    if f.name.startswith("ji3__"):
        continue
    d, n = f.stem.split("__", 1)
    if d not in ("ritratti", "scene", "momenti", "oggetti", "azioni", "stati", "luoghi"):
        continue
    im = Image.open(f).convert("RGB")
    w, h = im.size
    cut = int(h * 0.075)                          # il logo sta negli ultimi ~7% in basso
    if w == h:
        im = im.crop((cut // 2, 0, w - cut // 2, h - cut))
    else:
        im = im.crop((0, 0, w, h - cut))
    out = root / d / (n + ".jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        continue
    im.save(out, quality=90)
    print("ok", out.relative_to(root))
