/*
 * pan_test.ino
 * Test minimal du servo PAN (pin 8), sans Python ni PC.
 * Cycle : gauche 2 s → stop 1 s → droite 2 s → stop 1 s, en boucle.
 * Le Serial Monitor (115200) affiche l'étape en cours.
 *
 * Servo à rotation continue : il tourne dans un sens puis dans l'autre.
 * Servo 180° : il va à une position à gauche puis à droite (marche aussi).
 *
 * Câblage : signal → D8 | + → LiPo/BEC | − → GND commun avec l'Arduino
 */

#include <Servo.h>

#define PIN_PAN   8     // D8 pour le test (n importe quelle broche marche avec la lib Servo)
#define STOP_US   1500   // neutre
#define DELTA_US  250    // écart au neutre (vitesse) : 1250 µs = un sens, 1750 µs = l'autre

Servo panServo;

void step(const char *label, int us, unsigned long ms) {
    Serial.print(label); Serial.print("  ("); Serial.print(us); Serial.println(" us)");
    panServo.writeMicroseconds(us);
    delay(ms);
}

void setup() {
    Serial.begin(115200);
    panServo.attach(PIN_PAN, 600, 2400);
    panServo.writeMicroseconds(STOP_US);
    Serial.println("pan_test pret");
    delay(1000);
}

void loop() {
    step("GAUCHE", STOP_US - DELTA_US, 2000);
    step("STOP",   STOP_US,            1000);
    step("DROITE", STOP_US + DELTA_US, 2000);
    step("STOP",   STOP_US,            1000);
}
