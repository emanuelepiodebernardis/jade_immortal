"""
DIPINGE GLI SFONDI DEL GIOCO — paesaggi a inchiostro (shan shui) generati dal codice, tutti nello stesso stile.

    python strumenti/dipingi_sfondi.py            dipinge ciò che manca in immagini/luoghi, mondi, momenti
    python strumenti/dipingi_sfondi.py --tutto    li ridipinge tutti

Lo stile è unico per tutto il gioco: inchiostro su seta invecchiata, creste di montagne a strati che sfumano
nella nebbia, un sole o una luna di cinabro, pini sulle creste, e accenti di verde giada e oro. Ogni sfondo
ha il suo seme: ridipingere dà sempre la stessa immagine. Serve solo numpy e Pillow.

Le immagini scaricate o generate altrove (Higgsfield…) con lo stesso nome hanno la precedenza solo se
sostituisci il file: questo script non sovrascrive nulla senza --tutto.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / "immagini"

# ---------------------------------------------------------------- la tavolozza

SILK = (214, 203, 176)
INK = (24, 28, 27)
JADE = (54, 104, 88)
CINNABAR = (176, 46, 34)
GOLD = (206, 162, 72)


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------- strumenti di base

def silk(w, h, rng, base=SILK, dark=0.0):
    """La seta: un colore caldo, fibre orizzontali, macchie del tempo e un bordo più scuro."""
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    col = np.array(base, dtype=np.float32)[None, None, :] * np.ones((h, w, 1), np.float32)
    grad = 1.0 - 0.10 * y - dark * (0.4 + 0.6 * y)
    vign = 1.0 - 0.28 * ((x - 0.5) ** 2 * 2.2 + (y - 0.45) ** 2 * 1.6)
    fib = np.random.default_rng(rng.randrange(1 << 30)).normal(0, 1, (h, 1)).astype(np.float32)
    fib = np.repeat(fib, w, axis=1) * 0.012
    blot = _noise(w, h, rng, 6) * 0.06 + _noise(w, h, rng, 24) * 0.025
    col *= (grad * vign + fib + blot)[..., None]
    return np.clip(col, 0, 255)


def _noise(w, h, rng, cells):
    """Rumore morbido (bilineare su una griglia casuale), valori circa in [-1, 1]."""
    g = np.random.default_rng(rng.randrange(1 << 30)).uniform(-1, 1, (cells + 2, int(cells * w / h) + 2))
    im = Image.fromarray(((g + 1) * 127.5).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, np.float32) / 127.5 - 1.0


def ridge(w, base, amp, rough, rng, peaks=None):
    """Una cresta di montagne (spostamento del punto medio), opzionalmente con picchi forzati [(x, altezza)]."""
    n = 1
    pts = [base + rng.uniform(-amp, amp) * 0.3, base + rng.uniform(-amp, amp) * 0.3]
    disp = amp
    while n < w:
        new = []
        for i in range(len(pts) - 1):
            new += [pts[i], (pts[i] + pts[i + 1]) / 2 + rng.uniform(-disp, disp)]
        new.append(pts[-1])
        pts = new
        n = len(pts) - 1
        disp *= rough
    ys = np.interp(np.linspace(0, len(pts) - 1, w), np.arange(len(pts)), pts)
    if peaks:
        xs = np.arange(w)
        for px, ph, pw in peaks:
            ys -= ph * np.exp(-((xs - px) / pw) ** 2)
    return ys


def paint_range(img, ys, color, alpha, fade, rng, texture=0.35, edge=0.35):
    """Una catena: inchiostro denso sulla cresta che sfuma verso il basso nella nebbia, con le «rughe» (cun)."""
    h, w, _ = img.shape
    yy = np.arange(h, dtype=np.float32)[:, None]
    d = yy - ys[None, :]
    inside = d >= 0
    a = np.where(inside, alpha * (edge + (1 - edge) * np.exp(-d / fade)), 0.0)
    a += np.where(inside, alpha * 0.12, 0.0)                                  # un velo anche in basso
    # rughe: strisce verticali e leggermente oblique
    st = _noise(w, h, rng, 3)
    streak = np.random.default_rng(rng.randrange(1 << 30)).normal(0, 1, (1, w)).astype(np.float32)
    streak = np.asarray(Image.fromarray(((np.clip(streak, -3, 3) + 3) * 40).astype(np.uint8)).resize((w, h)),
                        np.float32) / 120 - 1
    vary = _noise(w, h, rng, 10) * 0.5 + 0.5                                  # le rughe vanno e vengono
    a *= np.clip(1 + texture * (0.35 * streak * vary + 0.65 * st), 0.2, 1.5)
    # bordo netto, quasi una pennellata, sulla cresta
    rim = np.exp(-np.maximum(d, 0) / 3.0) * inside * alpha * 0.9
    a = np.clip(np.maximum(a, rim), 0, 1)[..., None]
    c = np.array(color, np.float32)[None, None, :]
    img[:] = img * (1 - a) + c * a


def mist(img, y0, height, strength, rng, color=(236, 230, 214)):
    h, w, _ = img.shape
    yy = np.arange(h, dtype=np.float32)[:, None]
    prof = np.exp(-((yy - y0) / height) ** 2)
    n = (_noise(w, h, rng, 4) * 0.5 + 0.5) * 0.7 + 0.3
    a = np.clip(prof * n * strength, 0, 1)[..., None]
    img[:] = img * (1 - a) + np.array(color, np.float32)[None, None, :] * a


def disk(img, cx, cy, r, color, alpha=0.85, glow=2.2):
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    a = np.clip((r - d) / 2.5, 0, 1) * alpha + np.exp(-np.maximum(d - r, 0) / (r * glow)) * 0.12 * (d > r)
    a = a[..., None]
    img[:] = img * (1 - a) + np.array(color, np.float32)[None, None, :] * a


def to_image(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def pine(draw, x, y, s, rng, ink=INK):
    """Un pino a inchiostro: tronco storto e palchi di aghi orizzontali."""
    pts = [(x, y)]
    cx, cy = x, y
    for _ in range(5):
        cx += rng.uniform(-0.25, 0.25) * s
        cy -= s * 0.32
        pts.append((cx, cy))
    draw.line(pts, fill=ink, width=max(1, int(s * 0.07)))
    for i, (px, py) in enumerate(pts[1:], 1):
        k = (1.0 - i / 7) * s * 0.9
        for side in (-1, 1):
            ex = px + side * k * rng.uniform(0.6, 1.0)
            draw.ellipse([min(px, ex) - 2, py - s * 0.06, max(px, ex) + 2, py + s * 0.05], fill=ink)


def pagoda(draw, x, base, wdt, floors, ink=INK, accent=CINNABAR):
    """Una pagoda: piani che si stringono e tetti a punte rialzate."""
    y = base
    for f in range(floors):
        fw = wdt * (1 - f * 0.13)
        fh = wdt * 0.32
        draw.rectangle([x - fw * 0.36, y - fh, x + fw * 0.36, y], fill=ink)
        if f == 0:
            draw.rectangle([x - fw * 0.08, y - fh * 0.75, x + fw * 0.08, y], fill=accent)
        ry = y - fh
        draw.polygon([(x - fw * 0.62, ry + fh * 0.05), (x - fw * 0.5, ry - fh * 0.12), (x, ry - fh * 0.42),
                      (x + fw * 0.5, ry - fh * 0.12), (x + fw * 0.62, ry + fh * 0.05), (x, ry - fh * 0.18)], fill=ink)
        y = ry - fh * 0.2
    draw.line([(x, y), (x, y - wdt * 0.5)], fill=ink, width=max(1, int(wdt * 0.04)))


def hall(draw, x, base, wdt, ink=INK, accent=CINNABAR):
    """Un padiglione basso con il tetto curvo."""
    h = wdt * 0.28
    draw.rectangle([x - wdt * 0.42, base - h, x + wdt * 0.42, base], fill=ink)
    for k in (-0.25, 0, 0.25):
        draw.rectangle([x + wdt * k - wdt * 0.03, base - h * 0.8, x + wdt * k + wdt * 0.03, base], fill=accent)
    draw.polygon([(x - wdt * 0.6, base - h + 2), (x - wdt * 0.48, base - h - h * 0.35), (x, base - h - h * 0.6),
                  (x + wdt * 0.48, base - h - h * 0.35), (x + wdt * 0.6, base - h + 2)], fill=ink)


def seal(img_pil, x, y, s, rng):
    """Il sigillo rosso dell'artista (un timbro astratto)."""
    d = ImageDraw.Draw(img_pil, "RGBA")
    d.rectangle([x, y, x + s, y + s], fill=CINNABAR + (215,))
    for _ in range(5):
        a = rng.uniform(0.15, 0.85)
        b = rng.uniform(0.15, 0.85)
        if rng.random() < 0.5:
            d.rectangle([x + s * a - s * 0.05, y + s * 0.15, x + s * a + s * 0.05, y + s * 0.85], fill=SILK + (235,))
        else:
            d.rectangle([x + s * 0.15, y + s * b - s * 0.05, x + s * 0.85, y + s * b + s * 0.05], fill=SILK + (235,))


