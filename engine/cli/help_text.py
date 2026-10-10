"""
Testo d'aiuto, diviso per categorie.

`help` mostra l'essenziale e l'elenco delle categorie; `help <categoria>` il dettaglio;
`help tutto` l'elenco completo. Lo stesso elenco alimenta il traduttore di intenti in
linguaggio naturale (engine/cli/intent.py), così i due non vanno mai fuori sincrono.
"""

from __future__ import annotations

# (chiave, titolo, righe "comando — descrizione")
CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("esplorazione", "Esplorazione e viaggio", [
        "move <north|south|east|west>  (abbrev: n/s/e/w)  — ti sposti, +1 tick",
        "look                          — osservi la location corrente",
        "look <dir>                    — sbirci la location adiacente in quella direzione",
        "map                           — uscite della location corrente con destinazioni",
        "where                         — nome e pericolo della location corrente",
        "wait                          — attendi (il mondo avanza, osservi i dintorni)",
        "sleep                         — dormi fino all'alba del giorno seguente",
        "home                          — torni direttamente alla sede della tua setta",
        "warzone                       — ti porti direttamente al fronte di guerra più vicino",
        "raidtarget                    — ti porti alla sede di una setta rivale (poi 'raid')",
        "events                        — invasioni mondiali in corso (difendi un luogo)",
        "defend                        — difendi il luogo invaso (abbatti l'ondata)",
    ]),
    ("combattimento", "Combattimento e Abisso", [
        "attack <nome> [mossa]         — attacchi un NPC (puoi morire!); mossa attiva opzionale",
        "attack all                    — attacchi TUTTI i nemici presenti (creature e umani), in sequenza",
        "attack humans                 — attacchi solo gli avversari umani presenti",
        "attack creatures              — attacchi solo le creature selvagge presenti",
        "moves                         — le tue mosse attive in combattimento (cooldown)",
        "absorb <nome>                 — (Abisso Divoratore) divori i resti di un caduto",
        "absorb all                    — divori in sequenza tutti i resti presenti",
        "loot                          — raccogli l'eredità dei caduti (e i tesori della tua tomba)",
        "bounties                      — ricercati da cacciare (taglie e missioni)",
        "hunt <nome>                   — localizza un ricercato e ti indica dove andare",
        "rating                        — il tuo profilo di potenza (Qi/Corpo/Anima/Dao), classe e zona",
    ]),
    ("coltivazione", "Coltivazione e Dao", [
        "cultivate (o 'c')             — mediti per accumulare progresso nel tuo regno",
        "breakthrough                  — tenti di salire di regno (può fallire o ucciderti!); a volte appare il demone interiore",
        "dao                           — i Dao che pratichi e la loro comprensione",
        "comprehend <nome>             — affini un Dao (i Dao da combattimento ti rendono più forte)",
        "tribulation                   — sfida al Cielo (heaven defiance) e tribolazione divina",
        "inventory                     — il tuo zaino (oggetti raccolti)",
        "use <oggetto> | use all       — usi un oggetto dello zaino (o tutti in sequenza)",
        "radici                        — le tue RADICI SPIRITUALI: punteggi, talenti, combinazioni",
        "gongfa [pratica <n>|setta]    — i metodi di coltivazione: quale pratichi, cambiarlo, quello della setta",
        "ritiro <giorni> [dao]         — RITIRO a porte chiuse (montagna, rovine, sede, dimora): giorni di coltivazione",
        "classifica [giovani|sette]    — Classifica del Cielo, Lista del Drago Nascente, classifica delle sette",
    ]),
    ("mondo", "Reami segreti, Assemblea, aste, mondi superiori", [
        "realm                         — il reame segreto aperto ora (dove, quanto resta) — 'realm esci' per uscire",
        "enter                         — entri nel reame segreto (devi essere all'ingresso)",
        "delve                         — scendi al piano successivo del reame (in fondo, la Sala dell'Eredità)",
        "assemblea [iscriviti|1|2|3]   — la GRANDE ASSEMBLEA dell'Alleanza Marziale: iscrizione e incontri",
        "asta [offri <lotto> <pietre>] — la casa d'aste (in città, quando è aperta)",
        "ascendi_mondo                 — (regno 9, poi 12, 15…) apri la Porta Celeste verso un mondo superiore",
        "mondi                         — gli strati di mondo raggiunti — 'up'/'down' per attraversare le porte",
        "sistema [riscuoti|negozio|compra <n>] — (Trasmigratore) missioni e negozio del Sistema",
    ]),
    ("dimora", "Grotta-dimora, discepoli e la tua setta", [
        "dimora                        — la tua grotta-dimora (o come ottenerne una)",
        "dimora reclama                — reclami il luogo selvaggio in cui sei come dimora",
        "dimora potenzia <ala>         — erbe · qi · ritiro · alchimia · difesa · stalla (livelli infiniti)",
        "dimora raccogli | dimora torna — raccogli la produzione | torni a casa",
        "accogli <nome>                — (regno 3+) prendi un discepolo che ti stima ed è più debole",
        "insegna <nome> [dao]          — una lezione al giorno: lui cresce, tu comprendi meglio il Dao",
        "discepoli                     — i tuoi discepoli — 'congeda_discepolo <nome>' per congedarne uno",
        "fonda <nome>                  — (regno 4, dimora, 3 discepoli, 2000 pietre) fondi la tua setta",
        "setta [riscuoti|recluta|difendi] — pannello della tua setta, tributi, reclutamento, difesa",
    ]),
    ("setta", "Sette, guerra e mercato", [
        "sects                         — sette a cui iscriversi e dove hanno sede",
        "join                          — test d'ingresso e iscrizione alla setta locale",
        "class                         — compagni di classe, classifica, prossima sfida/torneo",
        "challenge                     — sfidi un discepolo di rango superiore: se vinci, sali di categoria",
        "weapon <arma>                 — scegli l'arma principale (sblocca il Dao d'arma)",
        "huntzone                      — la zona di caccia della tua setta (mostri = merito)",
        "techniques                    — tecniche segrete della setta e merito disponibile",
        "learn <n>                     — impari una tecnica segreta spendendo merito",
        "invitations                   — inviti delle sette superiori (dopo aver vinto un torneo)",
        "accept <n>                    — accetti un invito e ascendi a una setta superiore",
        "leave                         — lascia la tua setta",
        "anziani                       — gli anziani della tua setta e il loro favore",
        "servi <anziano>               — una giornata al servizio di un anziano (favore, merito)",
        "missioni [accetta <n>|completa] — la bacheca delle missioni di setta",
        "market                        — (in città) il mercato: oggetti da comprare con le pietre",
        "buy <n>                       — compri l'oggetto n dal mercato",
        "war                           — guerra tra sette in corso: fronte, punteggio, tempo",
        "spare <nome>                  — al fronte: sottometti e risparmia un nemico (onore)",
        "raid                          — (alla sede di una setta rivale) la assalti da solo e la saccheggi",
        "invade                        — (rango alto) GUIDI la tua setta a conquistare la setta rivale qui",
        "factions                      — elenco delle fazioni (influenza, territori)",
        "faction <nome>                — dettaglio di una fazione (territori, relazioni)",
    ]),
    ("legami", "Persone e legami", [
        "examine <nome>                — esamini un NPC presente (archetipo, indole, rapporto)",
        "greet <nome>                  — saluti un NPC: prima conoscenza / migliora il rapporto",
        "talk <nome>                   — parli con qualcuno: il rapporto cresce, scopri chi è",
        "gift <nome> <pietre>          — offri pietre spirituali in dono (gli avidi apprezzano)",
        "spar <nome>                   — duello amichevole, non letale: entrambi imparate qualcosa",
        "recruit <nome>                — chiedi a un amico di viaggiare con te come compagno",
        "dismiss                       — congedi il tuo compagno di viaggio",
        "disciple <nome>               — chiedi a un anziano/eremita di farti da maestro",
        "bonds                         — i tuoi legami: compagni, maestro, rivali e nemesi",
        "masters                       — i MAESTRI SEGRETI: chi hai incontrato e cosa serve per il prossimo",
        "giura <nome>                  — giuri fratellanza (rapporto ≥ 70) — 'chiama <nome>' per chiamarlo",
        "proponi <nome>                — diventate compagni del Dao (rapporto ≥ 80): doppia coltivazione",
    ]),
    ("bestie", "Bestie spirituali e lignaggi di sangue", [
        "tame <creatura>               — provi a domare una creatura (ferirla prima aiuta)",
        "beast                         — la tua bestia, il suo talento e gli avvistamenti di bestie rare",
        "feed                          — nutri la tua bestia con un nucleo (cresce)",
        "release                       — liberi la tua bestia",
        "sangue                        — i tuoi LIGNAGGI DI SANGUE: gradi, manifestazioni, trasformazione",
        "use essenza                   — assorbi un'essenza di sangue lasciata da una bestia d'alto livello",
        "fondi_sangue <n> <m> [...]    — fondi due o più lignaggi Puri in un sangue ibrido",
        "trasformati [n]               — (grado Sacro) nel prossimo scontro assumi la forma della bestia sacra",
    ]),
    ("arti", "Professioni: alchimia, talismani, forgia, formazioni, domatore", [
        "profession <arte>             — alchimia · talismani · forgia · formazioni · domatore",
        "gather                        — raccogli erbe, minerali e nuclei nelle zone selvagge",
        "recipes                       — le ricette della tua arte e i materiali che hai",
        "craft <n>                     — crei la ricetta n (pillole, talismani, armi)",
        "sintonia <elemento> [...]     — leghi la tua arte agli elementi delle tue radici: nasce la tua CLASSE",
        "classe_arte                   — la tua classe (arte × elementi) e cosa fa",
        "formazioni                    — (Formazioni) le formazioni piazzate nel mondo ('use' il disco per piazzarne)",
        "teletrasporto [n]             — viaggi all'istante tra le tue formazioni di teletrasporto",
    ]),
    ("storia", "Storia, destino e memoria", [
        "goals                         — i tuoi obiettivi: la tua storia personale e i traguardi vicini",
        "encounter                     — rivedi l'incontro in corso e le scelte possibili",
        "<numero>                      — scegli un'opzione (dell'incontro o delle azioni suggerite)",
        "lives                         — le tue vite passate e le loro tombe",
        "titles                        — i titoli che hai conquistato",
        "status                        — il tuo stato completo",
        "profilo                       — origine, età e affinità (descrizione qualitativa)",
        "reputation                    — fama, infamia, allineamento percepito, sospetto",
        "mask <on|off>                 — indossi/togli la maschera (agisci in incognito)",
        "log [n]                       — cronache recenti note al giocatore",
        "memories                      — ciò che il tuo personaggio ricorda (memoria attiva)",
        "narrate                       — rendi la scena attuale come prosa (LLM o fallback)",
        "chronicle                     — un breve passo di cronaca del mondo",
    ]),
    ("auto", "Pilota automatico (stato etereo)", [
        "auto                          — la configurazione del pilota automatico",
        "auto <giorni>                 — i giorni scorrono da soli (max 60); si ferma agli eventi importanti",
        "auto imposta attivita coltiva=3 dao=2 caccia=2 raccolta=1 lavoro=1 insegna=1 — pesi delle attività",
        "auto imposta bersagli <nessuno|bestie|ricercati|deboli|tutti> — chi attaccare (mai i più forti)",
        "auto imposta assorbi <si|no>  — (Divoratore) divora i caduti",
        "auto imposta loot <si|no> | oggetti <si|no> — raccogli il bottino | usa pillole ed essenze",
        "auto imposta sfonda <si|no>   — tenta da solo il breakthrough quando sei al colmo (rischioso!)",
        "auto imposta condotta <virtuosa|prudente|opportunista|spietata> — scelte negli incontri minori",
        "auto imposta fermati <reame|assemblea|asta|invasione> <si|no> — per quali occasioni fermarsi",
    ]),
    ("sistema", "Interfaccia", [
        "help [categoria|tutto]        — aiuto (anche 'h')",
        "hud <on|off>                  — mostra/nasconde la riga di stato dopo ogni comando",
        "suggest <on|off>              — mostra/nasconde le azioni suggerite numerate",
        "quit / exit                   — esci",
    ]),
]

