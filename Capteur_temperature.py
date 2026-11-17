"""
Capteur de temperature (simule).               JOUR 1 : capteur, publie en clair
                                               JOURS 2-3 : le meme code, mais seal() ajoute token + AES
"""
import random

from common import T_TEMP, connect, pause, seal

# Connexion au broker sous le nom "temp_sensor" (c'est aussi son compte et son token)
client = connect("temp_sensor")
client.loop_start()  # gere la communication MQTT en arriere-plan

valeur = 26.0
while True:
    # Simulation : la temperature varie un peu a chaque mesure, entre 15 et 40 degres
    valeur = round(min(40, max(15, valeur + random.uniform(-2.5, 2.5))), 1)

    # Publication sur /farm/temperature. seal() decide : clair (Jour 1) ou chiffre (Jours 2-3)
    client.publish(T_TEMP, seal("temp_sensor", {"value": valeur}))
    print("temperature :", valeur, flush=True)

    pause()  # attente de 30 a 60 s avant la prochaine mesure
