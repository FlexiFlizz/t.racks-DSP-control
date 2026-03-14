# Interface t.racks DSP Controller

Interface web de controle pour processeurs t.racks (Thomann/Musicrown).
Projet demarre pour le DSP 206, concu pour etre compatible multi-processeurs.

## Contexte

Ce projet fait partie d'un systeme de calage automatique (dossier parent `Calage-Systeme-IA/`).
L'interface est un des composants : elle permet le controle manuel et automatise des processeurs DSP t.racks via leur protocole TCP reverse-engineere.

### Inspiration
- App existante : [dsp-408-ui](https://github.com/Aeternitaas/dsp-408-ui) (Flutter/Dart, GPL-3.0)
- Cette app couvre le DSP 408 mais manque de fonctionnalites (pas de PEQ, comp, gate, delay, limiter)
- Notre interface vise a etre complete, propre, et multi-processeur

### Protocole t.racks
- **Connexion** : TCP port 9761 (Ethernet) ou USB HID (VID:0168, PID:0821)
- **Format trame** : `[0x10] [0x02] [DIR] [0x01] [LEN] [PAYLOAD...] [0x10] [0x03] [CHECKSUM]`
- **Checksum** : XOR de tous les octets entre header et footer, initialise a 1
- **Driver Python** : `../drivers/tracks_dsp206.py` (protocole complet, pret a l'emploi)
- **Simulateur** : `../tools/simulateur_dsp206.py` (emule un DSP 206 sur TCP pour dev sans hardware)

### Commandes protocole connues
| Cmd   | Fonction                          |
|-------|-----------------------------------|
| 0x10  | Handshake                         |
| 0x12  | Status (preset actif)             |
| 0x13  | Device info                       |
| 0x20  | Load preset                       |
| 0x22  | Commande inconnue (init)          |
| 0x14  | Commande inconnue (init)          |
| 0x24  | Config chunk (reponse)            |
| 0x27  | Get config chunk (sub-index 0x00-0x1C) |
| 0x29  | Get/set preset par index          |
| 0x2C  | Get nombre de presets             |
| 0x31  | Filtre passe-bas (LPF)            |
| 0x32  | Filtre passe-haut (HPF)           |
| 0x33  | PEQ parametrique (freq, Q, gain, type, bypass) |
| 0x34  | Gain canal (2 octets LE)          |
| 0x35  | Mute canal (on/off)               |
| 0x36  | Delay (experimental, non verifie) |
| 0x3A  | Matrice de routage (bitmask entrees) |
| 0x40  | Metres / keepalive (float16 par canal) |
| 0x48  | GEQ graphique (canal + bande + valeur) |

### Encodages
- **Gain** : `dB = (valeur_brute - 280) / 10.0` (resolution 0.1 dB au dessus de -20 dB, 0.5 dB en dessous)
- **Frequence PEQ** : logarithmique, 1000 pas, `freq_hz = 19.70 * (20160/19.70)^(brut/1000)`
- **Q PEQ** : logarithmique, 256 pas, `Q = 0.40 * 320^(brut/255)`
- **Gain PEQ/GEQ** : `dB = (valeur - 120) / 10.0` (plage -12 a +12 dB)
- **Metres** : IEEE 754 float16 demi-precision, little-endian

### Processeurs supportes (actuel et futur)
| Modele    | Topologie      | Statut           |
|-----------|----------------|------------------|
| DSP 206   | 2 in / 6 out   | Cible principale |
| DSP 408   | 4 in / 8 out   | Prevu            |
| DSP 306   | 3 in / 6 out   | Prevu            |
| DSP 204   | 2 in / 4 out   | Prevu            |

Tous utilisent le meme protocole TCP, seule la topologie (nombre de canaux) change.

## Stack technique

- **Framework** : Next.js (App Router)
- **UI** : shadcn/ui + Tailwind CSS + Radix UI
- **Graphiques** : A definir (recharts, d3, ou canvas custom pour les courbes EQ)
- **Backend/API** : Route handlers Next.js ou FastAPI Python
- **Communication DSP** : WebSocket vers un bridge Python (le navigateur ne peut pas faire de TCP brut)
- **Langue** : Interface en francais

## Architecture

```
interface-tracks/
  src/
    app/                    # Pages Next.js (App Router)
    components/
      ui/                   # Composants shadcn/ui
      dsp/                  # Composants specifiques DSP (gain, EQ, matrice, metres...)
    lib/
      protocol/             # Logique protocole t.racks (encodage/decodage)
      processors/           # Definitions par modele (DSP206, DSP408...)
      websocket/            # Client WebSocket vers le bridge Python
    hooks/                  # React hooks custom
    types/                  # Types TypeScript
  bridge/                   # Bridge Python (TCP DSP <-> WebSocket navigateur)
```

## Architecture de communication

```
Navigateur (Next.js) <--WebSocket--> Bridge Python <--TCP 9761--> DSP t.racks
                                         |
                                         v
                                   Simulateur (dev)
```

Le bridge Python est necessaire car le navigateur ne peut pas ouvrir de socket TCP brut.
Le bridge reutilise le driver `../drivers/tracks_dsp206.py`.

## Design

### Pages principales
1. **Dashboard** : Vue d'ensemble, metres temps reel, statut connexion
2. **Gain/Mute** : Faders par canal avec vu-metres
3. **PEQ** : Courbe EQ interactive avec points draggables (par canal)
4. **GEQ** : 31 bandes graphiques (entrees uniquement)
5. **Crossover** : HPF/LPF par sortie avec selection de pente
6. **Matrice** : Grille de routage entrees -> sorties
7. **Dynamique** : Compresseur, limiteur, gate (par canal)
8. **Delay** : Reglage delay par sortie (ms et metres)
9. **Presets** : Sauvegarde/chargement/renommage

### Principes de design
- Design sombre (theme dark) adapte a l'utilisation en regie/live
- Composants reactifs : les changements sont envoyes en temps reel au DSP
- Feedback visuel immediat (metres, courbes)
- Responsive mais optimise desktop (utilisation principale)
- Accessible (raccourcis clavier pour les operations courantes)

## Regles
- Ne jamais hardcoder le nombre de canaux : toujours se baser sur la config du processeur
- Privilegier l'EQ soustractif dans les suggestions automatiques
- Les metres doivent etre fluides (requestAnimationFrame, pas de re-render React complet)
- Le bridge Python doit gerer la reconnexion automatique au DSP
- Toute modification envoyee au DSP doit etre confirmee par une relecture (read-back)
