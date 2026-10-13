"""Il testo essenziale: il diario alleggerito senza perdere il senso."""
from engine.systems import compact


def test_duplicates_lists_and_runs_are_folded():
    txt = "\n".join([
        "Dao: Spada +1, Corpo +1, Fulmine +1, Fuoco +1, Vento +1, Luce +1, Tempo +1, Metallo +1.",
        "Una riga.", "Una riga.",
        "🗺 La frontiera si allarga a est.", "🗺 La frontiera si allarga a ovest.",
        "🗺 La frontiera si allarga a nord.", "🗺 La frontiera si allarga a sud.",
        "🗺 La frontiera si allarga in alto.", "🗺 La frontiera si allarga in basso.",
        "  [1] Accetti la sfida", "  [2] Fuggi", "(scrivi il numero della tua scelta)",
        "==========", "  GIORNO 3", "==========",
    ])
    out = compact.compact(txt).split("\n")
    assert out[0] == "Dao: Spada +1, Corpo +1, Fulmine +1, Fuoco +1, Vento +1 e altri 3."
    assert out.count("Una riga.") == 1
    assert sum("frontiera" in x for x in out) == 3 and "… e altre 3 simili." in out
    assert "  [1] Accetti la sfida" in out and "  [2] Fuggi" in out
    assert not any("scrivi il numero" in x for x in out)
    assert out.count("==========") == 2
