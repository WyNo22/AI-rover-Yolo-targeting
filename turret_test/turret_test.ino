/*
 * turret_test.ino
 * Test manuel de la tourelle via le Serial Monitor de l'Arduino IDE
 * (pas besoin de Python ni du PC pour ce test)
 *
 * Commandes a envoyer dans le Serial Monitor (115200 baud, fin de ligne = NL) :
 *   L         -> pan gauche (vitesse PAN_SPEED)
 *   R         -> pan droite (vitesse PAN_SPEED)
 *   S         -> stop pan
 *   U         -> tilt +5 (haut)
 *   D         -> tilt -5 (bas)
 *   C         -> tilt centre (90)
 *   Z         -> reset angle pan a zero
 *   I         -> infos : angle pan estime + tilt actuel
 *
 * Cablage :
 *   MG996R signal -> Pin 9   (pan, rotation continue)
 *   MG995  signal -> Pin 10  (tilt, 180)
 *   LiPo 2S -> Arduino VIN + Servo VCC (masse commune)
 */

#include <Servo.h>

#define PIN_PAN   9
#define PIN_TILT  10

#define PAN_STOP_US      1500
#define PAN_RANGE_US      400
#define PAN_SPEED          50   // vitesse utilisee par les commandes L/R (0-100)
#define PAN_DEG_PER_SEC  300.0f
#define PAN_LIMIT_DEG    170.0f

#define TILT_CENTER  90
#define TILT_MIN     10
#define TILT_MAX    170
#define TILT_STEP     5

Servo panServo;
Servo tiltServo;

int   currentTilt   = TILT_CENTER;
int   currentPanSpd = 0;
float panAngle      = 0.0f;
unsigned long lastLoopMs = 0;

void applyPan(int speed) {
  speed = constrain(speed, -100, 100);
  if (speed > 0 && panAngle >=  PAN_LIMIT_DEG) { speed = 0; Serial.println(">> LIMITE atteinte (droite)"); }
  if (speed < 0 && panAngle <= -PAN_LIMIT_DEG) { speed = 0; Serial.println(">> LIMITE atteinte (gauche)"); }
  currentPanSpd = speed;
  panServo.writeMicroseconds(PAN_STOP_US + (int)(speed * PAN_RANGE_US / 100.0));
}

void applyTilt(int angle) {
  currentTilt = constrain(angle, TILT_MIN, TILT_MAX);
  tiltServo.write(currentTilt);
  Serial.print(">> Tilt = "); Serial.println(currentTilt);
}

void printHelp() {
  Serial.println("=== TOURELLE TEST ===");
  Serial.println("  L = pan gauche   R = pan droite   S = stop pan");
  Serial.println("  U = tilt haut    D = tilt bas      C = tilt centre");
  Serial.println("  Z = reset angle pan    I = infos");
  Serial.println("====================");
}

void setup() {
  Serial.begin(115200);
  panServo.attach(PIN_PAN,  600, 2400);
  tiltServo.attach(PIN_TILT, 600, 2400);
  panServo.writeMicroseconds(PAN_STOP_US);
  tiltServo.write(TILT_CENTER);
  lastLoopMs = millis();
  printHelp();
  Serial.println("PRET");
}

void loop() {
  unsigned long now = millis();
  float dt = (now - lastLoopMs) / 1000.0f;
  lastLoopMs = now;

  // Integrer angle pan
  if (currentPanSpd != 0) {
    panAngle += currentPanSpd * (PAN_DEG_PER_SEC / 100.0f) * dt;
    panAngle = constrain(panAngle, -PAN_LIMIT_DEG, PAN_LIMIT_DEG);
    if (panAngle >= PAN_LIMIT_DEG || panAngle <= -PAN_LIMIT_DEG) {
      currentPanSpd = 0;
      panServo.writeMicroseconds(PAN_STOP_US);
      Serial.println(">> LIMITE PAN - envoyez Z pour reset");
    }
  }

  // Lecture Serial Monitor
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    line.toUpperCase();

    if (line == "L") {
      applyPan(-PAN_SPEED);
      Serial.print(">> Pan gauche  (angle estime : "); Serial.print(panAngle, 1); Serial.println(" deg)");
    } else if (line == "R") {
      applyPan(PAN_SPEED);
      Serial.print(">> Pan droite  (angle estime : "); Serial.print(panAngle, 1); Serial.println(" deg)");
    } else if (line == "S") {
      applyPan(0);
      Serial.println(">> Pan stop");
    } else if (line == "U") {
      applyTilt(currentTilt + TILT_STEP);
    } else if (line == "D") {
      applyTilt(currentTilt - TILT_STEP);
    } else if (line == "C") {
      applyTilt(TILT_CENTER);
      Serial.println(">> Tilt centre");
    } else if (line == "Z") {
      panAngle = 0.0f;
      Serial.println(">> Angle pan remis a zero");
    } else if (line == "I") {
      Serial.print(">> Angle pan estime : "); Serial.print(panAngle, 1); Serial.println(" deg");
      Serial.print(">> Tilt actuel      : "); Serial.print(currentTilt); Serial.println(" deg");
    } else if (line == "H" || line == "?") {
      printHelp();
    } else if (line.length() > 0) {
      Serial.print(">> Commande inconnue : "); Serial.println(line);
    }
  }
}
