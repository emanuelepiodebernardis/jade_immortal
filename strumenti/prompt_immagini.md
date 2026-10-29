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

## bestie/ (1:1)
| file | soggetto |
|---|---|
| drago | Chinese dragon coiling through clouds, jade scales, pearl |
| fenice | fenghuang phoenix in flight, cinnabar and gold plumage |
| tigre | white tiger on a rock, fierce, ink fur strokes |
| tartaruga | black tortoise with a serpent coiled around its shell, Xuanwu |
| qilin | qilin with deer antlers and dragon scales, hooves of fire |
| gru | red-crowned crane among pines |
| volpe | nine-tailed fox spirit, white fur, glowing eyes |
| serpente | celestial serpent with a jewel on the brow |
| kun | Kun, the colossal fish turning into the Peng bird, waves and clouds |

## creature/ (1:1)
| file | soggetto |
|---|---|
| beast | savage spirit beast with stone-like hide, glowing eyes, ink and wash |
| demon | horned demon cultivator wreathed in black qi, cinnabar eyes |
| spirit | wandering ghost spirit, translucent, trailing mist |
