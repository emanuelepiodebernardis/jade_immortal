"""
LA TARATURA DEL GIOCO — tutte le manopole del ritmo e del pericolo, in un posto solo.

Misurate con partite automatiche da 400 giorni (4 origini × 2 mondi), divise per FASE di gioco:
  A  regni 1-3    l'inizio: si impara, si muore poco
  B  regni 4-6    il mondo si allarga
  C  regni 7-9    le grandi potenze
  D  regni 10+    i mondi superiori

Obiettivi per ogni fase (vedi CHANGES, Aggiornamento 55):
  · scontri: circa 1 al giorno, i nemici tra 0,6 e 1,0 volte la tua forza (mediana ~0,8), quelli più
    forti di 1,5 volte rari (meno del 5%) ed evitabili;
  · imboscate (chi ti attacca senza che tu scelga): al massimo una ogni pochi giorni, mai un muro;
  · morti: rare (meno di 1 ogni 100 giorni), sempre per una scelta o una sfida vera;
  · trame e scene: circa una scena al giorno, un atto di trama ogni 3-5 giorni.
"""

from __future__ import annotations

# --- inseguitori: forza rispetto alla tua (sua/tua), per tipo -----------------------------
PURSUER_BANDS = {
    "cacciatore": (0.6, 0.95),
    "campione": (0.7, 1.0),
    "nemesi": (0.8, 1.1),
    "arcinemico": (0.8, 1.15),
    "vendicatore": (0.6, 0.95),
    "anziano": (0.8, None),          # faide degli anziani: mai indeboliti, solo tenuti al passo
}

# --- imboscate (scontri che non scegli tu) -------------------------------------------------
AMBUSH_GAP_DAYS = {"A": 4, "B": 3, "C": 3, "D": 2}   # giorni minimi tra due imboscate, per fase
THREAT_CHANCE = 0.12                                  # un nemico ostile e vicino ti attacca (per controllo)
THREAT_MAX_RATIO = 1.4                                # chi è più forte di così non si scomoda a tenderti agguati
THREAT_COOLDOWN_DAYS = 4                              # dopo averti attaccato, quel nemico aspetta
HUNTER_COOLDOWN_DAYS = 3                              # un cacciatore che ti ha affrontato si ritira un po'

# --- esito degli scontri persi --------------------------------------------------------------
LOSS_DEATH_CHANCE = 0.30          # se perdi uno scontro che hai scelto (prima era 0,5)
WIPE_DEATH_CHANCE = 0.45          # se sei travolto al primo round (prima era 0,7)
AMBUSH_DEATH_MULT = 0.25          # chi ti tende un agguato e vince, di rado ti finisce (prima 0,4)

# --- terre di frontiera ---------------------------------------------------------------------
FRONTIER_RESPAWN_DAYS = 5         # dopo quanti giorni una terra ripulita torna a popolarsi
FAUNA_BAND = (0.45, 1.0)          # le creature delle terre del tuo livello: tra il 45% e il 100% della tua forza

# --- il bilancio della potenza (power_budget.py) ------------------------------------------------
DAO_AMP_MAX = 2.5                 # i Dao moltiplicano l'attacco al massimo ×2,5 (prima senza tetto: ×6,7 in un salvataggio)
GIFTS_ATK_CAP = 3.0               # tutti i doni in combattimento insieme: verso ×3 in fretta...
GIFTS_TAIL = 0.10                 # ...poi +10% per ogni raddoppio oltre ×3 (Agg. 66): prima a ×20 grezzi un dono
                                  # nuovo (il dantian, una cavalcatura) non spostava più nulla
MAX_EXTRA_STRIKES = 3             # colpi in più per turno
MAX_LETHAL_SAVES = 3              # resurrezioni per scontro
MAX_DAMAGE_REDUCTION = 0.6        # danni subiti: al massimo −60%
MAX_EVADE = 0.4                   # schivata
MAX_CRIT = 0.6                    # critici in più

# --- trame -----------------------------------------------------------------------------------
PLOT_MAX_ACTIVE = 2
PLOT_FIRST_DAY = 4                # le prime giornate sono tue: niente trame subito
PLOT_NEW_GAP_DAYS = 9
PLOT_EXPIRE_DAYS = 30
PLOT_REPEAT_GAP_DAYS = 60


def phase(tier: int) -> str:
    return "A" if tier <= 3 else "B" if tier <= 6 else "C" if tier <= 9 else "D"


REBIRTH_GRACE_DAYS = 15           # (Agg. 66) i primi giorni di una vita nuova: niente agguati, e una sconfitta non uccide
REBIRTH_KEY = "reborn_day"


def in_grace(conn) -> bool:
    """L'anima appena rinata è ancora avvolta dal Samsara. Prima, in Spietato, si moriva fino a quattro volte
    in venti giorni al primo regno, in una spirale senza scampo."""
    from engine.systems import state
    from engine.core import tick as tick_mod
    d = state.get_int(conn, REBIRTH_KEY, -9999)
    return tick_mod.get_tick(conn) // 120 - d < REBIRTH_GRACE_DAYS


def ambush_ok(conn, player_id: int, tick: int) -> bool:
    """Una sola imboscata ogni qualche giorno (secondo la fase): il mondo è pericoloso, non accanito."""
    from engine.systems import state
    from engine.simulation import cultivation
    if in_grace(conn):
        return False
    day = tick // 120
    last = state.get_int(conn, "ambush_day", -999)
    gap = AMBUSH_GAP_DAYS[phase(cultivation.realm_tier(conn, "player", player_id) or 1)]
    return day - last >= gap


