# Calage Systeme IA

Projet d'outil automatise de calage systeme son par IA.

## Contexte
- Boucle fermee : Mesure (REW) -> Analyse phase -> Calcul delay/EQ/all-pass -> Application DSP -> Re-mesure
- Cible : acousticiens independants, constructeurs DIY, small PA/soundsystem
- DSP cible : processeurs t.racks (Thomann/Musicrown) — protocole TCP reverse-engineere
- Langue : francais

## Deux modes de calage
- **Mode Script** : algorithmes fixes offline (delay par phase/IR, EQ soustractif, detection polarite)
- **Mode IA** : Claude Code dans un terminal — lit les mesures, lance les scripts, analyse et propose

## Stack technique
- **Backend** : Python + FastAPI (port 8765)
- **Frontend** : Next.js + shadcn/ui + Tailwind (port 3001)
- **DSP** : t.racks via TCP port 9761 (protocole binaire reverse-engineere)
- **Mesure** : REW API REST (port 4735, GET gratuit, POST necessite Pro)
- **Signal** : NumPy/SciPy pour traitement

## Lancer le projet
```bash
# Backend + simulateur DSP
python tools/simulateur_dsp206.py &
python -m uvicorn backend.main:app --port 8765

# Frontend
cd app && npm run dev
```

## Structure
```
backend/
  rew/           Client REW API + decodeur Base64
  dsp/           Abstraction DSP + driver t.racks (206/408/306/204)
  core/          Moteur de calage (phase, delay, EQ soustractif)
  cli/           Scripts CLI pour mode IA
  routers/       Endpoints FastAPI (rew, dsp, calage, systeme, presets)
  models/        Modeles de donnees
  presets/       Bibliotheque d'enceintes (JSON)
app/             Frontend Next.js + shadcn/ui
drivers/         Driver bas-niveau t.racks
tools/           Simulateur DSP 206
interface-tracks/  Interface t.racks standalone (projet separe)
```

## Pages de l'interface
- **Dashboard** : statuts REW/DSP, metres temps reel
- **Mesures** : liste et details des mesures REW
- **Enceintes** : bibliotheque de presets (17 built-in + custom) + configuration du systeme
- **DSP** : connexion et controle du processeur t.racks (gain, mute, metres)
- **Calage** : definition paires, courbes SPL/phase, onglets Delay/Phase/EQ, terminal + journal
- **Parametres** : configuration

## Scripts CLI (mode IA)
```bash
python -m backend.cli.lire_mesure              # lister les mesures REW
python -m backend.cli.lire_mesure 0 --phase    # voir une mesure
python -m backend.cli.analyser 0 1 --crossover 120  # calage sub/top
python -m backend.cli.analyser 0 --seuil 3     # EQ correctif
python -m backend.cli.appliquer --host 127.0.0.1 eq-auto 0 "Out 1"
python -m backend.cli.comparer 0 1             # comparer avant/apres
python -m backend.cli.etat_dsp --host 127.0.0.1
```

## APIs
- REW : GET/POST http://localhost:4735/ (Swagger UI)
  - /measurements : dict indexe par numero (1-based, pas 0-based)
  - magnitude/phase en Base64 float32 big-endian
  - Cles REW v5.40 : 'magnitude' (pas 'magnitudes'), 'data' (pas 'samples'), 'startFreq'+'ppo'
- t.racks DSP : TCP port 9761, protocole binaire
- Backend : http://127.0.0.1:8765 (FastAPI, Swagger sur /docs)

## Systeme d'enceintes
- Bibliotheque de presets : backend/presets/enceintes.json (17 presets built-in)
- Presets custom : backend/presets/custom.json (crees par l'utilisateur)
- Chaque enceinte : nom, type (sub/top/fill/delay/monitor), HP, canal DSP, HPF, LPF
- Paires : deux enceintes a caler, crossover auto-calcule depuis LPF bas / HPF haut
- Persistance : systeme.json

## Regles
- Toujours privilegier l'EQ soustractif (couper les pics, pas booster les creux)
- La trace de phase est la reference pour le calage sub/top (pas l'IR seule)
- Ne jamais hardcoder le nombre de canaux (supporter DSP 206/408/306/204)
- Le simulateur (tools/simulateur_dsp206.py) permet de tester sans hardware
- REW indexe les mesures a partir de 1 (le client convertit 0-based → 1-based)
