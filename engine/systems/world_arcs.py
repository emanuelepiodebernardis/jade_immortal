"""
ARCHI DI METÀ PARTITA — storie del MONDO, non solo della tua origine.

Dopo l'arco personale, il mondo ti coinvolge in vicende più grandi, una per fascia di
regni. Ogni arco ha 3 capitoli (scene a scelta, stesso motore delle storie d'origine)
e uno stato separato, così storie d'origine e archi del mondo convivono.

  Regno 3+  «La Guerra delle Tre Sette»         una setta demoniaca invade le terre ortodosse
  Regno 5+  «Il Sigillo del Re Demone»           un antico sigillo si incrina
  Regno 7+  «Il Sentiero dell'Ascensione»        il Cielo ti mette alla prova: oltre questo
                                                 mondo ce ne sono altri, più alti
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "world_arc_progress"      # {arc_key: capitoli completati}

ARCS = [
    {"key": "guerra", "title": "La Guerra delle Tre Sette", "chapters": [
        {"goal": "Raggiungi il terzo regno.", "cond": {"tier_min": 3},
         "scene": {"title": "Fumo all'orizzonte", "text": (
             "Colonne di fumo nero salgono dai villaggi di confine: una setta demoniaca ha varcato "
             "i passi. Il loro generale, {npc}, giura che entro un anno le sette ortodosse "
             "s'inginocchieranno."), "choices": [
                 {"label": "Ti unisci alla difesa delle sette ortodosse",
                  "effects": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "wa_generale",
                                        "hops": 3, "stage": 6, "traits": {"compassion": 0, "ambition": 95}},
                              "outlaw": 400, "crime": "guida l'invasione demoniaca",
                              "flags": ["wa_ortodosso"], "fame": 5}},
                 {"label": "Offri i tuoi servigi al generale demoniaco",
                  "effects": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "wa_generale",
                                        "hops": 3, "stage": 6, "traits": {"compassion": 0, "ambition": 95}},
                              "relation": 40, "infamy": 15, "flags": ["wa_demoniaco", "invito_demoniaco"],
                              "stones": 200}},
                 {"label": "Resti neutrale: le guerre delle sette non ti riguardano",
                  "effects": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "wa_generale",
                                        "hops": 3, "stage": 6, "traits": {"compassion": 0, "ambition": 95}},
                              "flags": ["wa_neutrale"]}}]}},
        {"goal": "La guerra infuria: abbatti il generale demoniaco {wa_generale} — o lascia che vinca "
                 "e guarda cosa ne resta.",
         "cond": {"npc_dead": "wa_generale"},
         "scene": {"title": "Dopo la battaglia", "text": (
             "Il generale è caduto. Tra le sue cose, una mappa vergata col sangue: indica un antico "
             "campo di battaglia sigillato, dove dormono le armi degli immortali."), "choices": [
                 {"label": "Consegni la mappa alle sette ortodosse",
                  "effects": {"fame": 15, "karma": 30, "stones": 300, "flags": ["wa_mappa"]}},
                 {"label": "La tieni per te",
                  "effects": {"flags": ["wa_mappa"], "karma": -5}}]}},
        {"goal": "Raggiungi il quarto regno per sopravvivere al campo di battaglia sigillato.",
         "cond": {"flag": "wa_mappa", "tier_min": 4},
         "scene": {"title": "Il campo delle armi immortali", "text": (
             "Il sigillo si apre al tuo tocco. Ossa di giganti, lance conficcate nella roccia, "
             "e tre lasciti che pulsano ancora di intento."), "choices": [
                 {"label": "Il metodo di coltivazione del generale immortale",
                  "effects": {"gongfa": {"grade": 5}, "title": "Reduce della Guerra delle Sette"}},
                 {"label": "Il cuore cristallizzato di un drago caduto",
                  "effects": {"root_gain": {"element": "all", "amount": 25},
                              "title": "Reduce della Guerra delle Sette"}},
                 {"label": "L'intento di una lancia immortale",
                  "effects": {"learn_technique": {"name": "Intento della Lancia Immortale", "magnitude": 0.15,
                                                  "tech_key": "arco:guerra"},
                              "title": "Reduce della Guerra delle Sette"}}]}},
    ]},
    {"key": "sigillo", "title": "Il Sigillo del Re Demone", "chapters": [
        {"goal": "Raggiungi il quinto regno.", "cond": {"tier_min": 5},
         "scene": {"title": "La terra trema", "text": (
             "Per tre notti la terra trema. Un vecchio eremita ti trova: «Il sigillo del Re Demone "
             "si sta incrinando. Il suo araldo, {npc}, raccoglie sangue per spezzarlo del tutto.»"),
             "choices": [
                 {"label": "Prometti di fermare l'araldo",
                  "effects": {"spawn": {"archetype": "eremita", "tier_offset": 1, "role": "wa_araldo",
                                        "hops": 4, "stage": 5, "traits": {"compassion": 0}},
                              "outlaw": 900, "crime": "vuole liberare il Re Demone", "karma": 10}},
                 {"label": "Chiedi cosa ci guadagneresti",
                  "effects": {"spawn": {"archetype": "eremita", "tier_offset": 1, "role": "wa_araldo",
                                        "hops": 4, "stage": 5, "traits": {"compassion": 0}},
                              "outlaw": 900, "crime": "vuole liberare il Re Demone", "stones": 300}}]}},
        {"goal": "Abbatti l'araldo {wa_araldo} prima che spezzi il sigillo.",
         "cond": {"npc_dead": "wa_araldo"},
         "scene": {"title": "Davanti al sigillo", "text": (
             "L'araldo è morto. Il sigillo pulsa davanti a te: dietro di esso, una potenza antica "
             "come il mondo. Puoi rinforzarlo… o attingervi."), "choices": [
                 {"label": "Rinforzi il sigillo con la tua stessa vita",
                  "effects": {"karma": 120, "fame": 25, "lifespan_years": -30,
                              "title": "Custode del Sigillo", "flags": ["wa_sigillo_saldo"]}},
                 {"label": "Attingi alla potenza del Re Demone",
                  "effects": {"residue": 40, "infamy": 10, "dao_key": "random", "dao_gain": 60,
                              "inner_demon": True, "flags": ["wa_sigillo_violato"]}}]}},
        {"goal": "Raggiungi il sesto regno: il sigillo ha ancora qualcosa da dirti.",
         "cond": {"tier_min": 6, "flag": "wa_sigillo_saldo"},
         "scene": {"title": "La voce dietro il sigillo", "text": (
             "Il Re Demone ti parla attraverso la pietra: «Mi hai imprigionato. Allora prendi "
             "questo, custode: tieni d'occhio ciò che non puoi uccidere.»"), "choices": [
                 {"label": "Accetti il dono con diffidenza",
                  "effects": {"root_gain": {"element": "oscurita", "amount": 80}, "karma": -10}},
                 {"label": "Rifiuti: nessun patto coi demoni",
                  "effects": {"karma": 60, "root_gain": {"element": "luce", "amount": 80}}}]}},
    ]},
    {"key": "ascensione", "title": "Il Sentiero dell'Ascensione", "chapters": [
        {"goal": "Raggiungi il settimo regno.", "cond": {"tier_min": 7},
         "scene": {"title": "L'inviato del Cielo", "text": (
             "Una figura di luce scende dalle nuvole: «Questo mondo è solo il primo gradino. "
             "Sopra di esso ci sono i Mondi Superiori. Dimostra di meritarli.»"), "choices": [
                 {"label": "«Mostrami la via.»", "effects": {"flags": ["wa_via_cielo"], "fame": 10}},
                 {"label": "«Non ho bisogno del permesso del Cielo.»",
                  "effects": {"flags": ["wa_via_cielo", "wa_sfida_cielo"], "dao_key": "random",
                              "dao_gain": 30}}]}},
        {"goal": "Raggiungi l'ottavo regno: la prova del Cielo ti attende.",
         "cond": {"tier_min": 8, "flag": "wa_via_cielo"},
         "scene": {"title": "La prova delle Nove Porte", "text": (
             "Nove porte di luce, una dopo l'altra. Dietro ognuna, una parte di te che devi vincere."),
             "choices": [
                 {"label": "Le attraversi con la forza del Dao", "check": {"stat": "coltivazione", "dc": 80},
                  "success": {"bt_bonus": 0.2, "flags": ["wa_porte"], "text": "Le porte cedono una a una."},
                  "failure": {"injury": 6, "flags": ["wa_porte"], "text": "Passi, ma a caro prezzo."}},
                 {"label": "Le attraversi con la purezza dell'anima", "check": {"stat": "anima", "dc": 80},
                  "success": {"root_gain": {"element": "all", "amount": 15}, "flags": ["wa_porte"]},
                  "failure": {"aff_soul": -2, "flags": ["wa_porte"]}}]}},
        {"goal": "Raggiungi il nono regno: la Porta Celeste si aprirà per te.",
         "cond": {"tier_min": 9, "flag": "wa_porte"},
         "scene": {"title": "La Porta Celeste", "text": (
             "Una scala di giada sale oltre le nuvole. Il passaggio verso il Mondo Superiore è aperto: "
             "potrai varcarlo quando vorrai ('ascendi_mondo')."), "choices": [
                 {"label": "Guardi in alto, senza paura",
                  "effects": {"flags": ["ascension_ready"], "title": "Colui che Ha Visto la Porta"}}]}},
    ]},
]


def progress(conn) -> dict:
    return state.get_json(conn, KEY, {}) or {}


def maybe_advance(conn, player) -> str | None:
    from engine.systems import encounters, storyline, npc_factory
    if encounters.pending(conn):
        return None
    pr = progress(conn)
    for arc in ARCS:
        idx = pr.get(arc["key"], 0)
        if idx >= len(arc["chapters"]):
            continue
        ch = arc["chapters"][idx]
        if not storyline._cond_met(conn, player, ch["cond"]):
            continue
        rng = random.Random(tick_mod.get_tick(conn) * 389 + idx)
        sc = dict(ch["scene"])
        sc["title"] = f"{arc['title']} — {sc['title']} (capitolo {idx + 1}/{len(arc['chapters'])})"
        sc["event_type"] = "story"
        scene = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn),
                                             "story": True})
        scene["sticky"] = True
        pr[arc["key"]] = idx + 1
        state.set_json(conn, KEY, pr)
        return encounters.start_scene(conn, player, scene)
    return None


def goals(conn) -> list[str]:
    from engine.systems import storyline
    pr = progress(conn)
    out = []
    for arc in ARCS:
        idx = pr.get(arc["key"], 0)
        if 0 < idx < len(arc["chapters"]):
            out.append(f"✦ {arc['title']}: " + storyline._fill(arc["chapters"][idx]["goal"], conn))
    return out
