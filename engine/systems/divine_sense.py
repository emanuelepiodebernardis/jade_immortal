"""
SENSO DIVINO (神识) e CELARE IL PROPRIO LIVELLO (隐藏修为).

  scruta [nome]     il tuo senso divino si allunga: senza farti notare leggi chi hai davanti
                    (regno vero, forza esatta rispetto a te, sangue, corpo, fortune) — e dal
                    terzo regno anche i luoghi vicini. Costa spirito.
  cela <on|off>     nascondi il tuo vero livello: gli altri ti credono un mortale debole.
                    I prepotenti ti provocano più spesso… e quando li abbatti, l'umiliazione
                    pubblica vale il doppio della fama (il «colpo in faccia» dei romanzi).

Il senso divino cresce senza fine con il Dao dell'Anima: più è alto, più lontano arriva e
meno spirito consuma. Chi ha gli Occhi del Cielo o la Pupilla ritrovata vede anche oltre i
livelli nascosti degli altri.
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state


def concealed(conn) -> bool:
    return state.flag(conn, "concealed", False)


def toggle(conn, arg: str) -> str:
    a = arg.strip().lower()
    on = a in ("on", "si", "sì", "1") or (a == "" and not concealed(conn))
    state.set(conn, "concealed", "1" if on else "0")
    return ("Ritiri la tua aura fin dentro le ossa: agli occhi del mondo sei un mortale qualunque."
            if on else "Lasci che la tua aura torni a respirare: chi ti guarda, ora, capisce.")


def _sense(conn, pid: int) -> int:
    r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
                     "AND dao_key='anima';", (pid,)).fetchone()
    from engine.systems import soul_temper
    return ((r["comprehension"] or 0) if r else 0) + 5 * soul_temper.grade(conn, pid)


def scan(conn, player, arg: str) -> str:
    from engine.systems import spirit as spmod, perception, prodigies, beasts, bloodlines
    from engine.simulation import cultivation
    sense = _sense(conn, player.id)
    cost = max(2, 12 - sense // 20)
    if not spmod.spend(conn, cost, player.id):
        return f"Il tuo spirito è troppo stanco per allungare il senso divino (serve {cost})."
    targets = []
    if arg.strip():
        n = entities.find_npc_in_location(conn, player.location_id, arg)
        if n is None:
            return f"Il tuo senso divino non trova nessuno di nome '{arg}' qui."
        targets = [n.id]
    else:
        targets = [r["id"] for r in conn.execute("SELECT id FROM npcs WHERE location_id=? AND status='alive' "
                                                 "ORDER BY id LIMIT 8;", (player.location_id,))]
    lines = [f"👁 Il tuo senso divino si allunga (portata {1 + sense // 100} luoghi, costo {cost} spirito):"]
    for nid in targets:
        nm = conn.execute("SELECT name, kind FROM npcs WHERE id=?;", (nid,)).fetchone()
        ratio = perception.strength_ratio(conn, player.id, nid)
        extra = []
        if nm["kind"] == "beast":
            tr = beasts.traits(conn, nid)
            extra.append(f"talento {tr['talent']}, {tr['rarity']}")
            b = bloodlines.beast_blood(conn, nid)
            if b:
                extra.append(f"sangue: {b['species']}")
        f = prodigies.fortunes(conn).get(str(nid))
        if f:
            extra.append("fortune: " + ", ".join(f))
        lines.append(f"  · {nm['name']} — {cultivation.realm_label(conn, 'npc', nid)} — forza {1 / max(0.01, ratio):.2f}× "
                     f"la tua" + (f" — {'; '.join(extra)}" if extra else ""))
    if (cultivation.realm_tier(conn, "player", player.id) or 1) >= 3:
        reach = 1 + sense // 100
        seen = _nearby(conn, player.location_id, reach)
        for lid in seen:
            cnt = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND status='alive';", (lid,)).fetchone()["c"]
            ln = conn.execute("SELECT name FROM locations WHERE id=?;", (lid,)).fetchone()["name"]
            lines.append(f"  ↳ {ln}: {cnt} presenze")
    n = state.get_int(conn, "scans", 0) + 1
    state.set(conn, "scans", str(n))
    if n % 10 == 0:
        conn.execute("UPDATE character_daos SET comprehension=comprehension+1 WHERE character_type='player' "
                     "AND character_id=? AND dao_key='anima';", (player.id,))
    return "\n".join(lines)


def _nearby(conn, start, reach) -> list[int]:
    from collections import deque
    seen, q, out = {start}, deque([(start, 0)]), []
    while q:
        cur, d = q.popleft()
        if d >= reach:
            continue
        for nxt in entities.get_exits(conn, cur).values():
            if nxt not in seen:
                seen.add(nxt)
                out.append(nxt)
                q.append((nxt, d + 1))
    return out[:6]


def on_upset(conn, player, npc_name: str) -> list[str]:
    """Vittoria mentre celi il tuo livello: l'umiliazione vale doppio."""
    from engine.systems import reputation
    if not concealed(conn):
        return []
    reputation.adjust(conn, player.id, fame=5)
    n = state.get_int(conn, "face_slaps", 0) + 1
    state.set(conn, "face_slaps", str(n))
    out = [f"Tutti avevano riso di te. Ora fissano {npc_name} a terra, a bocca aperta: «Ma chi… chi è costui?»"]
    if n in (1, 10, 50) and state.grant_title(conn, {1: "Il Mortale che Non Era", 10: "Tigre Travestita da Maiale",
                                                      50: "Il Drago Nascosto"}[n]):
        out.append("✧ Nuovo titolo! ✧")
    return out


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    """Chi cela il suo livello attira i prepotenti (in città)."""
    from engine.systems import encounters, npc_factory
    from engine.simulation import cultivation
    if not concealed(conn) or encounters.pending(conn) or rng.random() > 0.2:
        return []
    lt = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    if not lt or lt["location_type"] != "city":
        return []
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    sc = {"key": "provocazione", "title": "Un prepotente", "event_type": "social",
          "text": "{npc}, un giovane maestro pieno di sé, ti urta apposta: «Togliti dai piedi, mortale.» La gente ride.",
          "spawn": {"archetype": "discepolo", "tier_offset": 0 if tier > 1 else 0, "stage": 6,
                    "traits": {"pride": 95}},
          "choices": [{"label": "Gli insegni l'educazione", "effects": {}, "command": "attack {npc}"},
                      {"label": "Abbassi la testa e passi oltre", "effects": {"heart": -1}}]}
    sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
    txt = encounters.start_scene(conn, player, sc)
    return [txt] if txt else []
