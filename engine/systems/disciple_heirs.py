"""
GLI EREDI DEL TUO STILE (Aggiornamento 80) — i discepoli imparano i tuoi Dao, anche le vie nuove e le fusioni.

  insegna <discepolo> [<dao>]   la lezione ora trasmette davvero il Dao: più lo comprendi, più ne passa (fino a te)
  discepoli_dao                 chi conosce quale dei tuoi Dao, e a che punto

Ogni giorno i discepoli che conoscono i tuoi Dao li allenano da soli, secondo il loro talento. Il giorno in cui uno
ti SUPERA in un Dao che gli hai insegnato:
  · se ti è leale, viene a mostrarti ciò che ha visto e che tu non vedevi: il tuo Dao fa un salto;
  · se è ambizioso e poco legato a te, può andarsene con il tuo stile e diventare un rivale della tua generazione.
"""

from __future__ import annotations

import random

from engine.systems import state

KEY = "heirs_passed"


def _comp(conn, ctype: str, cid: int, key: str) -> int:
    r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type=? AND character_id=? AND dao_key=?;",
                     (ctype, cid, key)).fetchone()
    return int(r["comprehension"] or 0) if r else 0


def lesson_gain(conn, pid: int, npc_id: int, key: str) -> int:
    mine = _comp(conn, "player", pid, key)
    theirs = _comp(conn, "npc", npc_id, key)
    room = max(0, mine - theirs)
    return max(1, min(room, max(3, mine // 12), 60)) if room else 1


def _talent(conn, npc_id: int) -> float:
    r = conn.execute("SELECT ambition FROM npc_traits WHERE npc_id=?;", (npc_id,)).fetchone()
    return 0.6 + (int(r["ambition"] or 50) / 100 if r else 0.5)


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import own_sect, disciple_life
    if player is None:
        return []
    out = []
    passed = state.get_json(conn, KEY, {}) or {}
    mine = {r["dao_key"]: int(r["comprehension"] or 0) for r in conn.execute(
        "SELECT dao_key, comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
        "AND comprehension>0;", (player.id,))}
    for d in own_sect.disciples(conn, player.id):
        nid = d["npc_id"]
        rows = conn.execute("SELECT dao_key, comprehension FROM character_daos WHERE character_type='npc' "
                            "AND character_id=? AND comprehension>0;", (nid,)).fetchall()
        tal = _talent(conn, nid)
        for r in rows:
            k = r["dao_key"]
            if k not in mine:
                continue
            g = max(0, int(rng.uniform(0.3, 1.6) * tal))
            if g:
                conn.execute("UPDATE character_daos SET comprehension=comprehension+? WHERE character_type='npc' "
                             "AND character_id=? AND dao_key=?;", (g, nid, k))
            c = int(r["comprehension"] or 0) + g
            tag = f"{nid}:{k}"
            if c > mine[k] >= 25 and tag not in passed:
                passed[tag] = t // 120
                out += _surpassed(conn, t, rng, player, d, k, c, mine[k], disciple_life)
    state.set_json(conn, KEY, passed)
    return out


def _surpassed(conn, t, rng, player, d, key: str, theirs: int, mine: int, disciple_life) -> list[str]:
    from engine.systems.dao_techniques import _dao_label
    from engine.systems import bonds, prodigies
    nm = d["name"]
    first = nm.split()[0]
    inf = disciple_life.info(conn, d["npc_id"])
    ambitious = "Ambizioso" in (inf.get("traits") or [])
    loyal = inf.get("loyal", 0)
    if ambitious and loyal < 2 and rng.random() < 0.5:
        bonds.end_bond(conn, player.id, d["npc_id"], "disciple", "se ne va con il tuo stile")
        ids = state.get_json(conn, prodigies.KEY, []) or []
        if d["npc_id"] not in ids:
            ids.append(d["npc_id"])
            state.set_json(conn, prodigies.KEY, ids)
        return [f"⚠ {nm} ti ha superato nel {_dao_label(key)} ({theirs} contro {mine}). Una mattina la sua stanza è "
                f"vuota: sul tavolo, una sola riga. «Grazie, maestro. Il resto della strada lo faccio da solo.» Ora è "
                f"un rivale della tua generazione, e porta con sé il tuo stile ('prodigi')."]
    gain = max(5, (theirs - mine) // 2 + mine // 20)
    conn.execute("UPDATE character_daos SET comprehension=comprehension+? WHERE character_type='player' "
                 "AND character_id=? AND dao_key=?;", (gain, player.id, key))
    state.grant_title(conn, "Superato dal Discepolo")
    return [f"✦ {first} ti ha superato nel {_dao_label(key)}. Viene da te a testa bassa, poi alza gli occhi: «Maestro, "
            f"guardi qui. Questo non me l'aveva insegnato nessuno.» Ed è vero: ti mostra un modo che non vedevi. "
            f"Il tuo {_dao_label(key)} +{gain}. ✧ Titolo: «Superato dal Discepolo»"]


def describe(conn, player) -> str:
    from engine.systems import own_sect
    from engine.systems.dao_techniques import _dao_label
    rows = own_sect.disciples(conn, player.id)
    if not rows:
        return "Non hai discepoli ('accogli <nome>')."
    lines = ["🜂 I TUOI EREDI — quale dei tuoi Dao conosce ciascuno ('insegna <nome> <dao>')"]
    for d in rows:
        ks = conn.execute("SELECT dao_key, comprehension FROM character_daos WHERE character_type='npc' "
                          "AND character_id=? AND comprehension>0 ORDER BY comprehension DESC;", (d["npc_id"],)).fetchall()
        parts = [f"{_dao_label(r['dao_key'])} {r['comprehension']}/{_comp(conn, 'player', player.id, r['dao_key'])}"
                 for r in ks if _comp(conn, "player", player.id, r["dao_key"])]
        lines.append(f"  · {d['name']}: " + (", ".join(parts) if parts else "nessuno dei tuoi Dao, ancora"))
    return "\n".join(lines)
