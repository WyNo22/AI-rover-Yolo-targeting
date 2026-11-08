# Étape 7 – radio FS-iA6B en iBUS et arrêt d'urgence.
# Récepteur : prise iBUS (servo) → signal sur GP1, + sur VBUS (5 V), − sur GND.
# Sur l'émetteur, règle le failsafe de CH5 sur la position ARRÊT (menu Failsafe) : si la radio est coupée,
# le récepteur enverra « arrêt ». S'il cesse d'envoyer des trames, le Pico coupe aussi au bout de 100 ms.
#
# Avec ARRET_URGENCE = True :
#   - ARRÊT (CH5 en position arrêt, ou plus de radio) → couple coupé sur les 8 servos (diffusion, répétée) ;
#   - ARMÉ → avec TENIR_QUAND_ARME, chaque servo se raidit sur sa position ACTUELLE (aucun mouvement).
# Test : servos branchés, bascule CH5 → ils deviennent mous ; éteins l'émetteur → mous en moins de 0,1 s.
import time

from machine import Pin

import brochage as B
from ibus import IBus
from sts import Bus, ErreurBus, CONSIGNE

ARRET_URGENCE = True
TENIR_QUAND_ARME = True


def en_arret(radio):
    age = radio.age_ms()
    if age is None or age > B.PERTE_RADIO_MS:
        return True, "plus de radio"
    v = radio.voie(B.VOIE_ARRET)
    haut = v > 1500
    if haut == B.ARRET_SI_HAUT:
        return True, "CH%d = %d" % (B.VOIE_ARRET, v)
    return False, ""


def tenir_position(bus):
    for i in B.IDS:
        try:
            p = bus.position(i)
            bus.ecrire(i, CONSIGNE, (p & 0xFF, p >> 8, 0, 0, 0, 0))   # consigne = position actuelle
            bus.couple(i, True)
        except ErreurBus:
            pass


def main(tours=None):
    radio = IBus(B.uart_radio())
    bus = Bus(B.uart_servos()) if ARRET_URGENCE else None
    led = Pin("LED", Pin.OUT)
    arrete = True
    if bus:
        bus.couple_tous_off()
    t_diff = time.ticks_ms()
    t_aff = time.ticks_ms()
    print("Bouge les manches et les interrupteurs. Ctrl+C pour arrêter.")
    n = 0
    while tours is None or n < tours:
        n += 1
        radio.lire()
        stop, raison = en_arret(radio)
        if bus:
            if stop and (not arrete or time.ticks_diff(time.ticks_ms(), t_diff) > 200):
                bus.couple_tous_off()                       # répété toutes les 200 ms tant que l'arrêt dure
                t_diff = time.ticks_ms()
            elif not stop and arrete and TENIR_QUAND_ARME:
                tenir_position(bus)
        if stop != arrete:
            print("\n%s %s" % ("■ ARRÊT" if stop else "▶ ARMÉ", raison))
        arrete = stop
        led.value(0 if stop else 1)
        if time.ticks_diff(time.ticks_ms(), t_aff) > 100:
            t_aff = time.ticks_ms()
            v = radio.voies
            age = radio.age_ms()
            print("CH1 %4d CH2 %4d CH3 %4d CH4 %4d CH5 %4d CH6 %4d | trames %d, erreurs %d, dernière il y a %s ms  "
                  % (v[0], v[1], v[2], v[3], v[4], v[5], radio.trames, radio.erreurs, "—" if age is None else age),
                  end="\r")
        time.sleep_ms(2)
    if bus:
        bus.couple_tous_off()
    return arrete


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêté.")
