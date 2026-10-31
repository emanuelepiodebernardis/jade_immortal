"""
IL MONDO CHE REAGISCE (Aggiornamento 76) — righe di narrazione per un mondo più vivo.

  · duel_mine / duel_theirs: quando un colpo è forte, il luogo ne porta i segni (rocce che si spaccano,
    alberi abbattuti, acqua che si solleva), e quando il colpo nemico è pesante devi saltare, rotolare,
    ripararti. Secondo il tipo di luogo e l'elemento della mossa.
  · arrival: arrivando in un luogo, due righe di paesaggio secondo il tipo, l'ora e il tempo.

Testi originali, scelti a caso con un seme stabile: aggiungerne = una riga nelle tabelle.
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------- l'ambiente nel duello

PLACE = {   # tipo di luogo → cose che si possono rompere
    "mountain": ["il crinale", "una parete di roccia", "il sentiero di pietra", "un pino aggrappato allo strapiombo"],
    "forest": ["un tronco secolare", "il sottobosco", "una cortina di rami", "le radici affioranti"],
    "city": ["il selciato", "una bancarella", "il muro di una casa", "la tettoia di una taverna"],
    "village": ["uno steccato", "il pozzo", "un covone di paglia", "il tetto di una capanna"],
    "sect": ["le lastre del cortile", "una colonna laccata", "la balaustra di giada", "un bruciaincenso di bronzo"],
    "ruin": ["un colonnato già crepato", "una statua senza volto", "i resti di un arco", "un altare spezzato"],
    "cave": ["una stalattite", "la volta della grotta", "un cristallo incastonato nella roccia", "la parete umida"],
    "lake": ["la superficie del lago", "il pontile", "le canne della riva", "una barca ormeggiata"],
    "wilderness": ["la terra arida", "un masso solitario", "l'erba alta", "un albero morto"],
    "forbidden_zone": ["il suolo maledetto", "un obelisco di ossa", "la nebbia velenosa", "una crepa che fuma"],
}
EL_MARK = {
    "fuoco": ["prende fuoco", "si annerisce in un istante", "si scioglie in una colata rossa"],
    "acqua": ["si spacca sotto un'onda che non c'era", "esplode in una nube di vapore", "affonda nel fango"],
    "fulmine": ["si spacca in una ragnatela di crepe azzurre", "si carbonizza con un tuono", "vibra e crolla"],
    "vento": ["vola via come una foglia", "si piega fino a spezzarsi", "viene tagliato di netto da una lama d'aria"],
    "terra": ["sprofonda", "si solleva in una zolla gigantesca", "si sgretola in polvere"],
    "metallo": ["viene tagliato in due da una linea perfetta", "si riempie di schegge lucenti"],
    "legno": ["viene stritolato da radici che spuntano dal nulla", "germoglia e si spezza"],
    "luce": ["si dissolve in un bagliore bianco", "si vetrifica"],
    "oscurita": ["viene inghiottito da un'ombra", "marcisce in un respiro"],
    "spada": ["viene tranciato di netto", "porta un taglio lungo dieci passi"],
}
GENERIC_MARK = ["va in pezzi", "esplode in schegge", "si spacca con uno schianto", "crolla in una nuvola di polvere"]
BIG = ["L'onda d'urto rade al suolo tutto ciò che c'è per trenta passi.",
       "Per un attimo il cielo si oscura: dove stava lui ora c'è un cratere.",
       "La terra trema; in lontananza, gli uccelli si alzano in volo tutti insieme.",
       "Il colpo lascia nell'aria un'eco che non si spegne: chi guarda da lontano indietreggia."]
DODGE = ["Ti butti di lato: il colpo apre un solco dove stavi un istante fa.",
         "Salti all'indietro e atterri su un masso; sotto di te la terra fuma.",
         "Rotoli dietro una roccia: la roccia esplode, tu no.",
         "Ti abbassi appena in tempo: il vento del colpo ti strappa una ciocca di capelli.",
         "Pianti i piedi a terra e scivoli indietro di dieci passi, solcando il terreno."]
STAGGER = ["Ti rialzi a fatica: il sangue ti scende dalla bocca.", "Barcolli; la vista ti si annebbia per un istante.",
           "Il colpo ti scaglia contro {cosa}: la senti cedere sotto la schiena."]


def _rng(seed: int) -> random.Random:
    return random.Random(seed * 7919 + 13)


def duel_mine(place_type: str | None, element: str | None, dmg_ratio: float, crit: bool, seed: int) -> str:
    """Il tuo colpo segna il luogo: dal 30% della vita nemica in su (o con un critico)."""
    if dmg_ratio < 0.3 and not (crit and dmg_ratio > 0.12):
        return ""
    r = _rng(seed)
    things = PLACE.get(place_type or "", PLACE["wilderness"])
    marks = EL_MARK.get(element or "", GENERIC_MARK)
    line = f"  🌪 Dietro di lui, {r.choice(things)} {r.choice(marks)}."
    if dmg_ratio >= 0.65:
        line += " " + r.choice(BIG)
    return line


def duel_theirs(place_type: str | None, dmg_ratio: float, crit: bool, seed: int) -> str:
    """Il colpo nemico è pesante (dal 20% della tua vita): devi saltare, rotolare, ripararti."""
    if dmg_ratio < 0.2 and not crit:
        return ""
    r = _rng(seed + 1)
    if dmg_ratio >= 0.35:
        thing = r.choice(PLACE.get(place_type or "", PLACE["wilderness"]))
        return "  💥 " + r.choice(STAGGER).format(cosa=thing)
    return "  🌀 " + r.choice(DODGE)


# ---------------------------------------------------------------- l'arrivo in un luogo

SIGHT = {
    "mountain": ["Le cime si perdono tra le nuvole; il vento porta odore di neve e di resina.",
                 "Un sentiero scavato nella roccia sale a tornanti verso un cielo troppo vicino."],
    "forest": ["Gli alberi sono così alti che la luce arriva a terra in lame sottili.",
               "Il bosco respira: foglie che cadono, un ruscello invisibile, un verso lontano."],
    "city": ["Banchi, insegne, carri, voci: la città non sta ferma un istante.",
             "Le strade odorano di spezie e di incenso; sopra i tetti volano gli aquiloni dei bambini."],
    "village": ["Poche case di legno, il fumo dei focolari, un cane che ti abbaia contro e poi si annoia.",
                "I contadini alzano la testa dai campi per guardarti passare, poi tornano al lavoro."],
    "sect": ["Scalinate di pietra bianca, padiglioni dai tetti ricurvi, il suono lontano di una campana.",
             "Discepoli in fila si allenano nel cortile: le loro spade si muovono come un'unica onda."],
    "ruin": ["Colonne spezzate, iscrizioni che nessuno sa più leggere: qui c'era una grande setta.",
             "Il silenzio delle rovine è pesante, come se le pietre ricordassero ancora."],
    "cave": ["L'aria è fredda e umida; da qualche parte l'acqua goccia con un ritmo lento.",
             "Le pareti scintillano debolmente: vene di cristallo che bevono il qi."],
    "lake": ["L'acqua è così ferma che il cielo sembra due volte più grande.",
             "Sulla riva le canne si piegano al vento; una barca vuota ondeggia legata al pontile."],
    "wilderness": ["Terra aperta, erba piegata dal vento, nessuna strada: solo direzioni.",
                   "Il paesaggio è vuoto fino all'orizzonte, e proprio per questo pericoloso."],
    "forbidden_zone": ["Qui il qi è denso e sbagliato: ti si appiccica alla pelle come fumo.",
                       "Niente canta, niente vola. Anche il vento sembra evitare questo posto."],
}
TIME = {"alba": "La prima luce tinge tutto di rosa.", "mattino": "Il sole del mattino è ancora gentile.",
        "giorno": "Il sole è alto.", "pomeriggio": "Le ombre cominciano ad allungarsi.",
        "sera": "Il tramonto incendia l'orizzonte.", "notte": "È notte: le stelle sono l'unica luce."}
WEATHER = {"pioggia": "Piove, e ogni passo affonda nel fango.", "neve": "Nevica in silenzio.",
           "nebbia": "La nebbia nasconde ciò che è a più di dieci passi.", "vento": "Il vento ti spinge alle spalle.",
           "tempesta": "Il cielo brontola: una tempesta è vicina."}


def arrival(place_type: str | None, moment: str = "", weather: str = "", seed: int = 0) -> str:
    r = _rng(seed)
    parts = [r.choice(SIGHT.get(place_type or "", SIGHT["wilderness"]))]
    m = next((v for k, v in TIME.items() if k in (moment or "").lower()), "")
    w = next((v for k, v in WEATHER.items() if k in (weather or "").lower()), "")
    extra = " ".join(x for x in (m, w) if x)
    return "🏞 " + parts[0] + (" " + extra if extra else "")
