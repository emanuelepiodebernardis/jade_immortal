
---

## Aggiornamento — Armi equipaggiabili (regno × rarità)

**Nuovo modello.** La VIA marziale (tipo d'arma) resta la scelta permanente di setta;
ora però l'arma ha una QUALITÀ data dal **regno** (livello di coltivazione per cui è
forgiata) e da **4 classi di rarità** — comune, raffinata, pregiata, divina. Il bonus
è una % di attacco che cresce col regno (+6% per regno) e, di più, con la rarità
(+5% per classe). L'arma iniziale è comune/regno 1 = **+0%** (quindi nessun test
preesistente cambia).

**Auto-equip dai caduti.** I caduti importanti (e i patriarchi quasi sempre) lasciano
la loro arma. Quando fai `loot`:
- stesso tipo e più forte → **equipaggiata in automatico** ("Impugni …: è superiore alla tua …");
- stesso tipo ma uguale/peggiore → la lasci ("… non è all'altezza della tua …");
- tipo diverso dalla tua via → non puoi usarla ("… ma la tua via è la Spada: non puoi usarla");
- senza una via scelta → non puoi impugnarla.

Le armi non si accumulano nello zaino: o si equipaggiano o si lasciano (resta solo il
messaggio). Il bonus dell'arma equipaggiata moltiplica l'attacco in combattimento
(`combat.combat_power`), distinto dal Dao d'arma (che cresce con la comprensione).

**File toccati:** `engine/systems/weapons.py` (modello + `try_equip_drop`),
`engine/systems/loot.py` (drop dell'arma del caduto), `engine/cli/loop.py`
(messaggi in `cmd_loot`, display in `weapon`/`status`), `engine/simulation/combat.py`
(bonus in `combat_power`), `database/schema.sql` + `engine/db.py` (colonne
`weapon_tier`, `weapon_rarity`). Nuovo test: `tests/test_weapon_equip.py` (10 test).
Suite totale: **285 passati**, 1 rosso atteso (LLM).
