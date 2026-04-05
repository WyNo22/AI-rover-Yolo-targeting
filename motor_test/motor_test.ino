/*
 * motor_test.ino
 * Test déplacement base roulante 4WD – Adafruit Motor Shield v2
 * Câblage validé : M1=avant-gauche  M2=avant-droit
 *                  M3=arrière-droit M4=arrière-gauche
 *
 * Commandes Serial Monitor (115200 baud) :
 *   f → avancer
 *   b → reculer
 *   l → tourner gauche (pivot sur place)
 *   r → tourner droite (pivot sur place)
 *   s → stop
 *   h → aide
 *
 * Au démarrage : séquence auto avant → recul → gauche → droite → stop
 */

#include <Wire.h>
#include <Adafruit_MotorShield.h>

#define SPEED       180   // vitesse 0–255
#define TURN_SPEED  160   // vitesse en pivot
#define SEQ_MS     1500   // durée de chaque mouvement séquence auto (ms)

Adafruit_MotorShield AFMS = Adafruit_MotorShield();
Adafruit_DCMotor *mFL = nullptr;   // M1 avant-gauche
Adafruit_DCMotor *mFR = nullptr;   // M2 avant-droit
Adafruit_DCMotor *mBR = nullptr;   // M3 arrière-droit
Adafruit_DCMotor *mBL = nullptr;   // M4 arrière-gauche


// ── Helpers ───────────────────────────────────────────────────────────────────

void stopAll() {
    mFL->run(RELEASE); mFR->run(RELEASE);
    mBR->run(RELEASE); mBL->run(RELEASE);
}

void setLeft(int spd) {
    mFL->setSpeed(abs(spd)); mBL->setSpeed(abs(spd));
    mFL->run(spd >= 0 ? FORWARD : BACKWARD);
    mBL->run(spd >= 0 ? FORWARD : BACKWARD);
}

void setRight(int spd) {
    mFR->setSpeed(abs(spd)); mBR->setSpeed(abs(spd));
    mFR->run(spd >= 0 ? FORWARD : BACKWARD);
    mBR->run(spd >= 0 ? FORWARD : BACKWARD);
}

void forward()   { setLeft( SPEED);      setRight( SPEED);      Serial.println(">> AVANT");  }
void backward()  { setLeft(-SPEED);      setRight(-SPEED);      Serial.println(">> RECUL");  }
void turnLeft()  { setLeft(-TURN_SPEED); setRight( TURN_SPEED); Serial.println(">> GAUCHE"); }
void turnRight() { setLeft( TURN_SPEED); setRight(-TURN_SPEED); Serial.println(">> DROITE"); }
void stop()      { stopAll();                                    Serial.println(">> STOP");   }

void printHelp() {
    Serial.println("");
    Serial.println("=== Test deplacement ===");
    Serial.println("  f = avant   b = recul");
    Serial.println("  l = gauche  r = droite  s = stop");
    Serial.println("");
}


// ── Setup ─────────────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    AFMS.begin();
    mFL = AFMS.getMotor(1);
    mFR = AFMS.getMotor(2);
    mBR = AFMS.getMotor(3);
    mBL = AFMS.getMotor(4);
    stopAll();

    Serial.println("=== Motor Test – deplacement ===");
    Serial.println("Sequence auto dans 1s...");
    delay(1000);

    forward();  delay(SEQ_MS); stop(); delay(400);
    backward(); delay(SEQ_MS); stop(); delay(400);
    turnLeft(); delay(SEQ_MS); stop(); delay(400);
    turnRight();delay(SEQ_MS); stop(); delay(400);

    Serial.println("--- Fin sequence ---");
    printHelp();
}


// ── Loop ──────────────────────────────────────────────────────────────────────

void loop() {
    if (!Serial.available()) return;
    char cmd = (char)Serial.read();
    switch (cmd) {
        case 'f': case 'F': forward();   break;
        case 'b': case 'B': backward();  break;
        case 'l': case 'L': turnLeft();  break;
        case 'r': case 'R': turnRight(); break;
        case 's': case 'S': stop();      break;
        case 'h': case 'H': printHelp(); break;
        default: break;
    }
}
