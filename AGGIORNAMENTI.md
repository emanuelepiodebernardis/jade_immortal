# Jade Immortal — stato aggiornato (incrementi 1–21)

Cartella COMPLETA e pronta: nessun file da copiare a mano.

## Avvio / Test
```
python main.py
python -m pytest -q     # atteso: 255 passati, 1 "rosso" atteso (settings.yaml: vedi nota)
```

## Contenuto
- INCR. 1–19 — (vedi cronologia).
- INCR. 20 — Potenza Effettiva, Classi e Zone tematiche: profilo a 4 assi
  (Qi/Corpo/Anima/Dao), rating, classi (Coltivatore del Qi/Cultivatore del Corpo/
  Maestro dell'Anima/Guerriero Dao), vantaggio di stile (morra cinese), zone tematiche
  popolate da classi diverse ma equivalenti; comando 'rating'; 'examine' mostra lo Stile.
- INCR. 21 — I nemici combattono con lo STILE della loro classe (NUOVO):
    * Ogni classe nemica ha ora MECCANICA e LINGUAGGIO propri in combattimento:
        - GUERRIERO DAO: i suoi colpi sono "intenti" che PERFORANO la difesa;
          "Si muove con l'intento del Dao: ogni colpo è una lama di volontà".
        - CULTIVATORE DEL CORPO: coriaceo (più vitalità/difesa) e colpi più PESANTI;
          "Il suo corpo è una fortezza vivente: avanza incurante".
        - MAESTRO DELL'ANIMA: ti opprime con la PRESSIONE SPIRITUALE; linguaggio mentale.
        - COLTIVATORE DEL QI: tecniche spettacolari, maggiore probabilità di critico.
    * Corpo e Anima della coltivazione ora pesano nella potenza degli NPC, così le classi
      hanno identità reale anche meccanica (i Cultivatori del Corpo sono davvero tosti).
    * In apertura di scontro compare l'INTRO di stile dell'avversario; il vantaggio di
      stile (Dao>Qi>Corpo>Anima>Dao) resta applicato e narrato.

## Salvataggi
Le novità si vedono al meglio nei mondi NUOVI: cancella database/world.db per una prova
pulita (zone tematiche e classi popolano il mondo alla generazione).
