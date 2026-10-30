"""
Ritratti su misura per le persone che contano nella TUA partita (nemesi, rivali, compagni, fratelli giurati, famiglia).

    python strumenti/ritratti_importanti.py            # elenca nome file e prompt
    python strumenti/ritratti_importanti.py --link     # aggiunge il link Pollinations da aprire nel browser

Salva ogni immagine come immagini/ritratti/<nome_file>.jpg: il gioco la usa al posto del ritratto del suo tipo.
(Pollinations gratuito: un'immagine ogni ~45 secondi.)
"""
from __future__ import annotations

import sqlite3
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote

DB = Path(__file__).resolve().parent.parent / "database" / "world.db"
KINDS = ("rival", "nemesis", "companion", "sworn", "family", "master", "partner")
STYLE = (", Chinese ink wash painting on aged silk, xianxia donghua style, muted colors with jade and cinnabar accents, "
         "misty background, no text")
ROLE = {"rival": "proud rival", "nemesis": "menacing nemesis full of hatred", "companion": "loyal companion",
        "sworn": "sworn brother", "family": "family member", "master": "wise master", "partner": "beloved partner"}
ARCH = {"anziano": "elder about 70, white hair", "patriarca": "sect patriarch about 60, ornate robes, crown",
        "eremita": "hermit about 40, plain grey robes", "discepolo": "young disciple about 20, sect robes",
        "guardia": "guard about 35, armor, spear", "mercante": "merchant about 45, silk robes, abacus",
        "vagabondo": "wanderer about 30, straw hat, travel cloak", "cacciatore": "hunter about 35, fur cloak, bow"}


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().replace(" ", "_")


def main() -> None:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    q = (f"SELECT DISTINCT n.name, n.gender, n.archetype, b.kind FROM bonds b JOIN npcs n ON n.id=b.npc_id "
         f"WHERE n.status='alive' AND b.kind IN ({','.join('?' * len(KINDS))});")
    out = Path(__file__).resolve().parent.parent / "immagini" / "ritratti"
    for r in c.execute(q, KINDS):
        f = slug(r["name"])
        if (out / f"{f}.jpg").exists():
            continue
        who = ("an old WOMAN" if r["archetype"] in ("anziano", "patriarca") else "a WOMAN") if r["gender"] == "f" else \
            "a MAN, masculine face, strong jawline, thick eyebrows"
        p = f"portrait of {who}, {ARCH.get(r['archetype'] or '', 'cultivator')}, {ROLE.get(r['kind'], '')}{STYLE}"
        print(f"{f}.jpg  [{r['kind']}]\n  {p}")
        if "--link" in sys.argv:
            print(f"  https://image.pollinations.ai/prompt/{quote(p)}?width=512&height=558&nologo=true&model=flux")
        print()


if __name__ == "__main__":
    main()
