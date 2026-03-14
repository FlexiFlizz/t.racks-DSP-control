# Calage Systeme IA

Projet d'outil automatise de calage systeme son par IA.

## Contexte
- Boucle fermee : Mesure (REW) -> Analyse phase -> Calcul delay/EQ/all-pass -> Application DSP -> Re-mesure
- Cible : acousticiens independants, constructeurs DIY, small PA/soundsystem
- DSP cible : processeurs t.racks (Thomann/Musicrown) — protocole TCP reverse-engineere
- Langue : francais

## Stack technique
- Python (langage principal)
- REW API REST (localhost:4735) pour mesure et analyse
- DSP : t.racks via TCP port 9761 (protocole binaire propriétaire, reverse-engineere)
- NumPy/SciPy pour traitement de signal
- FastAPI pour le backend (port 8765)
- Electron + Next.js + shadcn/ui pour le frontend (a venir)

## Deux modes de calage
- **Mode Script** : algorithmes fixes offline (delay par phase/IR, EQ soustractif, detection polarite)
- **Mode IA** : Claude Code dans un terminal — lit les mesures, lance les scripts, analyse et propose

## Scripts CLI (mode IA)
```bash
# Lister les mesures REW
python -m backend.cli.lire_mesure

# Afficher une mesure avec phase
python -m backend.cli.lire_mesure 0 --phase --ir

# Analyser une mesure (EQ correctif)
python -m backend.cli.analyser 0

# Calage sub/top (deux mesures)
python -m backend.cli.analyser 0 1 --crossover 120

# Appliquer des corrections sur le DSP
python -m backend.cli.appliquer gain "Out 1" -6.0
python -m backend.cli.appliquer delay "Out 1" 2.5
python -m backend.cli.appliquer peq "Out 1" 0 -3.0 250 2.0
python -m backend.cli.appliquer eq-auto 0 "Out 1"

# Lire l'etat du DSP
python -m backend.cli.etat_dsp --host 127.0.0.1

# Comparer avant/apres
python -m backend.cli.comparer 0 1
```

## APIs
- REW : GET/POST http://localhost:4735/ (GET gratuit, POST necessite Pro)
- t.racks DSP : TCP port 9761, protocole binaire (voir drivers/tracks_dsp206.py)

## Structure backend
- `backend/rew/` : client REW API + decodeur Base64
- `backend/dsp/` : abstraction DSP + driver t.racks
- `backend/core/` : moteur de calage (phase, delay, EQ)
- `backend/cli/` : scripts CLI pour le mode IA
- `backend/routers/` : endpoints FastAPI
- `drivers/` : driver bas-niveau t.racks
- `tools/` : simulateur DSP 206

## Regles
- Toujours privilegier l'EQ soustractif (couper les pics, pas booster les creux)
- La trace de phase est la reference pour le calage sub/top (pas l'IR seule)
- Ne jamais hardcoder le nombre de canaux (supporter DSP 206/408/306/204)
- Le simulateur (tools/simulateur_dsp206.py) permet de tester sans hardware
