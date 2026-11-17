"""
Actionneur irrigation (simule).                JOUR 1 : execute les ordres du controleur (affichage console)
                                               JOURS 2-3 : n'obeit qu'a des ordres authentifies et non rejoues
"""
from common import T_IRRI, connect, unseal


def on_message(topic, raw):
    # JOURS 2-3 : seul le "controller" a le droit de commander. Sinon ordre ignore + alerte.
    msg = unseal(raw, "controller")
    if msg:
        # JOUR 1 : action simulee par un affichage
        print(">>> IRRIGATION", "ACTIVEE" if msg["command"] == "ON" else "ARRETEE", flush=True)


# Abonne uniquement a son propre topic de commande (l'ACL du Jour 3 l'impose aussi)
connect("irrigation", [T_IRRI], on_message).loop_forever()
