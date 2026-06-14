# Jade Immortal — stato aggiornato (incrementi 1–18)

Cartella COMPLETA e pronta: nessun file da copiare a mano.

## Avvio / Test
```
python main.py
python -m pytest -q     # atteso: 234 passati, 1 "rosso" atteso (settings.yaml: vedi nota)
```
test_fallback_render_produces_prose è "rosso" SOLO perché in config/settings.yaml hai
llm.enabled: true (il test si aspetta l'LLM spento). NON è un bug.

## Contenuto
- INCR. 1–17 — (vedi cronologia): assorbimento, dao, sette, reputazione, gilde, arma,
  eventi/invasioni, mosse, Qi, combattimento narrato, percezione, vie di crescita,
  Cacciatori dell'Eretico, Corruzione+evoluzioni, tribolazione+Fulmine, guerre tra sette.
- INCR. 18 — Correzione di 4 bug segnalati (NUOVO):
    1. RICARICA A INIZIO GIORNATA: a ogni nuovo giorno il Qi torna al massimo (banner
       "Un nuovo giorno: Qi e spirito ristabiliti"). Non serve più dormire di continuo.
    2. VITTORIA SCHIACCIANTE = UCCISIONE: se abbatti un nemico in fretta restando in
       forze, muore (non "si ritira" all'infinito). Solo gli scontri davvero tirati
       lasciano al nemico la fuga da ferito.
    3. TERRORE = PARALISI (non fuga): se il tuo spirito sovrasta enormemente quello
       dell'avversario (anche un patriarca), resta PARALIZZATO e puoi abbatterlo,
       invece di farlo scappare. Prima era il contrario.
    4. ASSORBIRE UMANI DÀ SEMPRE STATISTICHE: divorare un essere umano (anche un mortale
       per strada, senza Dao) dà sempre +forza, +vitalità, +anima (scalate al suo
       livello: più è forte, più rende), più un frammento di Dao se ne possedeva uno
       (anche un Dao che TU non hai). Niente più assorbimenti "a vuoto".

## Salvataggi
Le novità si vedono al meglio nei mondi NUOVI: cancella database/world.db per una prova
pulita. La migrazione aggiorna comunque i salvataggi vecchi.
