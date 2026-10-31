"""
L'ALBERO DEI DAO (Aggiornamento 79) — i dati per il grafo della dashboard.

Nodi: tutti i Dao (di base, superiori, vie nuove, fusioni). Archi:
  component  un Dao entra in una fusione          (acqua → vapore)
  derive     una via nuova deriva da un Dao di base (acqua → ghiaccio)
  insight    una fusione portata in fondo apre un Dao più alto (vapore → yinyang, a 1000)
Stato di ogni nodo: have (lo hai) · ready (puoi aprirlo o fonderlo ora) · open (si può raggiungere) · locked.
"""

from __future__ import annotations

GROUP = {"systemic": "base", "narrative": "arma", "deep": "profondo", "elemental": "elementale",
         "superior": "superiore", "fused": "fuso", "forbidden": "proibito"}


def graph(conn, pid: int = 1) -> dict:
    from engine.generators import dao_gen
    from engine.systems import dao_laws, dao_training as dt
    comp = {r["dao_key"]: int(r["comprehension"] or 0) for r in conn.execute(
        "SELECT dao_key, comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
        "AND (practiced=1 OR comprehension>0);", (pid,))}
    nodes, edges = [], []
    for k, name, lvl, desc in dao_gen.DAOS:
        row = dao_laws.BY_KEY.get(k)
        group = dao_laws.LEVEL_IT.get(row[2], "base") if row else ("fuso" if k in dao_laws.FUSED
                                                                    else GROUP.get(lvl, "base"))
        if row and row[2] == "systemic":
            group = "corpo e anima"
        c = comp.get(k)
        grade = dao_laws.grade(c) if (c is not None and k in dao_laws.FUSED) else None
        if c is not None:
            st, cmd = "have", f"comprehend {k}"
        elif k in dao_laws.FUSED:
            s = dao_laws.recipe_status(conn, k, pid)
            st = "ready" if not s["missing"] else ("open" if any(x in comp for x in dao_laws.FUSED[k][2]) else "locked")
            cmd = f"fusione {k}" if st == "ready" else f"obiettivo {k}"
        elif row:
            ok = dao_laws.requirement(conn, k, pid)[0]
            st = "ready" if ok and row[4][0] != "risveglio" else ("open" if row[4][0] != "risveglio" else "locked")
            cmd = f"comprehend {k}" if st == "ready" else f"obiettivo {k}"
        else:
            st, cmd = "locked", f"obiettivo {k}"
        if row:
            hint = f"{desc} ✔ {row[10]} · ✘ {row[11]}"
        elif k in dao_laws.FUSED:
            hint = f"{desc} — " + " + ".join(f"{dao_laws._plainname(n)} {v}" for n, v in
                                            ((dao_name(x), v) for x, v in dao_laws.requirement_of(conn, k).items()))
        else:
            hint = desc
        nodes.append({"key": k, "name": name, "group": group, "state": st, "comp": c or 0, "grade": grade,
                      "label": dt.comprehension_label(c) if c is not None else "", "cmd": cmd, "hint": hint})
    for fk, row in dao_laws.FUSED.items():
        for c in row[2]:
            edges.append({"from": c, "to": fk, "kind": "component"})
    for k, row in dao_laws.BY_KEY.items():
        if row[4][0] == "derivato":
            for b in row[4][1]:
                edges.append({"from": b, "to": k, "kind": "derive"})
    for fk, steps in dao_laws.INSIGHT.items():
        for th, d in steps:
            edges.append({"from": fk, "to": d, "kind": "insight", "at": th})
    return {"nodes": nodes, "edges": edges}


def dao_name(k: str) -> str:
    from engine.systems.dao_techniques import _dao_label
    return _dao_label(k)