_ALIASES = {
    "esplora": "esplorazione", "viaggio": "esplorazione",
    "combat": "combattimento", "lotta": "combattimento", "abisso": "combattimento",
    "coltiva": "coltivazione", "dao": "coltivazione", "cultivation": "coltivazione",
    "sette": "setta", "sect": "setta", "guerra": "setta", "mercato": "setta",
    "social": "legami", "persone": "legami", "compagni": "legami", "bonds": "legami",
    "destino": "storia", "story": "storia", "obiettivi": "storia",
    "beast": "bestie", "pet": "bestie", "professioni": "arti", "alchimia": "arti",
    "talismani": "arti", "forgia": "arti", "maestri": "legami",
    "ui": "sistema", "interfaccia": "sistema",
    "reame": "mondo", "reami": "mondo", "assemblea": "mondo", "aste": "mondo", "asta": "mondo",
    "casa": "dimora", "discepoli": "dimora", "grotta": "dimora", "radici": "coltivazione",
    "formazioni": "arti", "domatore": "arti", "sangue": "bestie", "lignaggi": "bestie",
    "autopilota": "auto", "pilota": "auto", "etereo": "auto",
}

ESSENTIALS = """Comandi essenziali:
  look · move <n|s|e|w> · cultivate · attack <nome> · status · goals · auto <giorni>
  Dopo ogni comando trovi delle AZIONI SUGGERITE numerate: scrivi il numero per eseguirle.
  Quando capita un INCONTRO, scegli scrivendo il numero dell'opzione.

Categorie ('help <categoria>', oppure 'help tutto'):"""