def mark_ambush(conn, tick: int) -> None:
    from engine.systems import state
    state.set(conn, "ambush_day", str(tick // 120))


# ================================================================================================
# LA DIFFICOLTÀ (Aggiornamento 59) — tre preset sulle stesse manopole. I valori qui sopra sono
# quelli di partenza; apply() li sostituisce con quelli del preset scelto per la partita.
#
#   sereno     si muore di rado (≈1 volta ogni 1000 giorni nelle simulazioni): per goderti la storia
#   normale    il mondo morde (≈1 morte ogni 200-300 giorni): nemici alla pari più spesso
#   spietato   il genere senza sconti: agguati frequenti, nemici più forti di te, la morte è vicina
# ================================================================================================

PRESETS = {
    "sereno": {
        "PURSUER_BANDS": {"cacciatore": (0.6, 0.95), "campione": (0.7, 1.0), "nemesi": (0.8, 1.1),
                          "arcinemico": (0.8, 1.15), "vendicatore": (0.6, 0.95), "anziano": (0.8, None)},
        "AMBUSH_GAP_DAYS": {"A": 4, "B": 3, "C": 3, "D": 2},
        "THREAT_CHANCE": 0.12, "THREAT_MAX_RATIO": 1.4,
        "LOSS_DEATH_CHANCE": 0.30, "WIPE_DEATH_CHANCE": 0.45, "AMBUSH_DEATH_MULT": 0.25,
        "FAUNA_BAND": (0.45, 1.0), "REBIRTH_GRACE_DAYS": 30,
    },
    "normale": {
        "PURSUER_BANDS": {"cacciatore": (0.65, 1.0), "campione": (0.75, 1.05), "nemesi": (0.85, 1.15),
                          "arcinemico": (0.85, 1.2), "vendicatore": (0.65, 1.0), "anziano": (0.85, None)},
        "AMBUSH_GAP_DAYS": {"A": 3, "B": 3, "C": 2, "D": 2},
        "THREAT_CHANCE": 0.16, "THREAT_MAX_RATIO": 1.5,
        "LOSS_DEATH_CHANCE": 0.30, "WIPE_DEATH_CHANCE": 0.45, "AMBUSH_DEATH_MULT": 0.25,
        "FAUNA_BAND": (0.5, 1.1), "REBIRTH_GRACE_DAYS": 20,
    },
    "spietato": {
        "PURSUER_BANDS": {"cacciatore": (0.75, 1.1), "campione": (0.85, 1.2), "nemesi": (0.95, 1.3),
                          "arcinemico": (0.95, 1.35), "vendicatore": (0.75, 1.1), "anziano": (0.95, None)},
        "AMBUSH_GAP_DAYS": {"A": 3, "B": 2, "C": 2, "D": 1},
        "THREAT_CHANCE": 0.22, "THREAT_MAX_RATIO": 1.8,
        "LOSS_DEATH_CHANCE": 0.40, "WIPE_DEATH_CHANCE": 0.55, "AMBUSH_DEATH_MULT": 0.4,
        "FAUNA_BAND": (0.6, 1.2), "REBIRTH_GRACE_DAYS": 12,
    },
}
# IMMORTALE (spunto: la modalità Immortale di Amazing Cultivation Simulator): le manopole di Spietato, ma
# a schermo spariscono i numeri (resta solo ciò che un coltivatore sentirebbe) e non si salva né si carica
# a mano: valgono solo i salvataggi automatici.
PRESETS["immortale"] = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PRESETS["spietato"].items()}
HIDE_NUMBERS = {"immortale"}
NO_MANUAL_SAVE = {"immortale"}
DIFFICULTY_LABEL = {"sereno": "Sereno", "normale": "Normale", "spietato": "Spietato", "immortale": "Immortale"}
DIFFICULTY_DESC = {
    "sereno": "Per goderti la storia: si muore di rado, gli agguati sono pochi e chi ti insegue non ti supera.",
    "normale": "Il mondo morde: nemici alla pari più spesso, agguati ogni pochi giorni, la morte è possibile.",
    "spietato": "Il genere senza sconti: agguati frequenti, inseguitori più forti di te, ogni sconfitta può essere l'ultima.",
    "immortale": "Come Spietato, ma senza numeri a schermo e senza salvare o caricare a mano: senti il mondo, non lo misuri.",
}
DEFAULT = "normale"
_APPLIED = [None]


def apply(name: str) -> str:
    """Imposta le manopole del preset (in place: anche chi le ha importate vede i valori nuovi)."""
    name = name if name in PRESETS else DEFAULT
    g = globals()
    for k, v in PRESETS[name].items():
        if isinstance(g.get(k), dict):
            g[k].clear()
            g[k].update(v)
        else:
            g[k] = v
    _APPLIED[0] = name
    return name


def current(conn) -> str:
    from engine.systems import state
    v = (state.get(conn, "difficolta") or "").lower()
    return v if v in PRESETS else DEFAULT


def ensure(conn) -> str:
    """Prima di ogni comando: la partita usa il suo preset."""
    name = current(conn)
    if _APPLIED[0] != name:
        apply(name)
    return name


def set_difficulty(conn, name: str) -> str:
    from engine.systems import state
    name = (name or "").strip().lower()
    alias = {"facile": "sereno", "storia": "sereno", "medio": "normale", "difficile": "spietato", "duro": "spietato"}
    name = alias.get(name, name)
    if name not in PRESETS:
        return ("Difficoltà:\n" + "\n".join(f"  {DIFFICULTY_LABEL[k]} — {DIFFICULTY_DESC[k]}" for k in PRESETS)
                + f"\nOra: {DIFFICULTY_LABEL[current(conn)]}. Cambia con 'difficolta sereno|normale|spietato'.")
    state.set(conn, "difficolta", name)
    apply(name)
    return f"Difficoltà: {DIFFICULTY_LABEL[name]}. {DIFFICULTY_DESC[name]}"


apply(DEFAULT)
