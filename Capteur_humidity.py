"""
Capteur d'humidite (simule).                   JOUR 1 : capteur, publie en clair
                                               JOURS 2-3 : le meme code, mais seal() ajoute token + AES
"""
import random

from common import T_HUM, connect, pause, seal

# Connexion au broker sous le nom "hum_sensor" (c'est aussi son compte et son token)
client = connect("hum_sensor")
client.loop_start()  # gere la communication MQTT en arriere-plan

valeur = 55.0
while True:
    # Simulation : l'humidite varie a chaque mesure, entre 20 et 80 %
    valeur = round(min(80, max(20, valeur + random.uniform(-6, 6))), 1)

    # Publication sur /farm/humidity. seal() decide : clair (Jour 1) ou chiffre (Jours 2-3)
    client.publish(T_HUM, seal("hum_sensor", {"value": valeur}))
    print("humidite :", valeur, flush=True)

    pause()  # attente de 30 a 60 s avant la prochaine mesure
