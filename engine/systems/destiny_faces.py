"""
I VOLTI DEL DESTINO (Aggiornamento 84) — chi ti segue, chi ti odia, chi ti deve la vita, in un posto solo.

Il gioco ricorda già moltissimo (l'arcinemico e le sue cicatrici, i vendicatori delle faide, chi hai risparmiato o
aiutato, i saluti di chi ti riconosce, gli echi che tornano). Qui tutto questo diventa visibile:

  faces(conn, player)      le persone che contano per te: ruolo, tono (odio, rancore, gratitudine…), regno, forza
                           come la vedi, dove sono, cosa ricordano di te, l'ultima notizia
  daily(...)               «VOCI DAL MONDO»: quando una di loro sale di regno lo vieni a sapere, con una riga
                           nel suo tono («…e si allena pensando a te»). Al massimo due notizie al giorno.

Nessuna tabella nuova: legge i sistemi che già esistono e tiene due piccoli stati JSON.
Aggiungere una fonte = una funzione che restituisce dei volti in `_sources`.
"""

from __future__ import annotations

import random

from engine.systems import state

SEEN = "faces_seen"                 # npc -> regno visto l'ultima volta
NEWS = "faces_news"                 # [{day, npc, text}]
MAX_FACES = 24
MAX_NEWS = 40

# tono -> (etichetta, priorità: più basso = più in alto)
TONES = {"odio": ("odio", 1), "rancore": ("rancore", 2), "paura": ("paura", 6), "grato": ("gratitudine", 4),
         "rispetto": ("rispetto", 5), "affetto": ("affetto", 3), "complice": ("complicità", 6), "": ("", 7)}

# ricordo di npc_memory -> come lo chiami nel pannello
MEM_ROLE = {"risparmiato": "L'hai risparmiat{o}", "sconfitto": "L'hai sconfitt{o}", "aiutato": "L'hai aiutat{o}",
            "parente_ucciso": "Hai ucciso un suo caro", "minacciato": "L'hai minacciat{o}", "perdonato": "Ti ha perdonato",
            "fratello": "Fratello giurato", "tradito": "L'hai tradit{o}", "rivale": "Rivale", "salvato": "L'hai salvat{o}",
            "amato": "Ti ama", "abbandonato": "L'hai abbandonat{o}", "socio": "Socio", "maestro": "Il tuo maestro"}
# {o} = o/a, {lo} = lo/la: si accordano con chi è (vedi _agree)
MEM_LINE = {"risparmiato": "A {w} potevi finir{lo}: l'hai lasciat{o} vivere.", "sconfitto": "L'hai battut{o} a {w}.",
            "aiutato": "L'hai aiutat{o} a {w}.", "parente_ucciso": "Hai ucciso {v}.", "minacciato": "L'hai minacciat{o} a {w}.",
            "perdonato": "Gli hai chiesto perdono.", "tradito": "L'hai tradit{o}.", "salvato": "L'hai salvat{o} a {w}.",
            "abbandonato": "L'hai lasciat{o} indietro."}


def _agree(text: str, female: bool) -> str:
    return text.replace("{o}", "a" if female else "o").replace("{lo}", "la" if female else "lo")


FLAVOR = {"odio": ["Si allena pensando a te.", "Dicono che abbia giurato di vederti in ginocchio.",
                   "Il tuo nome, sulle sue labbra, suona come una maledizione."],
          "rancore": ["Non ha dimenticato.", "Chi lo ha visto dice che ti cerca con lo sguardo in ogni folla."],
          "grato": ["Brinda al tuo nome.", "Racconta a tutti di quel giorno, e di te."],
          "rispetto": ["Ti aspetta per misurarsi di nuovo.", "«Ora siamo pari», avrebbe detto."],
          "affetto": ["Ti manda i suoi saluti, con il vento.", "Ha chiesto di te a ogni viandante."],
          "paura": ["Spera di non incontrarti più."], "complice": ["Gli affari, pare, vanno a gonfie vele."],
          "": [""]}


def _day(conn) -> int:
    from engine.core import tick
    return tick.get_tick(conn) // 120


def _alive(conn, nid: int):
    return conn.execute("SELECT n.id, n.name, n.status, n.location_id, n.archetype, n.gender, n.kind, l.name AS loc "
                        "FROM npcs n LEFT JOIN locations l ON l.id=n.location_id WHERE n.id=?;", (nid,)).fetchone()


# ------------------------------------------------------------------ le fonti

def _from_archrival(conn) -> list[dict]:
    from engine.systems import archrival
    d = archrival.get(conn)
    if not d or not d.get("npc"):
        return []
    story = []
    n = int(d.get("wins", 0)) + int(d.get("losses", 0))
    if n:
        story.append(f"Vi siete scontrati {n} volt{'a' if n == 1 else 'e'}: hai vinto tu {d.get('losses', 0)}, "
                     f"lui {d.get('wins', 0)}.")
    story += [f"Cicatrice: «{s}»." for s in (d.get("scars") or [])[-2:]]
    story += list(d.get("memory") or [])[-2:]
    gen = int(d.get("gen", 1))
    role = f"Arcinemico «{d.get('epithet', '')}»" + (f" · {gen}ª generazione" if gen > 1 else "")
    return [{"npc": d["npc"], "ruolo": role, "tono": "odio", "pri": 0, "storia": story}]


