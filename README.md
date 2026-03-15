# Calage Systeme IA

Outil automatise de calage systeme son par IA. Boucle fermee : **Mesure → Analyse → Correction → Verification**.

Cible : acousticiens independants, constructeurs DIY, small PA / soundsystem.

## Le probleme

Les outils pro (Smaart, SysTune) mesurent mais ne corrigent pas. Les outils qui corrigent (Dirac, TRACT) ne controlent pas de DSP externe. Les ecosystemes constructeurs (L-Acoustics, d&b) sont fermes a leur materiel. **Aucun outil open-source ne fait la boucle fermee pour le live/PA.**

## La solution

```
REW (mesure) → Calage Systeme IA (analyse + calcul) → DSP t.racks (application)
                         ↑                                        |
                         └────────── Re-mesure ←──────────────────┘
```

## Fonctionnalites

### Deux modes de calage
- **Mode Script** : algorithmes fixes offline — delay par analyse de phase/IR, detection polarite, EQ soustractif automatique
- **Mode IA** : Claude Code en terminal — analyse intelligente des mesures, strategies adaptees, explications en francais

### Interface web
- **Dashboard** : statuts REW/DSP, metres temps reel
- **Enceintes** : bibliotheque de presets (17 built-in + custom), definition du systeme
- **Mesures** : lecture des mesures REW en temps reel
- **DSP** : controle du processeur t.racks (gain, mute, delay, EQ)
- **Calage** : wizard par paires (Sub↔Top, Top↔Fill...), onglets Delay/Phase/EQ, courbes SPL et phase, terminal integre

### Backend
- Client REW API REST complet
- Driver t.racks reverse-engineere (protocole TCP binaire)
- Moteur de calage : analyse de phase, calcul delay optimal, EQ soustractif
- Simulateur DSP pour tests sans hardware
- Scripts CLI pour le mode IA

## Stack technique

| Composant | Techno |
|-----------|--------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | Next.js 16 / shadcn/ui / Tailwind |
| Signal | NumPy / SciPy |
| Mesure | REW API REST (localhost:4735) |
| DSP | t.racks USB HID + TCP 9761 (reverse-engineere) |

## DSP supportes

| Modele | Topologie | Statut |
|--------|-----------|--------|
| t.racks DSP 206 | 2 in / 6 out | Verifie sur hardware reel |
| t.racks DSP 408 | 4 in / 8 out | Supporte (meme protocole) |
| t.racks DSP 306 | 3 in / 6 out | Supporte (meme protocole) |
| t.racks DSP 204 | 2 in / 4 out | Supporte (meme protocole) |

## Protocole t.racks DSP 206 (reverse-engineere)

Protocole binaire proprietaire, entierement decode par capture Wireshark du Processor Editor.
Connexion USB HID (VID:0168 PID:0821) ou TCP port 9761.

### Table des commandes

| Cmd | Fonction | Payload | Verifie |
|-----|----------|---------|---------|
| 0x10 | Handshake | - | Oui |
| 0x13 | Device Info | - | Oui |
| 0x20 | Recall Preset | slot_index | Oui |
| 0x21 | Store Preset | slot_index | Oui |
| 0x26 | Store Name | name (14B ASCII) | Oui |
| 0x27 | Get Config | chunk_index | Oui |
| 0x29 | Get Preset | slot_index | Oui |
| 0x2A | Lock | ch, val | Capture |
| 0x2D | Copy (exec) | 00, src, dest | Capture |
| 0x2F | Copy (setup) | src, dest | Capture |
| 0x30 | Compresseur | ch, ratio(2B), atk(2B), rel(2B), knee(2B), thresh(2B) | Oui |
| 0x31 | LPF | ch, freq(2B), slope | Oui |
| 0x32 | HPF | ch, freq(2B), slope | Oui |
| 0x33 | PEQ | ch, band, gain(2B), freq(2B), Q(1B), type(1B), bypass(1B) | Oui |
| 0x34 | Gain | ch, val(2B LE) | Oui |
| 0x35 | Mute | ch, on/off | Oui |
| 0x36 | Phase Invert | ch, on/off | Oui |
| 0x38 | Delay | ch, val(2B LE) [type=0x02] | Oui |
| 0x39 | Test Tone | type, param | Oui |
| 0x3A | Matrice | ch, bitmask | Oui |
| 0x3B | Link | ch, mask | Capture |
| 0x3D | Channel Name | ch, name(8B ASCII) | Oui |
| 0x3E | Gate | ch, atk(2B), rel(2B), hold(2B), thresh(2B) | Oui |
| 0x3F | Limiter | ch, atk(2B), rel(2B), ??(2B), thresh(2B) | Oui |
| 0x40 | Metres | - | Oui |
| 0x48 | GEQ | ch, band, val(2B) | Oui |

### Encodages (calibres sur hardware)