def _section(title: str, lines: list[str]) -> str:
    return title + ":\n" + "\n".join("  " + ln for ln in lines)


def full_help() -> str:
    parts = ["Comandi disponibili:"]
    for _key, title, lines in CATEGORIES:
        parts.append(_section(title, lines))
    parts.append('(con Ollama attivo puoi anche scrivere in linguaggio naturale, '
                 'es. "esamina il vecchio")')
    return "\n\n".join(parts)


def help_for(arg: str) -> str:
    a = (arg or "").strip().lower()
    if not a:
        cats = "\n".join(f"  {key:<14} — {title}" for key, title, _ in CATEGORIES)
        return f"{ESSENTIALS}\n{cats}"
    if a in ("tutto", "all", "completo", "full"):
        return full_help()
    a = _ALIASES.get(a, a)
    for key, title, lines in CATEGORIES:
        if key.startswith(a):
            return _section(title, lines)
    return f"Categoria '{arg}' sconosciuta. " + help_for("")


def command_lines() -> list[str]:
    return [ln for _k, _t, lines in CATEGORIES for ln in lines]


def command_words() -> set[str]:
    """Primo token di ogni riga d'aiuto: i verbi che il motore accetta."""
    out = set()
    for ln in command_lines():
        w = ln.split()[0]
        if w.startswith("<"):
            continue
        out.add(w)
    return out


HELP = full_help()
