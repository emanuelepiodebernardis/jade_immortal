# Jade Immortal — stato aggiornato (incrementi 1–11)

Cartella COMPLETA e pronta: nessun file da copiare a mano.

## Avvio / Test
```
python main.py
python -m pytest -q     # atteso: 186 passati, 1 "rosso" atteso (settings.yaml: vedi nota)
```
test_fallback_render_produces_prose è "rosso" SOLO perché in config/settings.yaml hai
llm.enabled: true (il test si aspetta l'LLM spento). NON è un bug.

## Contenuto
- INCR. 1 — Reazione & chiarezza.
- INCR. 2 — Assorbimento = identità.
- INCR. 3 — Dao senza limite.
- INCR. 4 — Sette a livelli.
- INCR. 5 — Reputazione (fama/infamia/sospetto, allineamento, titoli, maschera, testimoni).
- INCR. 6 — Gilde: zone di caccia, merito, tecniche segrete.
- INCR. 7 — Arma principale (sblocca il Dao d'arma).
- INCR. 8 — Eventi mondiali / invasioni.
- INCR. 9 — Mosse attive (firma per arma, tecniche burst, Morso dell'Abisso).
- INCR. 10 — Qi come risorsa per le mosse (pool dal regno, niente recupero in combattimento).
- INCR. 11 — Combattimento automatico narrato (NUOVO / RIVISTO):
    * un solo attacco risolve l'intero scontro, raccontato ROUND PER ROUND.
    * il sistema DECIDE da solo quando tirare un colpo normale o una TECNICA speciale
      (spendendo Qi); non spreca tecniche se un colpo normale basta ad atterrare il nemico,
      e quando finisce il Qi torna ai colpi normali.
    * vengono narrate le azioni di ENTRAMBI (tu e l'avversario), con descrizioni
      qualitative dei colpi e dello stato (illeso/ferito/malconcio/allo stremo).
    * la DURATA emerge dal divario di forze: forze simili -> scontro prolungato
      (anche fino a un lungo stallo); divario enorme -> si conclude subito ("La differenza
      è schiacciante").
    * NB: la modalità a turni è stata accantonata per tenere un unico, ottimo automatico.

## Salvataggi
Le novità si vedono al meglio nei mondi NUOVI: cancella database/world.db per una prova
pulita. La migrazione aggiorna comunque i salvataggi vecchi.
