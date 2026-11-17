# Smart Farm IoT — Simulation d'une serre connectée sécurisée

Mini-projet IoT (EPITA) réalisé par **Idrissa Bidanessy** et **Dhruv Patel**.

Une serre est simulée en Python : deux capteurs (température, humidité), un contrôleur et deux actionneurs
(ventilation, irrigation) communiquent via un broker **MQTT Mosquitto** exécuté sous **WSL (Ubuntu)**.
Le système est d'abord construit sans sécurité (Jour 1), analysé et attaqué (Jour 2), puis sécurisé
progressivement (Jours 2 et 3).

## Architecture

```
 Capteur_temperature ──/farm/temperature──┐
                                          ▼
                                   ┌─────────────┐   /farm/commands/ventilation ──► ventilation
                                   │  Mosquitto  │◄──────── Controleur ────────────
                                   │   (broker)  │   /farm/commands/irrigation  ──► irrigation
                                   └─────────────┘
 Capteur_humidity ───/farm/humidity───────┘              monitor (écoute /farm/# → alerts.log)
```

| Topic | Émetteur | Récepteur |
|---|---|---|
| `/farm/temperature` | capteur température | contrôleur |
| `/farm/humidity` | capteur humidité | contrôleur |
| `/farm/commands/ventilation` | contrôleur | ventilation |
| `/farm/commands/irrigation` | contrôleur | irrigation |

Règles du contrôleur : température > 30 °C → ventilation ON ; humidité < 40 % → irrigation ON.

## Structure du projet

| Fichier | Rôle |
|---|---|
| `Capteur_temperature.py`, `Capteur_humidity.py` | simulent une mesure toutes les 30–60 s et la publient |
| `Controleur.py` | lit les capteurs, applique les règles, envoie les commandes |
| `ventilation.py`, `irrigation.py` | reçoivent les commandes et affichent l'action |
| `common.py` | partie sécurité et connexion : `seal` / `unseal` (token, AES, anti-replay), `connect`, `alert`, `pause` |
| `monitor.py` | monitoring : écrit les alertes dans `alerts.log` |
| `gen_keys.py` | génère la clé AES, les tokens et les comptes Mosquitto (`mosquitto_passwd`) |
| `conf/mosquitto_plain.conf` | broker ouvert (Jour 1) |
| `conf/mosquitto_secure.conf` + `conf/aclfile` | broker sans accès anonyme, avec utilisateurs et ACL (Jour 3) |
| `run_all.sh` | lance le broker et tous les scripts (`plain` ou `secure`) |

Fichiers générés, à ne **jamais** partager : `aes.key`, `tokens.json`, `broker_users.json`, `passwd`.

## Installation et lancement (WSL / Ubuntu)

```bash
sudo apt update && sudo apt install -y mosquitto mosquitto-clients python3-venv tcpdump
sudo systemctl stop mosquitto && sudo systemctl disable mosquitto   # libère le port 1883
git clone https://github.com/bidanessyidrissa45-ops/smart-farm-iot-security.git ~/smartfarm && cd ~/smartfarm && chmod +x run_all.sh

./run_all.sh plain     # Jour 1 : système sans sécurité
./run_all.sh secure    # Jours 2-3 : token + AES + anti-replay + ACL + monitoring
```

Par défaut `run_all.sh` envoie une mesure toutes les 3 s (démo). Pour le rythme du sujet (30–60 s) :
`FARM_INTERVAL= ./run_all.sh plain`. Arrêt : `Ctrl+C`.

Le mode est choisi par la variable `FARM_MODE` (`plain` ou `secure`) : le même code sert avant et après la sécurisation.

## Ce qui a été fait

### Jour 1 — Système fonctionnel, sans sécurité
- Capteurs, contrôleur et actionneurs communiquant en JSON clair `{"value", "timestamp"}`.
- Broker Mosquitto ouvert (`allow_anonymous true`) : aucun contrôle d'accès.

### Jour 2 — Analyse et premières sécurisations
- **Analyse** : capture du trafic avec `tcpdump`, lecture dans Wireshark (`capture_plain.pcap`). Constats :
  messages lisibles (pas de confidentialité), modifiables (pas d'intégrité), publication possible par n'importe qui
  (pas d'authentification), rejeu possible.
- **Authentification par tokens** : un token unique par capteur et pour le contrôleur (`tokens.json`),
  inclus dans chaque message et vérifié à la réception.
- **Chiffrement AES** : clé partagée `aes.key` ; le JSON est chiffré en **AES-GCM** puis encodé en Base64.
  GCM garantit la confidentialité **et** l'intégrité (tout message modifié est rejeté).
  Capture après sécurisation : `capture_secure.pcap` (contenu illisible).

### Jour 3 — Sécurisation progressive
- **Anti-replay** : chaque message porte un timestamp et un compteur croissant ; `unseal` rejette les messages
  trop anciens (> 120 s) ou dont le compteur n'est pas supérieur au précédent.
- **ACL Mosquitto** : connexions anonymes désactivées, un utilisateur par appareil (`mosquitto_passwd`),
  droits minimaux dans `conf/aclfile` : capteurs → publier sur leur topic ; actionneurs → lire leur commande ;
  contrôleur → lire les capteurs et publier les commandes.
- **Monitoring** : `monitor.py` détecte `NON_CHIFFRE`, `TOKEN_INVALIDE`, `REPLAY` et `FLUX_ANORMAL`
  (plus de 8 messages en 10 s sur un topic) et écrit dans `alerts.log`.

## Tests réalisés (mode secure)

| Test | Résultat |
|---|---|
| Observateur sur le broker | contenu en Base64 chiffré, illisible |
| Connexion anonyme | refusée : `Connection Refused: not authorised` |
| `ventilation` publie sur le topic d'irrigation | bloqué par l'ACL |
| Rejeu d'un vrai message capturé | rejeté, alerte `REPLAY` dans `alerts.log` |
| Injection en clair avec identifiants valides | rejetée, alerte `NON_CHIFFRE` |

## Répartition des rôles

| | **Idrissa Bidanessy** — infrastructure et système | **Dhruv Patel** — sécurité et analyse |
|---|---|---|
| Jour 1 | Capteurs, contrôleur, actionneurs ; installation WSL et Mosquitto ; `run_all.sh` | Revue du système, scénarios de test |
| Jour 2 | Captures réseau (`tcpdump`, Wireshark) et analyse du système non sécurisé | Tokens (`tokens.json`) et chiffrement AES-GCM/Base64 (`seal` / `unseal`, `gen_keys.py`) |
| Jour 3 | Configuration du broker et ACL (`conf/`, `mosquitto_passwd`) | Anti-replay (compteur + timestamp) et `monitor.py` / `alerts.log` |
| Rapport | Architecture, Jour 1, résultats des captures | Failles et protections (tableau), tests d'attaque, limites |

Les deux membres ont relu le code de l'autre et peuvent présenter l'ensemble du projet.

## Limites et pistes d'amélioration

- La clé AES est partagée par tous les appareils : si l'un est compromis, tous le sont. Améliorations : clé par appareil, rotation des clés.
- Le broker écoute en 1883 sans TLS : le chiffrement est fait au niveau applicatif. Amélioration : TLS sur le port 8883.
- Les secrets sont stockés dans des fichiers locaux ; en production : coffre de secrets.
- Bonus non réalisé : dashboard web de visualisation (Streamlit ou Flask).
