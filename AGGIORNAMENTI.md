# Jade Immortal — stato aggiornato (incrementi 1–16)

Cartella COMPLETA e pronta: nessun file da copiare a mano.

## Avvio / Test
```
python main.py
python -m pytest -q     # atteso: 222 passati, 1 "rosso" atteso (settings.yaml: vedi nota)
```
test_fallback_render_produces_prose è "rosso" SOLO perché in config/settings.yaml hai
llm.enabled: true (il test si aspetta l'LLM spento). NON è un bug.

## Contenuto
- INCR. 1–15 — (vedi cronologia): assorbimento, dao, sette, reputazione, gilde, arma,
  eventi/invasioni, mosse, Qi, combattimento narrato, percezione, vie di crescita,
  Cacciatori dell'Eretico, Corruzione+linee evolutive con effetti reali.
- INCR. 16 — Tribolazione: il Fulmine protegge e ogni folgore dona poteri (NUOVO):
    * RESISTENZA DEL FULMINE: più alta è la tua comprensione del DAO DEL FULMINE, meno la
      tribolazione dell'Abisso ti ferisce. A padronanza altissima la assorbi interamente
      ("il fulmine ti appartiene"): nessuna ferita.
    * BENEDIZIONI CELESTI: ogni folgore di tribolazione che ti colpisce viene ASSORBITA e
      ti dona una capacità permanente e potente, che si accumula a ogni colpo:
        - Corpo di Fulmine (+attacco), Pelle di Tuono (+difesa), Cuore Folgorato (+vitalità),
          Anima Folgorata (+spirito/percezione), Furia Celeste (+attacco diretto).
      I livelli si sommano: dopo molte tribolazioni diventi straordinariamente forte.
    * Inoltre ogni colpo fa CRESCERE il tuo Dao del Fulmine (circolo virtuoso: più ti
      colpiscono, più diventi resistente).
    * 'status' mostra i "Doni del Fulmine" accumulati.
  Così la tribolazione, da pericolo, diventa la fonte dei poteri più rari — e i coltivatori
  del Fulmine hanno una via dedicata per dominarla.

## Salvataggi
Le novità si vedono al meglio nei mondi NUOVI: cancella database/world.db per una prova
pulita. La migrazione aggiorna comunque i salvataggi vecchi.
