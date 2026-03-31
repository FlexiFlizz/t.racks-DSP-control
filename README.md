# Calage Systeme

Outil open-source de calage et d'alignement systeme son pour processeurs **t.racks DSP** (Thomann/Musicrown).

Boucle fermee complete : **Mesure → Analyse → Correction DSP → Verification**.

---

## Fonctionnalites

### Calage systeme
- Alignement temporel sub/top par analyse de phase et reponse impulsionnelle
- Detection automatique de polarite
- EQ soustractif automatique (couper les pics, pas booster les creux)
- Crossover auto-calcule depuis les filtres HPF/LPF du systeme
- Sequence de calage : Delay → Polarite → All-pass → EQ

### Interface web
- Dashboard avec statuts REW/DSP et metres temps reel
- Bibliotheque d'enceintes (17 presets built-in + custom)
- Visualisation des mesures REW (SPL, phase)
- Controle complet du DSP (gain, mute, delay, EQ, crossover, dynamics)
- Wizard de calage par paires (Sub/Top, Top/Fill, L/R...)
- Terminal integre avec journal d'operations

### Controle DSP
- Connexion USB HID ou TCP/IP
- Lecture/ecriture de tous les parametres en temps reel
- Metering float16 IEEE 754
- Gestion des presets (load, store, rename)
- Simulateur DSP integre pour tests sans hardware

### Integration REW
- Client API REST complet (Room EQ Wizard)
- Decodage des mesures Base64 float32 big-endian
- Lecture magnitude, phase, reponse impulsionnelle

---

## DSP supportes

| Modele | Topologie | Statut |
|--------|-----------|--------|
| t.racks DSP 206 | 2 in / 6 out | Verifie sur hardware |
| t.racks DSP 408 | 4 in / 8 out | Supporte |
| t.racks DSP 306 | 3 in / 6 out | Supporte |
| t.racks DSP 204 | 2 in / 4 out | Supporte |

---

## Protocole t.racks (reverse-engineere)

Protocole binaire proprietaire, integralement decode par capture Wireshark du logiciel Processor Editor officiel.

### Trame

```
[0x10] [0x02] [DIR] [0x02] [LEN] [CMD] [DATA...] [0x10] [0x03] [CHECKSUM]
```

- `DIR` : 0x00 = host → DSP, 0x01 = DSP → host
- `CHECKSUM` : XOR des octets entre header et footer, init a 1
- Transport : USB HID (VID:0168 PID:0821, reports 65 octets) ou TCP port 9761

### Table des commandes

| Cmd | Fonction | Payload |
|-----|----------|---------|
| `0x10` | Handshake | — |
| `0x13` | Device Info | — |
| `0x20` | Recall Preset | slot |
| `0x21` | Store Preset | slot |
| `0x26` | Store Name | name (14B ASCII) |
| `0x27` | Get Config | chunk_index |
| `0x29` | Get Preset Name | slot |
| `0x2A` | Lock | ch, val |
| `0x2D` | Copy (exec) | 00, src, dest |
| `0x2F` | Copy (setup) | src, dest |
| `0x30` | Compresseur | ch, ratio(2B), atk(2B), rel(2B), knee(2B), thresh(2B) |
| `0x31` | LPF | ch, freq(2B), slope |
| `0x32` | HPF | ch, freq(2B), slope |
| `0x33` | PEQ | ch, band, gain(2B), freq(2B), Q(1B), type(1B), bypass(1B) |
| `0x34` | Gain | ch, val(2B LE) |
| `0x35` | Mute | ch, on/off |
| `0x36` | Phase Invert | ch, on/off |
| `0x38` | Delay | ch, val(2B LE) |
| `0x39` | Test Tone | type, param |
| `0x3A` | Matrice Routing | output_ch, input_bitmask |
| `0x3B` | Link | ch, mask |
| `0x3D` | Channel Name | ch, name(8B ASCII) |
| `0x3E` | Gate | ch, atk(2B), rel(2B), hold(2B), thresh(2B) |
| `0x3F` | Limiter | ch, atk(2B), rel(2B), ??(2B), thresh(2B) |
| `0x40` | Metres | — |
| `0x48` | GEQ | ch, band, val(2B) |

### Encodages verifies sur hardware

