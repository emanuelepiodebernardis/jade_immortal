# Jade Immortal — stato aggiornato (incrementi 1–17)

Cartella COMPLETA e pronta: nessun file da copiare a mano.

## Avvio / Test
```
python main.py
python -m pytest -q     # atteso: 229 passati, 1 "rosso" atteso (settings.yaml: vedi nota)
```
test_fallback_render_produces_prose è "rosso" SOLO perché in config/settings.yaml hai
llm.enabled: true (il test si aspetta l'LLM spento). NON è un bug.

## Contenuto
- INCR. 1–16 — (vedi cronologia): assorbimento, dao, sette, reputazione, gilde, arma,
  eventi/invasioni, mosse, Qi, combattimento narrato, percezione, vie di crescita,
  Cacciatori dell'Eretico, Corruzione+linee evolutive, tribolazione+doni del Fulmine.
- INCR. 17 — Guerre tra sette (NUOVO):
    * Ogni tanto una setta rivale DICHIARA GUERRA alla tua: si apre un FRONTE (un luogo)
      con discepoli nemici e tuoi compagni schierati.
    * Raggiungi il fronte ('home' ti porta dritto in setta) e per ogni nemico scegli:
        - 'attack <nome>' UCCIDI  -> merito di setta (+ poca infamia, è guerra);
        - 'spare <nome>'  RISPARMIA -> onore e fama (e lo togli dalla guerra);
        - 'absorb <nome>' ASSORBI  -> ne divori l'eredità/Dao, ma cresce l'infamia.
    * Sul campo cadono anche i TUOI compagni (skirmish di sfondo): i resti restano a terra.
      Divorarli dà potere ma è un TRADIMENTO: la setta inizia a sospettare di te.
    * Alla scadenza la guerra si RISOLVE: il tuo contributo + la forza della setta decidono
      vittoria o sconfitta. Vincere dà merito, fama, pietre e influenza; ignorare la guerra
      indebolisce la tua setta (perde influenza).
    * 'war' mostra fronte, nemici/compagni in campo, punteggio e tempo rimasto.
  Comodità richieste:
    * 'h' (oltre a 'help') apre l'elenco comandi.
    * 'home' ti riporta direttamente alla sede della tua setta (niente più giri a vuoto).

## Salvataggi
Le novità si vedono al meglio nei mondi NUOVI: cancella database/world.db per una prova
pulita. La migrazione aggiorna comunque i salvataggi vecchi.
