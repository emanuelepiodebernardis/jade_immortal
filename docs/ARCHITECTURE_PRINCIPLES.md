# Principi architetturali (vincolanti)

Decisioni prese presto perché *cheap ora, costose dopo*. Non sono codice da
costruire subito: sono regole che ogni fase successiva deve rispettare.

---

## P1 — Active Simulation Scope (interest management)

**Regola:** il mondo è persistente nel DB ma **non è simulato tutto a ogni tick**.
Solo lo *scope attivo* riceve simulazione continua.

Scope attivo = location del player + location adiacenti + NPC con relazione
diretta col player + NPC coinvolti in eventi in corso.

Fuori dallo scope:
- gli NPC **non tickano** (restano dormienti);
- quando tornano rilevanti, si simulano **in batch** dal loro `last_active_tick`
  al tick corrente;
- fazioni molto lontane (più avanti) potranno evolvere come macro-statistiche,
  non NPC per NPC.

**Cosa NON costruire prima del tempo:** lo Scope Manager, la batch simulation e
l'abstract faction simulation nascono in **Fase 3+**, quando esiste il world tick.
In Fase 0–2 l'unica traccia è la colonna `npcs.last_active_tick` (già nello schema).

Perché: senza questo, il costo cresce con la dimensione del mondo (rischio O(N²)
su relazioni/fazioni). È la differenza tra "idea enorme" e "software realizzabile".

---

## P2 — Factual Lock: il Narrative Layer è un *sink puro*

**Regola fondamentale:** il testo prodotto dall'LLM va a schermo e in Obsidian,
ma **non rientra mai** nella simulazione come dato. Nessun parser legge la
narrativa per aggiornare lo stato. Il DB resta l'unica fonte di verità (vincolo 26).

Conseguenza: se l'LLM inventa causalità non simulata (es. "NPC C giura vendetta"),
quella causalità **non ha effetto meccanico**, perché niente la rilegge.
L'incoerenza è al massimo cosmetica in una scena, mai sistemica.

**Cosa implementare (in Fase 9, cheap e deterministico):**
- `prompt_builder` passa **fatti osservabili**, non framing emotivo
  (sanitize del NarrativeContext);
- il system prompt vieta esplicitamente inferenza di emozioni/intenzioni/cause;
- **whitelist entità**: controllo a stringa che l'output non nomini NPC/luoghi
  assenti dal NarrativeContext (deterministico, banale).

**Cosa NON costruire:** un `validate_output()` che verifica semanticamente
"l'LLM ha inferito una causa?". È un problema di NLP difficile e diventerebbe un
secondo motore di simulazione. La protezione vera è il sink puro (sopra), gratis.

---

## Disciplina di processo

Dei limiti reali del progetto, si incidono *ora* solo quelli cheap-now/expensive-later.
L'implementazione di tutto il resto si rimanda al momento in cui esiste il sistema
che quel limite tocca. Progettare tutta l'emergenza a priori è il modo in cui questi
progetti muoiono.
