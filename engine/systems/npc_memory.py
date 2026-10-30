"""
I PERSONAGGI RICORDANO (Aggiornamento 70) — senza bisogno del modello linguistico.

Ogni volta che fai qualcosa a qualcuno — lo risparmi, lo sconfiggi, lo aiuti, uccidi un suo caro — lui se lo
segna. Poi, quando lo incontri:
  · ti SALUTA (una volta al giorno) ricordandotelo: con gratitudine, con rancore, con paura;
  · PARLANDOGLI ('parla <nome>') si apre un dialogo con scelte che dipendono da cosa ricorda, e le scelte
    hanno conseguenze (pietre, rapporto, un servo, una sfida);
I COMPAGNI che viaggiano con te commentano le tue scelte nei duelli: chi è compassionevole disapprova chi
uccide un vinto, chi è ambizioso approva; il rapporto sale o scende.

Tutto in uno stato JSON: aggiungere un tipo di ricordo è una riga in KINDS.
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "npc_memory"
MAX_PER_NPC = 6

# tipo -> (tono, frasi di saluto: {n}=nome, {w}=dove)
KINDS = {
    "risparmiato": ("grato", ["«Mi hai risparmiato a {w}. Non l'ho dimenticato.»",
                              "«Ti devo la vita. Un debito è un debito.»",
                              "Abbassa lo sguardo: «Quel giorno a {w}… potevi finirmi.»"]),
    "sconfitto": ("rancore", ["«A {w} mi hai umiliato. La prossima volta sarà diverso.»",
                              "Ti fissa a lungo, senza dire nulla. Ricorda {w}.",
                              "«Mi sono allenato ogni giorno pensando a te.»"]),
    "aiutato": ("grato", ["«Senza il tuo aiuto non ce l'avrei fatta.»",
                          "Sorride appena ti vede: «Il mio benefattore!»"]),
    "parente_ucciso": ("odio", ["«Hai ucciso {v}. Il suo sangue chiama il tuo.»",
                                "Stringe i pugni: «{v} non è mai tornato a casa. Per colpa tua.»"]),
    "minacciato": ("paura", ["Indietreggia appena ti vede.", "«N-non cerco guai con te.»"]),
    "perdonato": ("rispetto", ["«Hai chiesto perdono. Non è abbastanza, ma è un inizio.»"]),
}


def _all(conn) -> dict:
    return state.get_json(conn, KEY) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def remember(conn, npc_id: int, kind: str, where: str = "", victim: str = "") -> None:
    d = _all(conn)
    lst = d.setdefault(str(npc_id), [])
    lst.append([tick_mod.get_tick(conn) // 120, kind, where, victim])
    d[str(npc_id)] = lst[-MAX_PER_NPC:]
    _save(conn, d)


def ricordi(conn, npc_id: int) -> list[list]:
    return _all(conn).get(str(npc_id), [])


def last(conn, npc_id: int) -> list | None:
    r = ricordi(conn, npc_id)
    return r[-1] if r else None


def _where(conn, player) -> str:
    loc = entities.get_location(conn, player.location_id)
    return loc.name if loc else "quel luogo"


def _kin(conn, npc_id: int) -> list[int]:
    """Chi piange un morto: i parenti nella tabella delle parentele (se c'è) e chi lo amava di più."""
    out: list[int] = []
    try:
        for r in conn.execute("SELECT source_npc FROM npc_relationships WHERE target_npc=? AND score>=40 "
                              "ORDER BY score DESC LIMIT 3;", (npc_id,)):
            out.append(r["source_npc"])
    except Exception:                                  # noqa: BLE001
        pass
    return out


# ---------------- gli agganci ----------------
def on_duel_end(conn, player, npc, how: str) -> list[str]:
    """Dopo un duello vinto: chi è stato risparmiato o sconfitto se lo ricorda; i cari dei caduti pure.
    I compagni commentano."""
    w = _where(conn, player)
    if how == "risparmiato":
        remember(conn, npc.id, "risparmiato", w)
    elif how == "sigillato":
        remember(conn, npc.id, "sconfitto", w)
    elif how == "ucciso":
        for k in _kin(conn, npc.id):
            n = entities.get_npc(conn, k)
            if n and n.status == "alive":
                remember(conn, k, "parente_ucciso", w, npc.name)
    return companion_comments(conn, player, how, npc.name)


def on_help(conn, npc_id: int, player) -> None:
    remember(conn, npc_id, "aiutato", _where(conn, player))


# ---------------- il saluto ----------------
def greetings(conn, player) -> list[str]:
    """Chi ti ricorda e si trova qui ti saluta (al massimo due, una volta al giorno ciascuno)."""
    d = _all(conn)
    if not d:
        return []
    day = tick_mod.get_tick(conn) // 120
    seen = state.get_json(conn, KEY + "_greet") or {}
    out = []
    for n in entities.npcs_in_location(conn, player.location_id)[:40]:
        r = d.get(str(n.id))
        if not r or seen.get(str(n.id)) == day:
            continue
        _day, kind, where, victim = (r[-1] + ["", ""])[:4]
        if kind not in KINDS:
            continue
        seen[str(n.id)] = day
        line = random.Random(n.id * 31 + day).choice(KINDS[kind][1]).format(w=where or "quel giorno", v=victim or "lui")
        out.append(f"👁 {n.name} ti riconosce. {line}  ('parla {n.name.split()[0]}')")
        if len(out) >= 2:
            break
    if out:
        state.set_json(conn, KEY + "_greet", seen)
    return out


# ---------------- il dialogo ----------------
def scene(conn, player, npc) -> dict | None:
    r = last(conn, npc.id)
    if not r:
        return None
    _day, kind, where, victim = (r + ["", ""])[:4]
    base = {"key": f"ricordo_{npc.id}", "event_type": "social", "ctx": {"npc_id": npc.id, "npc_name": npc.name}}
    t = tick_mod.get_tick(conn)
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    if kind == "risparmiato":
        return {**base, "title": f"{npc.name} ricorda", "text":
                f"{npc.name} si inchina appena: «A {where} potevi finirmi. Chiedimi qualcosa, e se posso lo farò.»",
                "choices": [
                    {"label": "«Ripagami: le tue pietre bastano.»", "effects": {"stones": 60 * tier, "relation": -2,
                     "text": "Ti porge un sacchetto, a malincuore."}},
                    {"label": "«Viaggia con me.»", "effects": {"bond": "companion", "relation": 3,
                     "bond_reason": f"risparmiato a {where}"}},
                    {"label": "«Non mi devi nulla.»", "effects": {"relation": 8, "karma": 2, "heart": 2,
                     "text": "Ti guarda come se ti vedesse per la prima volta."}}]}
    if kind == "sconfitto":
        return {**base, "title": f"{npc.name} non ha dimenticato", "text":
                f"«A {where} hai vinto tu. Ma non è finita.»",
                "choices": [
                    {"label": "«Allora riproviamo. Adesso.»", "effects": {"text": f"(scrivi 'duello {npc.name}')"}},
                    {"label": "Gli tendi la mano: «Allenati con me.»", "effects": {"relation": 6, "heart": 1}},
                    {"label": "Lo ignori", "effects": {"relation": -3}}]}
    if kind == "parente_ucciso":
        return {**base, "title": f"Il dolore di {npc.name}", "text":
                f"«Hai ucciso {victim or 'il mio caro'}. Dammi una ragione per non vendicarlo.»",
                "choices": [
                    {"label": f"Chiedi perdono e paghi il prezzo del sangue ({120 * tier} pietre)",
                     "effects": {"stones": -120 * tier, "relation": 10, "karma": 3,
                                 "text": "Prende le pietre senza guardarti. L'odio si incrina."}},
                    {"label": "«Era lui o io.»", "effects": {"relation": 2, "text": "Non risponde. Forse capisce."}},
                    {"label": "Lo minacci: «Vuoi raggiungerlo?»", "effects": {"relation": -10, "infamy": 2,
                     "text": "Indietreggia, ma nei suoi occhi l'odio diventa giuramento."}}]}
    if kind == "aiutato":
        return {**base, "title": f"La gratitudine di {npc.name}", "text": "«Non ti ho mai ringraziato davvero.»",
                "choices": [
                    {"label": "Accetti un dono", "effects": {"stones": 40 * tier, "relation": 2}},
                    {"label": "Gli chiedi notizie del mondo", "effects": {"relation": 3,
                     "text": "Ti racconta chi si muove nei dintorni, chi cerca chi."}}]}
    return None


def talk(conn, t: int, rng, player, npc) -> str | None:
    from engine.systems import encounters
    if encounters.pending(conn):
        return None
    k = f"mem_day_{npc.id}"
    day = t // 120
    if state.get_int(conn, k, -1) == day:
        return None
    sc = scene(conn, player, npc)
    if not sc:
        return None
    state.set(conn, k, str(day))
    return encounters.start_scene(conn, player, sc, force=True)


# ---------------- i compagni commentano ----------------
APPROVE = {"ucciso": ("ambition", "pride"), "risparmiato": ("compassion", "honor"), "sigillato": ("ambition",)}
DISAPPROVE = {"ucciso": ("compassion", "honor"), "risparmiato": ("ambition",), "sigillato": ("honor", "compassion")}


def companion_comments(conn, player, how: str, victim: str) -> list[str]:
    from engine.systems import relations
    rows = conn.execute("SELECT DISTINCT npc_id, kind FROM bonds WHERE player_id=? AND status='active' "
                        "AND kind IN ('companion','sworn','dao_partner','disciple') AND npc_id IS NOT NULL;",
                        (player.id,)).fetchall()
    out = []
    t = tick_mod.get_tick(conn)
    for r in rows[:6]:
        n = entities.get_npc(conn, r["npc_id"])
        if not n or n.status != "alive":
            continue
        tr = entities.get_npc_traits(conn, n.id) or {}
        pro = max((tr.get(x, 50) for x in APPROVE.get(how, ())), default=50)
        con = max((tr.get(x, 50) for x in DISAPPROVE.get(how, ())), default=50)
        if max(pro, con) < 68:
            continue
        if con >= pro:
            line = {"ucciso": "«Era a terra. Non c'era bisogno di finirlo.»",
                    "risparmiato": "«Lo lasci andare? Tornerà a morderti.»",
                    "sigillato": "«Un'anima non è una catena da mettere al collo di qualcuno.»"}.get(how, "")
            relations.adjust(conn, n.id, -2, t, player.id)
            out.append(f"💬 {n.name} disapprova: {line}")
        else:
            line = {"ucciso": "«Così si fa. Un nemico vivo è un debito.»",
                    "risparmiato": f"«Hai fatto bene a risparmiare {victim}. È questo che ti rende diverso.»",
                    "sigillato": "«Un servo forte in più. Bene.»"}.get(how, "")
            relations.adjust(conn, n.id, 2, t, player.id)
            out.append(f"💬 {n.name} approva: {line}")
        if len(out) >= 2:
            break
    return out