def bolt(draw, x, y0, y1, rng, color, width):
    pts = [(x, y0)]
    cy, cx = y0, x
    while cy < y1:
        cy += rng.uniform(18, 45)
        cx += rng.uniform(-40, 40)
        pts.append((cx, cy))
        if rng.random() < 0.25:
            bx, by = cx, cy
            br = [(bx, by)]
            for _ in range(3):
                by += rng.uniform(15, 35)
                bx += rng.uniform(-45, 45)
                br.append((bx, by))
            draw.line(br, fill=color, width=max(1, width // 2))
    draw.line(pts, fill=color, width=width)


# ---------------------------------------------------------------- i quadri

W, H = 1920, 720          # luoghi e momenti: larghi e bassi, come il riquadro del luogo e l'arena


def scene_mountain(seed):
    rng = random.Random(seed)
    img = silk(W, H, rng)
    disk(img, W * 0.78, H * 0.22, 46, CINNABAR, 0.8)
    for i, (base, amp, col, a, fade) in enumerate([
            (H * 0.42, 70, _mix(JADE, SILK, 0.55), 0.55, 120), (H * 0.55, 90, _mix(JADE, INK, 0.2), 0.62, 90),
            (H * 0.70, 80, _mix(INK, JADE, 0.25), 0.78, 70), (H * 0.86, 50, INK, 0.9, 50)]):
        peaks = [(rng.uniform(0.1, 0.9) * W, rng.uniform(80, 220) * (1 - i * 0.2), rng.uniform(60, 140)) for _ in range(3)]
        ys = ridge(W, base, amp, 0.55, rng, peaks)
        paint_range(img, ys, col, a, fade, rng)
        mist(img, base + 70, 45, 0.55, rng)
        if i == 3:
            pil = to_image(img)
            d = ImageDraw.Draw(pil)
            for _ in range(9):
                x = rng.uniform(0.02, 0.98) * W
                pine(d, x, ys[int(x)] + 6, rng.uniform(40, 80), rng)
            img = np.asarray(pil, np.float32).copy()
    return img


def scene_city(seed):
    rng = random.Random(seed)
    img = silk(W, H, rng)
    disk(img, W * 0.2, H * 0.2, 40, CINNABAR, 0.75)
    for base, amp, col, a in ((H * 0.38, 60, _mix(JADE, SILK, 0.6), 0.5), (H * 0.5, 50, _mix(JADE, SILK, 0.35), 0.55)):
        paint_range(img, ridge(W, base, amp, 0.55, rng), col, a, 110, rng)
        mist(img, base + 60, 50, 0.6, rng)
    pil = to_image(img)
    d = ImageDraw.Draw(pil)
    wall = H * 0.80
    d.rectangle([0, wall, W, wall + 26], fill=_mix(INK, SILK, 0.15))
    for x in range(0, W, 46):
        d.rectangle([x, wall - 12, x + 26, wall], fill=_mix(INK, SILK, 0.15))
    for _ in range(14):
        hall(d, rng.uniform(0, W), wall - rng.uniform(0, 30), rng.uniform(90, 170), ink=_mix(INK, JADE, 0.15))
    for x in (W * 0.35, W * 0.62):
        pagoda(d, x, wall - 20, rng.uniform(110, 150), rng.randint(5, 7))
    hall(d, W * 0.5, wall - 30, 260)
    img = np.asarray(pil, np.float32).copy()
    mist(img, H * 0.95, 60, 0.75, rng)
    return img


def scene_ruin(seed):
    rng = random.Random(seed)
    img = silk(W, H, rng, dark=0.08)
    disk(img, W * 0.68, H * 0.24, 52, _mix(CINNABAR, SILK, 0.25), 0.55)
    for base, amp, col, a in ((H * 0.45, 80, _mix(JADE, SILK, 0.5), 0.5), (H * 0.62, 60, _mix(INK, JADE, 0.3), 0.6)):
        paint_range(img, ridge(W, base, amp, 0.58, rng), col, a, 100, rng)
        mist(img, base + 70, 50, 0.5, rng)
    pil = to_image(img)
    d = ImageDraw.Draw(pil)
    ground = H * 0.84
    d.rectangle([0, ground, W, H], fill=_mix(INK, SILK, 0.2))
    for _ in range(11):                                       # colonne spezzate
        x = rng.uniform(0.05, 0.95) * W
        hgt = rng.uniform(60, 260)
        d.rectangle([x - 14, ground - hgt, x + 14, ground], fill=INK)
        d.polygon([(x - 16, ground - hgt), (x + 16, ground - hgt - rng.uniform(-25, 25)), (x + 16, ground - hgt + 10)],
                  fill=INK)
    x = W * 0.42                                              # un portale caduto a metà
    d.rectangle([x - 150, ground - 260, x - 124, ground], fill=INK)
    d.rectangle([x + 124, ground - 170, x + 150, ground], fill=INK)
    d.polygon([(x - 200, ground - 260), (x + 60, ground - 300), (x + 70, ground - 280), (x - 190, ground - 240)], fill=INK)
    for _ in range(6):
        px = rng.uniform(0, W)
        pine(d, px, ground + 4, rng.uniform(50, 90), rng)
    img = np.asarray(pil, np.float32).copy()
    mist(img, H * 0.9, 50, 0.6, rng)
    return img


def scene_forbidden(seed):
    rng = random.Random(seed)
    img = silk(W, H, rng, base=(176, 150, 140), dark=0.25)
    disk(img, W * 0.5, H * 0.18, 60, (120, 20, 26), 0.9)
    for i, (base, amp, col, a) in enumerate(((H * 0.4, 120, (80, 40, 48), 0.6), (H * 0.58, 140, (46, 22, 30), 0.75),
                                             (H * 0.8, 90, (16, 12, 14), 0.92))):
        peaks = [(rng.uniform(0.05, 0.95) * W, rng.uniform(120, 260), rng.uniform(25, 60)) for _ in range(5)]
        paint_range(img, ridge(W, base, amp, 0.66, rng, peaks), col, a, 60, rng, texture=0.8)
        mist(img, base + 80, 40, 0.35, rng, color=(150, 90, 96))
    pil = to_image(img)
    d = ImageDraw.Draw(pil)
    for _ in range(4):                                        # crepe di luce rossa nella roccia
        x = rng.uniform(0.1, 0.9) * W
        bolt(d, x, H * 0.62, H * 0.98, rng, (190, 50, 40), 3)
    return np.asarray(pil, np.float32).copy()


# ---------------------------------------------------------------- i mondi (mappa)

def world(seed, tone):
    rng = random.Random(seed)
    base = {"mortale": SILK, "cielo": (200, 210, 206), "immortale": (214, 196, 156), "vuoto": (150, 156, 170)}[tone]
    img = silk(W, H, rng, base=base, dark=0.05 if tone != "vuoto" else 0.2)
    if tone == "mortale":
        disk(img, W * 0.82, H * 0.2, 44, CINNABAR, 0.75)
    elif tone == "immortale":
        disk(img, W * 0.5, H * 0.16, 70, GOLD, 0.7, glow=4)
    elif tone == "vuoto":
        for _ in range(140):
            disk(img, rng.uniform(0, W), rng.uniform(0, H * 0.6), rng.uniform(1, 3), (240, 236, 220), 0.9, glow=1)
    layers = 5 if tone == "mortale" else 4
    for i in range(layers):
        base_y = H * (0.30 + 0.14 * i)
        col = _mix(_mix(JADE, SILK, 0.6), INK, i / layers) if tone != "immortale" else _mix(GOLD, INK, 0.25 + i / (layers * 1.6))
        if tone == "cielo":
            base_y = H * (0.2 + 0.12 * i)                     # isole sospese: creste corte
        ys = ridge(W, base_y, 60 + 20 * i, 0.55, rng,
                   [(rng.uniform(0, W), rng.uniform(40, 160), rng.uniform(50, 160)) for _ in range(2)])
        paint_range(img, ys, col, 0.45 + 0.1 * i, 80 if tone != "cielo" else 35, rng)
        mist(img, base_y + (60 if tone != "cielo" else 30), 40, 0.6, rng)
    if tone == "mortale":                                     # un fiume che serpeggia
        pil = to_image(img)
        d = ImageDraw.Draw(pil, "RGBA")
        pts = [(x, H * 0.92 - 40 * math.sin(x / 210) - x * 0.05) for x in range(0, W + 40, 40)]
        d.line(pts, fill=(236, 230, 214, 110), width=14)
        d.line([(x, y + 3) for x, y in pts], fill=(236, 230, 214, 70), width=5)
        img = np.asarray(pil.filter(ImageFilter.GaussianBlur(1.2)), np.float32).copy()
    return img


# ---------------------------------------------------------------- i momenti

def moment_tribulation(seed):
    rng = random.Random(seed)
    img = silk(W, H, rng, base=(120, 122, 130), dark=0.35)
    img[: int(H * 0.45)] *= 0.55                                            # il cielo si chiude
    for _ in range(6):                                        # nubi d'inchiostro, in alto
        y = rng.uniform(-40, H * 0.22)
        ys = ridge(W, y, 40, 0.6, rng)
        paint_range(img, ys, (20, 22, 30), 0.45, 25, rng, edge=0.7)
    mist(img, H * 0.62, 70, 0.75, rng, color=(176, 178, 186))
    paint_range(img, ridge(W, H * 0.80, 50, 0.55, rng, [(W * 0.5, 170, 80)]), INK, 0.97, 80, rng)
    pil = to_image(img)
    d = ImageDraw.Draw(pil)
    for _ in range(3):
        bolt(d, rng.uniform(0.25, 0.75) * W, 0, H * 0.55, rng, (255, 236, 170), 6)
    pil = pil.filter(ImageFilter.GaussianBlur(0.6))
    d = ImageDraw.Draw(pil)
    for _ in range(3):
        bolt(d, rng.uniform(0.3, 0.7) * W, 0, H * 0.62, rng, GOLD, 3)
    top = H * 0.80 - 170                                     # il coltivatore sulla vetta, controluce
    d.ellipse([W * 0.5 - 7, top - 44, W * 0.5 + 7, top - 30], fill=(8, 8, 10))
    d.polygon([(W * 0.5 - 12, top - 30), (W * 0.5 + 12, top - 30), (W * 0.5 + 16, top + 4), (W * 0.5 - 16, top + 4)],
              fill=(8, 8, 10))
    bolt(d, W * 0.5 + 4, 0, top - 46, random.Random(seed + 1), (255, 246, 210), 4)       # la folgore che lo cerca
    return np.asarray(pil, np.float32).copy()


def moment_duel(seed):
    rng = random.Random(seed)
    img = silk(W, H, rng)
    disk(img, W * 0.5, H * 0.3, 120, _mix(CINNABAR, SILK, 0.15), 0.55, glow=1.5)
    paint_range(img, ridge(W, H * 0.5, 70, 0.55, rng), _mix(JADE, SILK, 0.5), 0.5, 90, rng)
    mist(img, H * 0.6, 50, 0.6, rng)
    ys = ridge(W, H * 0.78, 20, 0.5, rng)
    paint_range(img, ys, INK, 0.95, 60, rng)
    pil = to_image(img)
    d = ImageDraw.Draw(pil)
    for x, dirn in ((W * 0.4, 1), (W * 0.6, -1)):            # due figure, le lame che si guardano
        g = ys[int(x)]
        d.ellipse([x - 9, g - 118, x + 9, g - 100], fill=INK)
        d.polygon([(x - 16, g - 100), (x + 16, g - 100), (x + 22 * dirn, g), (x - 26 * dirn, g)], fill=INK)
        d.line([(x + 14 * dirn, g - 80), (x + 110 * dirn, g - 120)], fill=(70, 74, 72), width=4)
        d.polygon([(x - 18, g - 96), (x - 70 * dirn, g - 60), (x - 20, g - 70)], fill=_mix(INK, JADE, 0.3))
    return np.asarray(pil, np.float32).copy()


JOBS = {
    "luoghi/mountain": (scene_mountain, 11), "luoghi/city": (scene_city, 12), "luoghi/ruin": (scene_ruin, 13),
    "luoghi/forbidden_zone": (scene_forbidden, 14),
    "mondi/0": (lambda s: world(s, "mortale"), 20), "mondi/1": (lambda s: world(s, "cielo"), 21),
    "mondi/2": (lambda s: world(s, "immortale"), 22), "mondi/3": (lambda s: world(s, "vuoto"), 23),
    "momenti/tribolazione": (moment_tribulation, 30), "momenti/duello": (moment_duel, 31),
}


def main(argv: list[str]) -> int:
    all_ = "--tutto" in argv
    only = [a for a in argv if not a.startswith("--")]
    for slot, (fn, seed) in JOBS.items():
        if only and slot not in only:
            continue
        folder, name = slot.split("/")
        out = ROOT / folder
        out.mkdir(parents=True, exist_ok=True)
        if not all_ and any(out.glob(name + ".*")):
            print("già c'è:", slot)
            continue
        arr = fn(seed)
        pil = to_image(arr).filter(ImageFilter.GaussianBlur(0.35))
        seal(pil, int(W * 0.94), int(H * 0.8), 46, random.Random(seed))
        pil.save(out / f"{name}.jpg", quality=86)
        print("dipinto:", slot)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
