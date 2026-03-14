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
| DSP | t.racks TCP 9761 (reverse-engineere) |

## DSP supportes

| Modele | Topologie | Statut |
|--------|-----------|--------|
| t.racks DSP 206 | 2 in / 6 out | Supporte |
| t.racks DSP 408 | 4 in / 8 out | Supporte (meme protocole) |
| t.racks DSP 306 | 3 in / 6 out | Supporte (meme protocole) |
| t.racks DSP 204 | 2 in / 4 out | Supporte (meme protocole) |

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
