# Jade Immortal — stato aggiornato (incrementi 1–15)

Cartella COMPLETA e pronta: nessun file da copiare a mano.

## Avvio / Test
```
python main.py
python -m pytest -q     # atteso: 217 passati, 1 "rosso" atteso (settings.yaml: vedi nota)
```
test_fallback_render_produces_prose è "rosso" SOLO perché in config/settings.yaml hai
llm.enabled: true (il test si aspetta l'LLM spento). NON è un bug.

## Contenuto
- INCR. 1–14 — (vedi cronologia): assorbimento, dao, sette, reputazione, gilde, arma,
  eventi/invasioni, mosse, Qi, combattimento narrato, percezione, vie di crescita,
  Cacciatori dell'Eretico.
- INCR. 15 — L'Abisso morde: Corruzione + Linee evolutive con effetti REALI (NUOVO):
    * LINEE EVOLUTIVE CON BONUS (non più solo un titolo). In base al tipo che divori di
      più, e allo stadio (nascente/affermato/compiuto), ottieni bonus meccanici:
        - Predatore Primordiale (bestie): +attacco e +vitalità (corpo, rigenerazione);
        - Tiranno Demoniaco (demoni): +attacco e AURA TERRIFICANTE (terrore in battaglia);
        - Imperatore Spirituale (spiriti): +difesa, +spirito (percezione) e comprensione
          Dao più rapida;
        - Divoratore Celeste (umani): un po' di tutto.
      Due Divoratori con la stessa origine finiscono build completamente diverse.
    * SOGLIE DI CORRUZIONE ORA ATTIVE:
        - assorbi meglio (già presente);
        - >=250 gli ANZIANI PERCEPISCONO l'Abisso -> i Cacciatori dell'Eretico scattano
          anche solo per la corruzione (oltre che per sospetto/infamia);
        - >=500 TERRORE: la tua presenza abissale fa esitare i nemici (subisci meno danni)
          e intimidisce i deboli;
        - >=1000 ANOMALIA CELESTE: il Cielo ti considera una minaccia e ogni tanto si
          abbatte una TRIBOLAZIONE DELL'ABISSO che ti ferisce ma scarica parte della
          corruzione (sopravvivere accresce la tua fama... e il tuo terrore).
    * 'status' mostra ora Corruzione e linea evolutiva per il Divoratore.

## Salvataggi
Le novità si vedono al meglio nei mondi NUOVI: cancella database/world.db per una prova
pulita. La migrazione aggiorna comunque i salvataggi vecchi.