| Parametre | Encodage | Decodage |
|-----------|----------|----------|
| Gain canal | `brut = dB * 10 + 280` | `dB = (brut - 280) / 10` |
| Gain PEQ/GEQ | `brut = dB * 10 + 120` | `dB = (brut - 120) / 10` |
| Frequence | `brut = 300 * log10(Hz/20) / 3` | `Hz = 20 * 1000^(brut/300)` |
| Q (PEQ) | `brut = 40 * log10(Q) + 16` | `Q = 10^((brut-16)/40)` |
| Delay | `brut = ms * 96` | `ms = brut / 96` |
| Threshold | `brut = dB * 2 + 180` | `dB = (brut - 180) / 2` |
| Attack/Release/Hold | `brut = ms - 1` | `ms = brut + 1` |
| Knee | `brut = dB` | `dB = brut` |

### Mapping canaux (DSP 206)

| Index | Canal | Index | Canal |
|-------|-------|-------|-------|
| 0x00 | In A | 0x04 | Out 3 |
| 0x01 | In B | 0x05 | Out 4 |
| 0x02 | Out 1 | 0x06 | Out 5 |
| 0x03 | Out 2 | 0x07 | Out 6 |

### Pentes HPF/LPF

| Index | Type | Index | Type | Index | Type |
|-------|------|-------|------|-------|------|
| 0x00 | Bypass | 0x08 | BW-24 | 0x10 | BW-42 |
| 0x01 | BW-6 | 0x09 | BL-24 | 0x11 | BL-42 |
| 0x02 | BL-6 | 0x0A | LK-24 | 0x12 | BW-48 |
| 0x03 | BW-12 | 0x0B | BW-30 | 0x13 | BL-48 |
| 0x04 | BL-12 | 0x0C | BL-30 | 0x14 | LK-48 |
| 0x05 | LK-12 | 0x0D | BW-36 | | |
| 0x06 | BW-18 | 0x0E | BL-36 | | |
| 0x07 | BL-18 | 0x0F | LK-36 | | |

BW = Butterworth, BL = Bessel, LK = Linkwitz-Riley

### Types PEQ

| Index | Type | Index | Type |
|-------|------|-------|------|
| 0 | Peak | 5 | HP -6dB |
| 1 | Low Shelf | 6 | HP -12dB |
| 2 | High Shelf | 7 | Allpass 1 |
| 3 | LP -6dB | 8 | Allpass 2 |
| 4 | LP -12dB | | |

### Ratios compresseur

| Index | Ratio | Index | Ratio | Index | Ratio | Index | Ratio |
|-------|-------|-------|-------|-------|-------|-------|-------|
| 0 | 1:1 | 4 | 1:1.7 | 8 | 1:3.5 | 12 | 1:8 |
| 1 | 1:1.1 | 5 | 1:2 | 9 | 1:4 | 13 | 1:10 |
| 2 | 1:1.3 | 6 | 1:2.5 | 10 | 1:5 | 14 | 1:20 |
| 3 | 1:1.5 | 7 | 1:3 | 11 | 1:6 | 15 | Limit |

### Metering

Reponse a la commande `0x40` : 3 octets par canal (8 canaux sur DSP 206).

```
[float16_lo] [float16_hi] [peak_byte]
```

Niveau lineaire en IEEE 754 half-precision little-endian. Peak byte proportionnel au niveau (0-255).

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python / FastAPI |
| Frontend | Next.js / shadcn/ui / Tailwind |
| Traitement signal | NumPy / SciPy |
| Mesure | REW API REST |
| DSP | USB HID + TCP 9761 |

---

## Architecture

```
backend/
  rew/           Client REW API + decodeur Base64
  dsp/           Abstraction DSP + driver t.racks (206/408/306/204)
  core/          Moteur de calage (phase, delay, EQ soustractif)
  cli/           Scripts CLI
  routers/       Endpoints FastAPI
  presets/       Bibliotheque d'enceintes (JSON)
  models/        Modeles de donnees
app/             Frontend Next.js
drivers/         Driver bas-niveau protocole t.racks
tools/           Simulateur DSP
```

---

## Licence

MIT

## Credits

- Protocole t.racks decode a partir de captures Wireshark du Processor Editor
- Travail initial inspire de [dsp-408-ui](https://github.com/Aeternitaas/dsp-408-ui) (Aeternitaas)
- REW (Room EQ Wizard) par John Mulcahy
- Methodologie de calage : Bob McCarthy — *Sound Systems: Design and Optimization*