| Parametre | Formule | Inverse |
|-----------|---------|---------|
| Gain canal | dB = (brut - 280) / 10 | brut = dB * 10 + 280 |
| Gain PEQ/GEQ | dB = (brut - 120) / 10 | brut = dB * 10 + 120 |
| Frequence (PEQ/HPF/LPF) | Hz = 20 * 1000^(brut/300) | brut = 300 * log10(Hz/20) / 3 |
| Q (PEQ) | Q = 10^((brut-16)/40) | brut = 40 * log10(Q) + 16 |
| Delay | ms = brut / 96 | brut = ms * 96 |
| Threshold (comp/gate/lim) | dB = (brut - 180) / 2 | brut = dB * 2 + 180 |
| Attack/Release/Hold | ms = brut + 1 | brut = ms - 1 |
| Knee (comp) | dB = brut | brut = dB |
| Ratio (comp) | index 0-15 | Table fixe |

### Mapping canaux DSP 206

| Index | Canal |
|-------|-------|
| 0x00 | In A |
| 0x01 | In B |
| 0x02 | Out 1 |
| 0x03 | Out 2 |
| 0x04 | Out 3 |
| 0x05 | Out 4 |
| 0x06 | Out 5 |
| 0x07 | Out 6 |

### Pentes HPF/LPF (20 + bypass)

0x00=bypass, 0x01=BW-6, 0x02=BL-6, 0x03=BW-12, 0x04=BL-12, 0x05=LK-12,
0x06=BW-18, 0x07=BL-18, 0x08=BW-24, 0x09=BL-24, 0x0A=LK-24,
0x0B=BW-30, 0x0C=BL-30, 0x0D=BW-36, 0x0E=BL-36, 0x0F=LK-36,
0x10=BW-42, 0x11=BL-42, 0x12=BW-48, 0x13=BL-48, 0x14=LK-48

### Types PEQ (0-indexed)

0=Peak, 1=Low Shelf, 2=High Shelf, 3=LP-6dB, 4=LP-12dB,
5=HP-6dB, 6=HP-12dB, 7=Allpass1, 8=Allpass2

### Ratios compresseur

0=1:1, 1=1:1.1, 2=1:1.3, 3=1:1.5, 4=1:1.7, 5=1:2, 6=1:2.5, 7=1:3,
8=1:3.5, 9=1:4, 10=1:5, 11=1:6, 12=1:8, 13=1:10, 14=1:20, 15=Limit

## Installation

### Prerequis
- Python 3.11+
- Node.js 18+
- REW (Room EQ Wizard) avec l'API activee

### Setup

```bash
# Cloner
git clone https://github.com/FlexiFlizz/Calage-Systeme-IA.git
cd Calage-Systeme-IA

# Backend
pip install -r requirements.txt

# Frontend
cd app && npm install && cd ..
```

### Lancer

```bash
# Terminal 1 : Simulateur DSP (optionnel, pour tester sans hardware)
python tools/simulateur_dsp206.py --verbose

# Terminal 2 : Backend
python -m uvicorn backend.main:app --port 8765

# Terminal 3 : Frontend
cd app && npm run dev
```

Ouvrir **http://localhost:3001** dans le navigateur.

## Mode IA (Claude Code)

Ouvrir Claude Code dans le dossier du projet :

```bash
claude
> Analyse les mesures 0 et 1 et cale le sub/top a 120 Hz
> Propose un EQ correctif pour la mesure 0
> Compare avant et apres correction
```

Claude Code utilise les scripts CLI :

```bash
python -m backend.cli.lire_mesure              # Lister les mesures REW
python -m backend.cli.lire_mesure 0 --phase    # Voir une mesure
python -m backend.cli.analyser 0 1 --crossover 120  # Calage sub/top
python -m backend.cli.analyser 0 --seuil 3     # EQ correctif
python -m backend.cli.appliquer --host 127.0.0.1 eq-auto 0 "Out 1"
python -m backend.cli.comparer 0 1             # Comparer avant/apres
python -m backend.cli.etat_dsp --host 127.0.0.1
```

## Principes de calage

- **EQ soustractif uniquement** : couper les pics, ne jamais booster les creux
- **Phase = reference** : la trace de phase guide le calage sub/top, pas l'IR seule
- **Sequence** : Delay → Polarite → All-pass → EQ
- **Crossover auto** : calcule depuis le LPF du sub et le HPF du top

## Structure du projet

```
backend/
  rew/           Client REW API + decodeur Base64
  dsp/           Abstraction DSP + driver t.racks
  core/          Moteur de calage (phase, delay, EQ)
  cli/           Scripts CLI pour mode IA
  routers/       Endpoints FastAPI
  presets/       Bibliotheque d'enceintes
  models/        Modeles de donnees
app/             Frontend Next.js + shadcn/ui
drivers/         Driver bas-niveau protocole t.racks
tools/           Simulateur DSP + app dsp-408-ui
```

## Licence

Projet prive.

## Credits

- Protocole t.racks reverse-engineere a partir de [dsp-408-ui](https://github.com/Aeternitaas/dsp-408-ui)
- REW (Room EQ Wizard) par John Mulcahy
- Methodologie de calage inspiree de Bob McCarthy (Sound Systems: Design and Optimization)
