"""
MANUTENZIONE — il salvataggio non deve crescere all'infinito.

Il mondo vive e registra tutto: dopo mesi di gioco le tabelle degli eventi diventano
enormi. Ogni KEEP_DAYS giorni (a fine giornata) si potano:
  · gli eventi più vecchi di KEEP_DAYS che non ti riguardano (i tuoi restano: sono la tua storia);
  · le conseguenze già risolte e i registri dei tick più vecchi;
  · i report già mostrati e le dicerie vecchie.
La CRONACA della tua vita sta in una tabella sua (vedi chronicle.py) e non viene mai potata.
"""

from __future__ import annotations

KEEP_DAYS = 150
EVERY_DAYS = 10


def prune(conn, day: int, force: bool = False) -> int:
    """Ritorna quante righe di eventi sono state potate."""
    if not force and (day <= 0 or day % EVERY_DAYS):
        return 0
    cutoff = (day - KEEP_DAYS) * 120
    if cutoff <= 0:
        return 0
    old = [r[0] for r in conn.execute(
        "SELECT e.id FROM events e WHERE e.tick < ? AND NOT EXISTS (SELECT 1 FROM event_participants p "
        "WHERE p.event_id=e.id AND p.participant_type='player');", (cutoff,))]
    for i in range(0, len(old), 500):
        chunk = old[i:i + 500]
        q = ",".join("?" * len(chunk))
        conn.execute(f"DELETE FROM event_participants WHERE event_id IN ({q});", chunk)
        conn.execute(f"DELETE FROM consequences WHERE event_id IN ({q}) AND resolved=1;", chunk)
        conn.execute(f"UPDATE consequences SET event_id=NULL WHERE event_id IN ({q});", chunk)
        conn.execute(f"DELETE FROM events WHERE id IN ({q});", chunk)
    conn.execute("DELETE FROM simulation_ticks WHERE tick_number < ?;", (cutoff,))
    conn.execute("DELETE FROM pending_reports WHERE shown=1 AND tick < ?;", (cutoff,))
    conn.execute("DELETE FROM rumors WHERE created_tick < ?;", (cutoff,))
    return len(old)