def _from_feuds(conn) -> list[dict]:
    from engine.systems import feuds
    out = []
    try:
        feuds.ensure_table(conn)
        feuds._fix_genders(conn)
        for r in feuds.feuds(conn):
            rel = feuds.REL_LABEL.get(r["relation"] or "", r["relation"] or "")
            st = {"giurata": "ha giurato vendetta", "in caccia": "ti sta dando la caccia",
                  "ignoto": "cerca chi è stato (non sa ancora che sei tu)"}.get(r["status"], r["status"])
            out.append({"npc": r["npc_id"], "ruolo": f"Vendicatore — {rel} di {r['victim_name'] or '?'}",
                        "tono": "odio", "pri": 1, "storia": [f"Hai ucciso {r['victim_name'] or 'un suo caro'}: {st}.",
                                                             f"Rancore: {r['intensity']}/100."],
                        "caccia": r["status"] == "in caccia"})
        for r in feuds.debts(conn):
            out.append({"npc": r["npc_id"], "ruolo": "Ti deve la vita", "tono": "grato", "pri": 3,
                        "storia": [r["note"] or "Hai risparmiato la sua vita: un debito così non si dimentica."]})
    except Exception:                                    # noqa: BLE001 — una fonte rotta non spegne il pannello
        pass
    return out


def _from_memory(conn) -> list[dict]:
    from engine.systems import npc_memory
    out = []
    for nid, lst in (npc_memory._all(conn) or {}).items():
        if not lst:
            continue
        kind = lst[-1][1]
        if kind not in npc_memory.KINDS:
            continue
        tone = npc_memory.KINDS[kind][0]
        story = []
        for day, k, where, victim in lst[-3:]:
            ln = MEM_LINE.get(k)
            if ln:
                story.append(f"g.{int(day) + 1} — " + ln.replace("{w}", where or "un luogo lontano")
                             .replace("{v}", victim or "un suo caro"))
        out.append({"npc": int(nid), "ruolo": MEM_ROLE.get(kind, kind), "tono": tone,
                    "pri": TONES.get(tone, ("", 7))[1] + 1, "storia": story})
    return out


def _from_echoes(conn) -> dict[int, int]:
    from engine.systems import echoes
    return {e["npc"]: e["due"] for e in echoes._all(conn)}


def _sources(conn) -> list[dict]:
    return _from_archrival(conn) + _from_feuds(conn) + _from_memory(conn)


# ------------------------------------------------------------------ il pannello

def faces(conn, player) -> list[dict]:
    from engine.simulation import cultivation
    from engine.systems import perception
    merged: dict[int, dict] = {}
    for f in _sources(conn):
        cur = merged.get(f["npc"])
        if cur is None:
            merged[f["npc"]] = dict(f)
            continue
        if f["pri"] < cur["pri"]:                        # il ruolo più forte vince, i ricordi si sommano
            f = dict(f)
            f["storia"] = f["storia"] + [s for s in cur["storia"] if s not in f["storia"]]
            f["caccia"] = f.get("caccia") or cur.get("caccia")
            merged[f["npc"]] = f
        else:
            cur["storia"] += [s for s in f["storia"] if s not in cur["storia"]]
    echo = _from_echoes(conn)
    news = {}
    for n in state.get_json(conn, NEWS, []) or []:
        news[n["npc"]] = n
    day = _day(conn)
    out = []
    for nid, f in merged.items():
        r = _alive(conn, nid)
        if not r or r["status"] != "alive":
            continue
        try:
            ratio, cel = perception.apparent(conn, player.id, nid)
        except Exception:                                # noqa: BLE001
            ratio, cel = 1.0, ""
        nw = news.get(nid)
        fem = (r["gender"] or "") == "f"
        out.append({
            "id": nid, "nome": r["name"], "ruolo": _agree(f["ruolo"], fem), "tono": f["tono"],
            "tono_it": TONES.get(f["tono"], (f["tono"], 7))[0], "pri": f["pri"],
            "regno": cultivation.realm_label(conn, "npc", nid), "forza": round(ratio, 3),
            "celato": cel == "celato", "dove": r["loc"] or "?", "qui": r["location_id"] == player.location_id,
            "storia": [_agree(x, fem) for x in f["storia"][:5]], "caccia": bool(f.get("caccia")),
            "tornera": nid in echo and echo[nid] > day,
            "notizia": nw["text"] if nw and day - nw["day"] <= 30 else "",
            "arch": r["archetype"] or "", "f": fem, "kind": r["kind"] or "human",
        })
    out.sort(key=lambda x: (x["pri"], not x["qui"], -x["forza"]))
    return out[:MAX_FACES]


def news_feed(conn, limit: int = 12) -> list[dict]:
    return list(reversed((state.get_json(conn, NEWS, []) or [])[-limit:]))


# ------------------------------------------------------------------ le voci dal mondo

def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.simulation import cultivation
    if player is None:
        return []
    seen = {int(k): v for k, v in (state.get_json(conn, SEEN, {}) or {}).items()}
    news = state.get_json(conn, NEWS, []) or []
    day = t // 120
    out = []
    try:
        lst = faces(conn, player)
    except Exception:                                    # noqa: BLE001
        return []
    for f in lst:
        tier = cultivation.realm_tier(conn, "npc", f["id"]) or 0
        before = seen.get(f["id"])
        seen[f["id"]] = tier
        if before is None or tier <= before or len(out) >= 2 or f["celato"]:
            continue
        flav = rng.choice(FLAVOR.get(f["tono"], [""]))
        txt = f"{f['nome']} ({f['ruolo'].split(' — ')[0].lower()}) ha raggiunto {f['regno']}." + (" " + flav if flav else "")
        news.append({"day": day, "npc": f["id"], "text": txt, "tono": f["tono"]})
        out.append("📜 Voci dal mondo: " + txt)
    state.set_json(conn, SEEN, {str(k): v for k, v in seen.items()})
    if out:
        state.set_json(conn, NEWS, news[-MAX_NEWS:])
    return out
