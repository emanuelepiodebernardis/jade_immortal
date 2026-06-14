# Jade Immortal — stato aggiornato (incrementi 1–13)

Cartella COMPLETA e pronta: nessun file da copiare a mano.

## Avvio / Test
```
python main.py
python -m pytest -q     # atteso: 201 passati, 1 "rosso" atteso (settings.yaml: vedi nota)
```
test_fallback_render_produces_prose è "rosso" SOLO perché in config/settings.yaml hai
llm.enabled: true (il test si aspetta l'LLM spento). NON è un bug.

## Contenuto
- INCR. 1–12 — (vedi cronologia): assorbimento, dao, sette, reputazione, gilde, arma,
  eventi/invasioni, mosse, Qi, combattimento automatico narrato, percezione/intimidazione.
- INCR. 13 — Vie di crescita + punti diretti dai Dao (NUOVO):
    * DUE VIE: ogni volta che COLTIVI ('cultivate'/'c') rafforzi le FONDAMENTA
      (vitalità e difesa); ogni volta che ALLENI un Dao ('comprehend') affini
      l'INTUIZIONE (attacco e spirito). In base a cosa fai di più diventi:
        - "Seguace del Dao" (pende verso i Dao) — amplifica i punti dei Dao;
        - "Coltivatore dell'Universo" (pende verso la coltivazione) — amplifica le fondamenta;
        - "Via Equilibrata" se le bilanci, "Viandante" all'inizio.
      La via è mostrata in 'status'.
    * PUNTI-STATISTICA DIRETTI DAI DAO: oltre alle percentuali, ogni soglia di Dao
      raggiunta versa punti DIRETTI in una statistica (cumulativi):
        soglie -> 0, 2, 5, 10, 20, 35, 55, 85 punti.
      Ogni Dao alimenta una statistica precisa: armi e Fulmine -> attacco,
      Corpo -> vitalità, Bastone/Destino/Spazio -> difesa, Anima -> spirito.
      Così chi allena Dao di alto livello è davvero più forte di chi accumula solo
      coltivazione (vale anche per gli NPC: i maestri di Dao sono temibili).

## Salvataggi
Le novità si vedono al meglio nei mondi NUOVI: cancella database/world.db per una prova
pulita. La migrazione aggiorna comunque i salvataggi vecchi (contatori a 0).
