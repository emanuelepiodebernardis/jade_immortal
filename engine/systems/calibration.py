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
GIFTS_ATK_CAP = 3.0               # tutti i doni in combattimento insieme: al massimo ×3
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


def ambush_ok(conn, player_id: int, tick: int) -> bool:
    """Una sola imboscata ogni qualche giorno (secondo la fase): il mondo è pericoloso, non accanito."""
    from engine.systems import state
    from engine.simulation import cultivation
    day = tick // 120
    last = state.get_int(conn, "ambush_day", -999)
    gap = AMBUSH_GAP_DAYS[phase(cultivation.realm_tier(conn, "player", player_id) or 1)]
    return day - last >= gap


def mark_ambush(conn, tick: int) -> None:
    from engine.systems import state
    state.set(conn, "ambush_day", str(tick // 120))
