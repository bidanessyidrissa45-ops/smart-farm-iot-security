"""
JOURS 2 et 3 : genere tous les secrets du mode secure.
  aes.key           JOUR 2 : cle AES partagee (chiffrement)
  tokens.json       JOUR 2 : un token par capteur et pour le controleur (authentification)
  broker_users.json JOUR 3 : mots de passe des comptes Mosquitto
  passwd            JOUR 3 : fichier de mots de passe lu par Mosquitto (cree avec mosquitto_passwd)
Lance automatiquement par run_all.sh au premier demarrage en mode secure.
"""
import base64
import json
import secrets
import subprocess
from pathlib import Path

DIR = Path(__file__).parent
APPAREILS = ["temp_sensor", "hum_sensor", "controller", "ventilation", "irrigation", "monitor"]

# JOUR 2 : cle AES de 256 bits, tiree au hasard
(DIR / "aes.key").write_text(base64.b64encode(secrets.token_bytes(32)).decode())

# JOUR 2 : un token aleatoire pour les 3 emetteurs de messages (2 capteurs + controleur)
(DIR / "tokens.json").write_text(json.dumps({u: secrets.token_urlsafe(24) for u in APPAREILS[:3]}))

# JOUR 3 : un mot de passe aleatoire par appareil pour se connecter au broker
users = {u: secrets.token_urlsafe(12) for u in APPAREILS}
(DIR / "broker_users.json").write_text(json.dumps(users))

# JOUR 3 : creation du fichier "passwd" de Mosquitto avec mosquitto_passwd
# (-c = creer le fichier pour le premier utilisateur, puis on ajoute les autres)
(DIR / "passwd").unlink(missing_ok=True)
for i, (u, p) in enumerate(users.items()):
    subprocess.run(["mosquitto_passwd", "-b"] + (["-c"] if i == 0 else []) + [str(DIR / "passwd"), u, p], check=True)
print("Cles generees")
