"""
JOUR 3 : monitoring. Ecoute tout /farm/# et ecrit les alertes dans alerts.log.
Detecte : messages non chiffres, tokens invalides, replays (via unseal) et flux anormaux.
Fonctionne uniquement en mode secure.
"""
import time

from common import SECURE, T_HUM, T_IRRI, T_TEMP, T_VENT, alert, connect, unseal

# Pour chaque topic : qui est cense l'avoir envoye
SENDER = {T_TEMP: "temp_sensor", T_HUM: "hum_sensor", T_VENT: "controller", T_IRRI: "controller"}

recus = {}  # heures d'arrivee des derniers messages, par topic


def on_message(topic, raw):
    # --- Detection de flux anormal : trop de messages en peu de temps (attaque / saturation) ---
    maintenant = time.time()
    recus[topic] = [t for t in recus.get(topic, []) if maintenant - t < 10] + [maintenant]
    if len(recus[topic]) > 8:  # plus de 8 messages en 10 s
        alert("FLUX_ANORMAL", f"{len(recus[topic])} messages en 10 s sur {topic}")

    # --- Detection des messages non chiffres, tokens invalides et replays ---
    # unseal() ecrit lui-meme l'alerte NON_CHIFFRE / TOKEN_INVALIDE / REPLAY
    if topic in SENDER:
        unseal(raw, SENDER[topic])


if not SECURE:
    raise SystemExit("Lance le monitor avec FARM_MODE=secure")

# Compte "monitor" : droit de lecture seule sur /farm/# (defini dans conf/aclfile)
connect("monitor", ["/farm/#"], on_message).loop_forever()
