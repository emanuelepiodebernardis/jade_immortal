# Prompt per le immagini del gioco (Higgsfield o qualunque generatore)

Tutte le immagini condividono lo **stile base**: incollalo all'inizio di ogni prompt, poi aggiungi il soggetto.
Salva ogni immagine in `immagini/<cartella>/<nome>.png` (o .jpg/.webp): il gioco la usa da sola.

**Importante (provato):** metti PRIMA il soggetto e POI lo stile. Per gli uomini scrivi sempre
«a MAN, masculine face, strong jawline, thick eyebrows, broad shoulders» e l'età: altrimenti il generatore fa
volti femminili. Le immagini del gioco sono state fatte così con Pollinations.ai (gratuito, un'immagine ogni 45 s).

**Stile base (sempre, in coda):**
> traditional Chinese ink wash painting (shuimo) on aged silk, xianxia cultivation fantasy, expressive brush strokes,
> mineral pigment accents of jade green, cinnabar red and gold leaf, soft drifting mist, muted warm palette,
> elegant, painterly, no text, no watermark, no frame

**Negativo (se il generatore lo accetta):** photo, 3d render, anime, cartoon, modern clothing, text, letters, watermark, signature, extra fingers, deformed hands

Formato: ritratti **1:1** (mezzo busto, tre quarti, sfondo di nebbia chiara); bestie e creature **1:1** (figura intera); i luoghi, i mondi e i momenti sono già dipinti da `strumenti/dipingi_sfondi.py`, ma puoi sostituirli (formato **8:3** o 16:9).

## ritratti/ (1:1)
| file | soggetto |
|---|---|
| eroe | young male cultivator protagonist, sharp calm eyes, long black hair tied with a jade pin, dark green and black robes, faint qi glowing around one hand |
| patriarca | ancient sect patriarch, long white beard, imposing, ornate dark robes with gold embroidery, eyes like deep wells |
| anziano | sect elder, grey hair in a topknot, stern face, grey-blue robes, hands behind back |
| eremita | mountain hermit, wild grey hair, simple undyed hemp robe, holding a gourd, serene smile |
| discepolo | young sect disciple, eager face, white and pale blue sect uniform, a sword on the back |
| guardia | sect guard, lean and scarred, lamellar armor over dark robes, a spear |
| mercante | plump wandering merchant, sly smile, rich brocade, abacus and pouches |
| vagabondo | ragged rogue cultivator, unkempt hair, patched robe, wary eyes, a chipped saber |
| cacciatore | demon hunter, hooded, fur mantle, bow and talismans at the belt |
| f | young female cultivator, graceful, long black hair with a cinnabar ribbon, flowing pale jade robes |
| f_anziana | elderly female sect master, silver hair in an elaborate bun, dignified, deep violet robes |

## I compagni perduti (ritratti/ — usa il nome del personaggio come nome del file)
Per il Trasmigratore: `Marco Rinaldi`, `Giulia Ferri`, `Sara Conti`, `Davide Moretti`, `Luca Bianchi`.
| chi | soggetto |
|---|---|
| l'amico (Marco Rinaldi) | young man in torn servant clothes, a scar on the neck, tired but kind eyes |
| la santa (Giulia Ferri) | young saintess of a righteous sect, white veil and silver crown, composed face hiding emotion |
| la prigioniera (Sara Conti) | young woman with pale skin and closed eyes, faint alchemical qi swirling around her, red-gold robes |
| il caduto (Davide Moretti) | young demonic cultivator, crimson eyes, black robes with blood-red trim, a cold smile |
| il cacciatore (Luca Bianchi) | young hunter with a black blade, haunted eyes, a shadowy voice-like mist around his head |

## bestie/ (1:1) — versione mistica (da rifare)
Le bestie attuali sono troppo semplici (cornici, la tartaruga è una macchia, il qilin sembra una capra).
Per queste usa questo **stile al posto di quello base**, in coda al soggetto:
> ethereal xianxia mythology, divine sacred beast, traditional Chinese ink wash painting blended with luminous mineral
> pigments, glowing qi aura, swirling auspicious clouds, drifting mist, rays of celestial light, gold leaf highlights,
> jade green and cinnabar accents, deep mysterious atmosphere, masterpiece, full bleed composition, no border, no frame,
> no text, no watermark

| file | soggetto |
|---|---|
| drago | majestic azure Chinese dragon (long) coiling through stormy clouds above sacred mountain peaks, long serpentine body, jade and sapphire scales shimmering, flowing whiskers, chasing a glowing flaming pearl, lightning in the clouds |
| fenice | divine fenghuang phoenix rising with wings fully spread, long flowing tail feathers of cinnabar, gold and violet trailing like flames and silk ribbons, sacred fire halo behind it, soaring over a sea of clouds at dawn |
| gru | celestial red-crowned crane immortal mount dancing above a misty sacred lake, wings spread, silver-white luminous feathers, ancient twisted pine on a cliff, full moon, floating petals of light |
| kun | colossal mythical Kun fish breaching from a dark endless ocean and transforming into the giant Peng bird, half fish half vast wings, enormous scale, tiny mountains below, swirling cosmic waves and clouds |
| qilin | sacred qilin unicorn beast, dragon head with single antler-like horns, deer body covered in shimmering jade scales, flowing mane of flame, hooves wreathed in golden fire, walking on clouds without touching the ground, benevolent and noble |
| serpente | celestial serpent spirit with a glowing jewel on its brow, immense coiling body of iridescent black and emerald scales, coiled around an ancient stone pillar with runes, moonlit mist, eyes glowing gold |
| tartaruga | Xuanwu the Black Tortoise of the North, a giant ancient tortoise with a mountain-like dark shell carved with glowing constellations, a black serpent coiled around it, rising from a dark ocean under a starry night sky |
| tigre | Baihu the White Tiger of the West, majestic divine white tiger with black ink stripes, glowing silver-blue eyes, standing on a jagged cliff, wind of metal blades and autumn leaves swirling, celestial light behind |
| volpe | nine-tailed fox spirit huli jing, elegant white fox with nine luminous flowing tails fanned like a halo, glowing violet eyes, foxfire orbs floating around, moonlit bamboo forest, mysterious and enchanting |

Pollinations gratuito: **una immagine ogni 45 secondi**, formato 768×768, poi `strumenti/sistema_scaricate.py`.

## creature/ (1:1)
| file | soggetto |
|---|---|
| beast | savage spirit beast with stone-like hide, glowing eyes, ink and wash |
| demon | horned demon cultivator wreathed in black qi, cinnabar eyes |
| spirit | wandering ghost spirit, translucent, trailing mist |
