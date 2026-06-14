# Jade Immortal — stato aggiornato (incrementi 1–10)

Cartella COMPLETA e pronta: nessun file da copiare a mano.

## Avvio / Test
```
python main.py
python -m pytest -q     # atteso: 182 passati, 1 "rosso" atteso (settings.yaml: vedi nota)
```
test_fallback_render_produces_prose è "rosso" SOLO perché in config/settings.yaml hai
llm.enabled: true (il test si aspetta l'LLM spento). NON è un bug.

## Contenuto
- INCR. 1 — Reazione & chiarezza.
- INCR. 2 — Assorbimento = identità.
- INCR. 3 — Dao senza limite.
- INCR. 4 — Sette a livelli (+ 7 rappresentanti).
- INCR. 5 — Reputazione (fama/infamia/sospetto, allineamento, titoli, maschera, testimoni).
- INCR. 6 — Gilde: zone di caccia, merito, tecniche segrete.
- INCR. 7 — Arma principale (sblocca il Dao d'arma).
- INCR. 8 — Eventi mondiali / invasioni.
- INCR. 9 — Mosse attive in combattimento (firma per arma, tecniche burst, Morso dell'Abisso).
- INCR. 10 — Qi come risorsa per le mosse (NUOVO):
    * ogni personaggio ha un POOL di Qi determinato dal REGNO: più alto il regno, più Qi.
    * le mosse CONSUMANO Qi; le mosse più forti costano di più.
    * il Qi NON si rigenera combattendo (gli 'attack' non lo recuperano): solo riposando
      ('wait' +35%, 'cultivate' +50%, 'sleep' = pieno) o spostandosi ('move' +15%).
    * così, anche col cooldown scaduto, se hai esaurito il Qi NON puoi più scatenare mosse:
      ti restano gli attacchi normali (gratis) o devi ritirarti a recuperare.
    * 'moves' mostra Qi attuale/max e il costo di ogni mossa; il Qi è anche in 'status'.

## Salvataggi
Le novità si vedono al meglio nei mondi NUOVI: cancella database/world.db per una prova
pulita. La migrazione aggiunge comunque le colonne ai salvataggi vecchi (qi pieno al primo uso).
