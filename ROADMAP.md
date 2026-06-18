# ROADMAP — macro-feature da progettare (non ancora implementate)

Questo turno ho chiuso il rework del breakthrough e i bug bloccanti. Le richieste qui
sotto sono **sistemi grossi**: le elenco prioritizzate, con la mia proposta di design,
così possiamo affrontarne una per volta senza costruirne tante a metà.

## 1. Ridisegno dei Dao Spazio / Tempo / Destino  ⭐ (consigliato come prossimo passo)
Coerente con il tuo documento. Tre ruoli distinti:
- **Spazio = Dao distruttivo**: a comprensione crescente ignora difesa, poi colpi
  istantanei (bonus hit/crit), poi colpi multipli (1 attacco → N impatti), fino a
  "difesa irrilevante". Si aggancia a `combat._strike`/`_attack_auto` come moltiplicatori
  e `extra_strikes` scalati dalla comprensione.
- **Tempo = Dao della coltivazione**: `cultivation_gain *= f(tempo)`, recupero accelerato,
  "camera temporale" (più sessioni per tick), iniziativa/evasione in combattimento.
  Si aggancia a `training.session_yield` e `cmd_cultivate`.
- **Destino = Dao della fortuna**: sposta le probabilità degli eventi (loot, incontri,
  meno deviazioni del qi, nemici sfortunati). Si aggancia a `world_events`, `loot`,
  `bounties`, e al `p_death`/`p_success` del breakthrough.

## 2. Tribolazioni Divine / Heaven's Defiance  ⭐
`heaven_defiance = spazio + tempo + destino (+ fulmine)`. Più alto → tribolazioni più
frequenti, forti e "mirate". Soglie di coltivazione che fanno **partire un fulmine di
tribolazione** di forza pari al regno; sopravvivere → **sblocca poteri** (per affinità
Fulmine, poteri spaziali) e **azzera la corruzione dell'Abisso**. Già esiste un modulo
`tribulation.py`: va esteso con il trigger automatico alle soglie e il reset del residuo.
(Questo copre anche: "ho finito la via degli immortali ma nessun potere/fulmine".)

## 3. Nomi di livello generati automaticamente + progressione infinita
Tabella/generatore che produce i nomi dei regni e dei ranghi di setta **all'infinito**
(radici + suffissi crescenti), così coltivazione/Dao/corpo/anima salgono senza tetto.
Richiede di togliere `MAX_TIER=8` e rendere `realm_label`/`tier_name` procedurali.

## 4. Mercato delle pietre spirituali (città)
In città un mercato vende oggetti (pillole, essenze, manuali, armi) **scalati col livello
della setta**: setta più alta → mercato più potente e costoso. Riusa `items.py` per gli
effetti e `sects.get_resource("pietre_spirituali")` come valuta.

## 5. Tornei di classe "giocati" + compagni che crescono
Allo scadere dei 30 giorni: simula i **combattimenti** fra compagni di classe (non solo
classifica), con premiazione e promozione di rango. Ogni giorno i compagni **coltivano in
base al talento** (talento alto → crescita rapida); nelle sette alte i compagni hanno
talento più alto. Vincere il torneo → categoria di discepolo superiore; al massimo rango
puoi **lanciare un'invasione**.

## 6. Tecniche Dao combinate a 3+ Dao + nuovi elementi
Oggi le tecniche combinate si fermano a 2 Dao. Vanno estese: ogni Dao che supera la soglia
si **aggiunge** alla tecnica creando una versione più forte (3, 4, … Dao). Inoltre
aggiungere gli **elementi base** (acqua, fuoco, terra, vento, metallo, legno…) e gli
**elementi superiori** (luce, oscurità, …) oltre al Fulmine già presente.

## 7. Invasioni di specie + caccia territoriale + razzie alle sette
Più invasioni di mostri/demoni/spiriti; infiltrarsi nei territori nemici; se uccidi troppo,
un campione nemico ti dà la **caccia**; uccidere creature alza la fama e abbassa gli status
negativi. Territori di confine sempre più pericolosi salendo di setta. Poter **assaltare in
solitaria** una setta rivale, sterminarla e razziare manuali/tesori, con conseguente
aumento di esposizione agli attacchi.

## 8. Generazione di zona per affinità di setta
Nelle zone delle sette alte gli avversari dovrebbero portare **principalmente il Dao affine
alla setta** e a comprensione più alta (si lega al punto del mercato e all'assorbimento
già scalato per tier).

> Nota: i punti 1, 2 e 6 sono i più "centrali" per il feeling xianxia e si rinforzano a
> vicenda (Dao potenti → defiance → tribolazioni → poteri). Suggerisco di partire da lì.
