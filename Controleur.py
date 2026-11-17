"""
Controleur : le "cerveau" de la serre.
  JOUR 1 : lit les capteurs, applique les regles metier, envoie les commandes
  JOURS 2-3 : unseal() verifie chaque mesure (token, AES, anti-replay) avant de s'en servir
"""
from common import T_HUM, T_IRRI, T_TEMP, T_VENT, connect, seal, unseal

# JOUR 2 : pour chaque topic, le SEUL emetteur autorise (un autre serait rejete)
SENDER = {T_TEMP: "temp_sensor", T_HUM: "hum_sensor"}

etat = {}  # derniere commande envoyee a chaque actionneur


# --- JOUR 1 : envoi d'une commande ON/OFF a un actionneur -------------------
def commander(topic, actif):
    if etat.get(topic) != actif:  # on n'envoie que quand l'etat change
        etat[topic] = actif
        client.publish(topic, seal("controller", {"command": "ON" if actif else "OFF"}))
        print(topic, "->", "ON" if actif else "OFF", flush=True)


# --- Appelee a chaque mesure recue d'un capteur ------------------------------
def on_message(topic, raw):
    # JOURS 2-3 : verification de securite. None = message refuse, alerte deja ecrite
    msg = unseal(raw, SENDER[topic])
    if msg is None:
        return

    print(topic, "=", msg["value"], flush=True)

    # JOUR 1 : regles metier
    if topic == T_TEMP:
        commander(T_VENT, msg["value"] > 30)   # temperature > 30 C  -> ventilation
    else:
        commander(T_IRRI, msg["value"] < 40)   # humidite < 40 %     -> irrigation


# Le controleur ecoute les deux capteurs et tourne sans fin
client = connect("controller", [T_TEMP, T_HUM], on_message)
client.loop_forever()
