"""
common.py : fonctions partagees par tous les scripts.

Le mode est choisi avec la variable FARM_MODE :
  - plain  = JOUR 1 : messages en clair, aucune securite
  - secure = JOURS 2 et 3 : token + chiffrement AES + anti-replay + broker avec utilisateurs
"""
import base64
import hmac
import json
import os
import random
import time
from pathlib import Path

import paho.mqtt.client as mqtt

DIR = Path(__file__).parent
SECURE = os.getenv("FARM_MODE", "plain") == "secure"


# =============================================================================
# JOUR 1 : les noms des "canaux" MQTT (topics) utilises dans toute la serre
# =============================================================================
T_TEMP = "/farm/temperature"             # capteur temperature -> controleur
T_HUM = "/farm/humidity"                 # capteur humidite    -> controleur
T_VENT = "/farm/commands/ventilation"    # controleur -> ventilation
T_IRRI = "/farm/commands/irrigation"     # controleur -> irrigation


# =============================================================================
# JOURS 2 et 3 : chargement des secrets (generes par gen_keys.py)
# =============================================================================
if SECURE:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    AES = AESGCM(base64.b64decode((DIR / "aes.key").read_text()))   # JOUR 2 : cle AES partagee
    TOKENS = json.loads((DIR / "tokens.json").read_text())           # JOUR 2 : un token par appareil
    PASSWORDS = json.loads((DIR / "broker_users.json").read_text())  # JOUR 3 : mot de passe du broker


# =============================================================================
# JOUR 1 : rythme des capteurs (une mesure toutes les 30 a 60 secondes)
# =============================================================================
def pause():
    # FARM_INTERVAL=3 force une pause fixe de 3 s (pratique pour la demo)
    time.sleep(float(os.getenv("FARM_INTERVAL", 0)) or random.uniform(30, 60))


# =============================================================================
# JOUR 3 : monitoring - on affiche l'alerte et on l'ecrit dans alerts.log
# =============================================================================
def alert(kind, detail):
    line = f"{time.strftime('%H:%M:%S')} [ALERTE {kind}] {detail}"
    print(line, flush=True)
    with open(DIR / "alerts.log", "a") as f:
        f.write(line + "\n")


# =============================================================================
# EMISSION d'un message
#   JOUR 1 : simple JSON en clair
#   JOUR 2 : on ajoute le token (authentification) puis on chiffre en AES + Base64
#   JOUR 3 : on ajoute un compteur croissant (anti-replay)
# =============================================================================
def seal(sender, data):
    msg = {**data, "timestamp": time.time()}
    if not SECURE:
        return json.dumps(msg)                      # JOUR 1 : tout en clair

    msg["sender"] = sender                          # JOUR 2 : qui envoie
    msg["token"] = TOKENS[sender]                   # JOUR 2 : preuve d'identite
    msg["counter"] = time.time_ns()                 # JOUR 3 : compteur toujours croissant
    iv = os.urandom(12)                             # JOUR 2 : valeur aleatoire unique pour AES
    chiffre = AES.encrypt(iv, json.dumps(msg).encode(), None)   # JOUR 2 : chiffrement AES-GCM
    return base64.b64encode(iv + chiffre).decode()              # JOUR 2 : Base64 pour le transport


# =============================================================================
# RECEPTION d'un message : on verifie tout, sinon on l'ignore avec une alerte
#   JOUR 1 : on lit simplement le JSON, sans aucune verification
#   JOUR 2 : dechiffrement (confidentialite + integrite) puis verification du token
#   JOUR 3 : verification anti-replay
# =============================================================================
last_counter = {}  # JOUR 3 : dernier compteur recu pour chaque emetteur


def unseal(raw, sender):
    if not SECURE:
        return json.loads(raw)                      # JOUR 1 : aucune verification

    # JOUR 2 - etape 1 : dechiffrement. Echoue si le message est en clair, modifie
    # ou chiffre avec une autre cle (AES-GCM detecte toute modification).
    try:
        data = base64.b64decode(raw)
        msg = json.loads(AES.decrypt(data[:12], data[12:], None))
    except Exception:
        alert("NON_CHIFFRE", f"message illisible : {raw[:40]}")
        return None

    # JOUR 2 - etape 2 : authentification. Le bon emetteur avec le bon token ?
    if msg["sender"] != sender or not hmac.compare_digest(msg["token"], TOKENS[sender]):
        alert("TOKEN_INVALIDE", f"emetteur {msg['sender']} (attendu {sender})")
        return None

    # JOUR 3 - etape 3 : anti-replay. Message trop vieux, ou deja vu (compteur pas plus grand) ?
    if time.time() - msg["timestamp"] > 120 or msg["counter"] <= last_counter.get(sender, 0):
        alert("REPLAY", f"message rejoue de {sender}")
        return None

    last_counter[sender] = msg["counter"]           # on memorise pour rejeter les rejeux
    return msg


# =============================================================================
# CONNEXION au broker Mosquitto
#   JOUR 1 : connexion anonyme
#   JOUR 3 : en mode secure, identifiant + mot de passe obligatoires (verifies par l'ACL)
# =============================================================================
def connect(name, topics=(), on_message=None):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=name)
    if SECURE:
        client.username_pw_set(name, PASSWORDS[name])   # JOUR 3 : sinon le broker refuse

    def on_connect(c, userdata, flags, rc, props):
        print(f"[{name}] connexion : {rc}", flush=True)
        for t in topics:
            c.subscribe(t)                              # on s'abonne aux topics demandes

    client.on_connect = on_connect
    if on_message:
        client.on_message = lambda c, u, m: on_message(m.topic, m.payload)
    client.connect("localhost", 1883)                   # le broker tourne dans WSL, port 1883
    return client
