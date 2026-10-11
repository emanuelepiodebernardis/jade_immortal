"""
PROVE DEL CUORE (问心) — le illusioni che custodiscono le eredità.

Prima di consegnare un'eredità, gli antichi mettono alla prova il cuore: un'illusione del tuo
DESIDERIO più grande, della tua PAURA, del tuo RIMPIANTO. Chi resta lucido ne esce con un
cuore del Dao più saldo (e a volte un dono); chi si perde nell'illusione ne esce ferito
nell'anima. Compaiono nelle Sale dell'Eredità dei reami segreti e nei momenti chiave della storia.
"""

from __future__ import annotations

import random

_TRIALS = {
    "desiderio": ("La Prova del Desiderio",
                  "La nebbia si apre: davanti a te c'è tutto ciò che hai sempre voluto — il potere, chi ami, "
                  "la tua famiglia al sicuro. Basta restare."),
    "paura": ("La Prova della Paura",
              "Sei di nuovo debole, solo, e tutti quelli che hai battuto ridono di te. La tua coltivazione "
              "svanisce come fumo."),
    "rimpianto": ("La Prova del Rimpianto",
                  "Rivedi il momento che più hai sbagliato. Questa volta puoi cambiarlo… se rinunci a ciò che "
                  "sei diventato."),
}


def scene(rng: random.Random, tier: int, then: dict | None = None) -> dict:
    k = rng.choice(list(_TRIALS))
    title, text = _TRIALS[k]
    dc = 50 + 3 * tier
    sc = {"key": f"prova_cuore_{k}", "title": title, "event_type": "story", "sticky": True,
          "text": text + " (Una prova del cuore: l'illusione mette alla prova il tuo Dao.)",
          "choices": [
              {"label": "Riconosci l'illusione e la spezzi", "check": {"stat": "anima", "dc": dc},
               "success": {"heart": 8, "dao_key": "anima", "dao_gain": 3 + tier,
                           "text": "L'illusione si frantuma come vetro: il tuo cuore ne esce temprato."},
               "failure": {"heart": -6, "aff_soul": -1, "text": "Ti perdi per un tempo che sembra un'era. Ne esci scosso."}},
              {"label": "Accetti ciò che vedi, senza aggrapparti", "check": {"stat": "karma", "dc": dc - 5},
               "success": {"heart": 12, "text": "Lasci andare. Non c'è nulla da spezzare: solo da attraversare."},
               "failure": {"heart": -4, "text": "Credevi di aver lasciato andare. Non era vero."}}]}
    if then:
        for ch in sc["choices"]:
            for br in ("success", "failure"):
                ch[br] = dict(ch[br], then=then)
    return sc
