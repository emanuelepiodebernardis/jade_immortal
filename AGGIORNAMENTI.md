# Jade Immortal — stato aggiornato (incrementi 1–9)

Cartella COMPLETA e pronta: nessun file da copiare a mano.

## Avvio / Test
```
python main.py
python -m pytest -q     # atteso: 176 passati, 1 "rosso" atteso (settings.yaml: vedi nota)
```
test_fallback_render_produces_prose è "rosso" SOLO perché in config/settings.yaml hai
llm.enabled: true (il test si aspetta l'LLM spento). NON è un bug.

## Contenuto
- INCR. 1 — Reazione & chiarezza.
- INCR. 2 — Assorbimento = identità.
- INCR. 3 — Dao senza limite (soglie infinite, tecniche).
- INCR. 4 — Sette a livelli (+ 7 rappresentanti, elemento affine).
- INCR. 5 — Reputazione (fama/infamia/sospetto, allineamento, titoli, maschera, testimoni).
- INCR. 6 — Gilde: zone di caccia, merito, tecniche segrete.
- INCR. 7 — Arma principale all'ingresso in setta (sblocca il Dao d'arma).
- INCR. 8 — Eventi mondiali / invasioni (difendi o ignora, ricompense e conseguenze).
- INCR. 9 — Mosse attive in combattimento (NUOVO):
    * oltre all'attacco normale puoi scatenare MOSSE attive, ognuna con un COOLDOWN.
    * MOSSA FIRMA per ogni arma (ora le armi sono diverse in battaglia!):
        Spada → Fendente Mortale (colpo esecutore)
        Lancia → Affondo Penetrante (perfora la difesa)
        Sciabola → Danza delle Lame (colpi extra)
        Arco → Tiro Preciso (attacco potentissimo)
        Pugni → Pioggia di Colpi (raffica)
        Bastone → Guardia del Bastone (difensiva: subisci molto meno)
    * TECNICHE SEGRETE apprese → diventano burst attivabili (più forti nelle sette alte).
    * MORSO DELL'ABISSO (Divoratore): se uccide, assorbe all'istante.
    * comandi: 'moves' (elenca), 'attack <bersaglio> <mossa>' oppure 'use <mossa> <bersaglio>'.

## Salvataggi
Le novità si vedono al meglio nei mondi NUOVI: cancella database/world.db per una prova
pulita. La migrazione aggiunge comunque le colonne ai salvataggi vecchi.
