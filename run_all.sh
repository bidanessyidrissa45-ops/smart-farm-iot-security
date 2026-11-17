#!/usr/bin/env bash
# Lance toute la simulation.   Usage : ./run_all.sh plain|secure      (Ctrl+C arrete tout)
#   plain  = JOUR 1 (sans securite)
#   secure = JOURS 2 et 3 (token + AES + anti-replay + ACL + monitoring)
cd "$(dirname "$0")"
MODE=${1:-plain}
# FARM_INTERVAL=3 : une mesure toutes les 3 s pour la demo. Lance "FARM_INTERVAL= ./run_all.sh plain" pour 30-60 s.
export FARM_MODE=$MODE FARM_INTERVAL=${FARM_INTERVAL-3}

# Premiere fois : environnement Python avec les bibliotheques MQTT et AES
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q paho-mqtt cryptography; }
PY=.venv/bin/python
mkdir -p logs; : > alerts.log

# JOURS 2-3 : generation des cles, tokens et comptes broker au premier lancement
[ "$MODE" = secure ] && { [ -f passwd ] || $PY gen_keys.py; }

# Demarrage du broker Mosquitto (config plain = Jour 1, config secure = Jour 3)
chmod 600 conf/aclfile passwd 2>/dev/null
mosquitto -c conf/mosquitto_$MODE.conf > logs/mosquitto.log 2>&1 &
sleep 1
if grep -q "already in use" logs/mosquitto.log; then
  echo "Port 1883 deja utilise (service mosquitto d'apt). Fais : sudo systemctl stop mosquitto"; exit 1
fi

# JOUR 1 : controleur, actionneurs et capteurs
for s in Controleur ventilation irrigation Capteur_temperature Capteur_humidity; do
  $PY $s.py > logs/$s.log 2>&1 &
done
# JOUR 3 : monitoring (mode secure seulement)
[ "$MODE" = secure ] && $PY monitor.py > logs/monitor.log 2>&1 &

trap 'kill $(jobs -p) 2>/dev/null' EXIT
echo "Mode $MODE lance. Ctrl+C pour arreter."
tail -f logs/Controleur.log logs/ventilation.log logs/irrigation.log
