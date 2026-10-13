"""
Scarica le immagini del gioco dalla collezione di Wikimedia Commons (grandi dipinti cinesi classici:
paesaggi Song, immortali, draghi, fenici, dame di corte…) e le mette nelle cartelle di «immagini/».

Si lancia DAL TUO PC (serve internet):

    python strumenti/scarica_immagini.py            scarica ciò che manca
    python strumenti/scarica_immagini.py --tutto    riscarica tutto
    python strumenti/scarica_immagini.py --elenco   mostra cosa cercherebbe, senza scaricare

Ogni «posto» del gioco ha una ricerca: lo script prende il primo risultato di Commons, lo salva
(largo 1024 pixel) e annota titolo, autore e licenza in immagini/CREDITI.txt.
Non ti piace un'immagine? Cancellala e mettine una tua con lo stesso nome (qualsiasi formato tra
png, jpg, webp): il gioco usa quella. Puoi anche cambiare le ricerche qui sotto.

Solo libreria standard di Python.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "immagini"
API = "https://commons.wikimedia.org/w/api.php"
UA = "JadeImmortal/1.0 (gioco personale; script di download delle immagini)"
WIDTH = 1024

# cartella/nome  ->  ricerca su Wikimedia Commons
SLOTS = {
    # i luoghi (sfondo del riquadro del luogo e dell'arena)
    "luoghi/city": "Along the River During the Qingming Festival",
    "luoghi/mountain": "Travelers Among Mountains and Streams Fan Kuan",
    "luoghi/ruin": "Buddhist Temple in the Hills after Rain Li Cheng",
    "luoghi/forbidden_zone": "Early Spring Guo Xi",
    # i mondi (sfondo della mappa)
    "mondi/0": "A Thousand Li of Rivers and Mountains Wang Ximeng",
    "mondi/1": "Immortals in a Mountain Pavilion",
    "mondi/2": "Spring Dawn in the Han Palace Qiu Ying",
    "mondi/3": "Peach Blossom Spring Qiu Ying",
    # ritratti per tipo di personaggio (se non c'è un ritratto col suo nome)
    "ritratti/patriarca": "Laozi riding an ox painting",
    "ritratti/anziano": "Immortal in Splashed Ink Liang Kai",
    "ritratti/eremita": "Li Bai Strolling Liang Kai",
    "ritratti/discepolo": "Portrait of a scholar Ming dynasty hanging scroll",
    "ritratti/guardia": "Guan Yu Captures Pang De Shang Xi",
    "ritratti/mercante": "Qingming scroll detail market",
    "ritratti/vagabondo": "Hanshan and Shide painting",
    "ritratti/cacciatore": "Kublai Khan hunting Liu Guandao",
    "ritratti/f": "Court Ladies Preparing Newly Woven Silk",
    "ritratti/f_anziana": "Nymph of the Luo River Gu Kaizhi",
    "ritratti/eroe": "Lü Dongbin Daoist immortal painting",
    # creature
    "creature/beast": "Tiger Chinese ink painting Qing dynasty",
    "creature/demon": "Zhong Kui painting",
    "creature/spirit": "Nymph of the Luo River Gu Kaizhi scroll",
    # bestie leggendarie (per nome: drago, fenice, tigre…)
    "bestie/drago": "Nine Dragons Chen Rong",
    "bestie/fenice": "fenghuang Chinese painting",
    "bestie/tigre": "Tiger painting Chinese hanging scroll",
    "bestie/tartaruga": "Black Tortoise Xuanwu",
    "bestie/qilin": "qilin Chinese painting",
    "bestie/gru": "Auspicious Cranes Emperor Huizong",
    "bestie/volpe": "nine-tailed fox Shan Hai Jing",
    "bestie/serpente": "Chinese painting snake ink",
    "bestie/kun": "Kunpeng Chinese painting",
    # momenti
    "momenti/tribolazione": "lightning storm Chinese painting",
    "momenti/duello": "Chinese sword fight painting",
}


def _get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def find(query: str) -> dict | None:
    """Il primo file d'immagine di Commons per la ricerca, con l'URL in miniatura e i crediti."""
    d = _get({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
              "gsrsearch": query + " filetype:bitmap", "gsrlimit": 5, "prop": "imageinfo",
              "iiprop": "url|extmetadata|mime", "iiurlwidth": WIDTH})
    pages = sorted((d.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        if not ii.get("mime", "").startswith("image/"):
            continue
        meta = ii.get("extmetadata", {})
        return {"title": p.get("title", ""), "url": ii.get("thumburl") or ii.get("url"),
                "page": ii.get("descriptionurl", ""),
                "author": (meta.get("Artist", {}) or {}).get("value", ""),
                "license": (meta.get("LicenseShortName", {}) or {}).get("value", ""),
                "mime": ii.get("mime", "")}
    return None


def _strip(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html or "").strip()


def main(argv: list[str]) -> int:
    try:                                          # la console di Windows non sempre parla UTF-8
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    all_ = "--tutto" in argv
    dry = "--elenco" in argv
    ROOT.mkdir(exist_ok=True)
    credits = []
    ok = skip = fail = 0
    for slot, query in SLOTS.items():
        folder, name = slot.rsplit("/", 1)
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
        existing = [p for p in (ROOT / folder).glob(name + ".*")]
        if existing and not all_:
            skip += 1
            continue
        if dry:
            print(f"{slot:28s} ← «{query}»")
            continue
        try:
            hit = find(query)
            if not hit or not hit["url"]:
                print(f"✗ {slot}: nessun risultato per «{query}»")
                fail += 1
                continue
            ext = {"image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(hit["mime"], ".jpg")
            req = urllib.request.Request(hit["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            for old in existing:
                old.unlink()
            (ROOT / folder / (name + ext)).write_bytes(data)
            credits.append(f"{slot}{ext}\n  {hit['title']}\n  {_strip(hit['author'])} — {hit['license']}\n  {hit['page']}\n")
            print(f"✓ {slot}{ext}  ←  {hit['title']}")
            ok += 1
            time.sleep(0.5)                       # gentilezza verso Commons
        except Exception as e:                    # una ricerca fallita non ferma le altre
            print(f"✗ {slot}: {e}")
            fail += 1
    if credits:
        with open(ROOT / "CREDITI.txt", "a", encoding="utf-8") as f:
            f.write("\n".join(credits) + "\n")
    if not dry:
        print(f"\nScaricate {ok}, già presenti {skip}, non trovate {fail}. Ricarica la dashboard (F5).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
