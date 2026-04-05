/*
 * turret_control.ino
 * Tourelle pan-tilt pilotee par commandes serie depuis le PC (YOLO tracking)
 *
 * Servos :
 *   - MG996R (pan, base 360 continu) -> Pin 9
 *   - MG995  (tilt, 180)             -> Pin 10
 *
 * Protocole serie recu (115200 baud) :
 *   "P<vitesse>T<angle>\n"
 *   - vitesse : -100 a +100  (0 = stop)
 *   - angle   :    0 a  180  (90 = regard horizontal)
 *   Exemple : "P35T60\n"
 *
 * Commande reset pan : "R\n"  -> remet panAngle a 0 (position de reference)
 *
 * Alimentation : LiPo 2S -> Arduino VIN + Servo VCC (masse commune)
 */

#include <Servo.h>

// Pins
#define PIN_PAN   9
#define PIN_TILT  10

// Parametres pan (MG996R continu)
// 1500 us = stop ; < 1500 = sens horaire ; > 1500 = anti-horaire
#define PAN_STOP_US        1500
#define PAN_RANGE_US        400

// Vitesse angulaire estimee a vitesse 100 (a calibrer si besoin)
// MG996R tourne ~360/s a pleine charge sous 6V
#define PAN_DEG_PER_SEC    180.0f

// Limite angulaire : evite l'emmelement des cables
#define PAN_LIMIT_DEG      170.0f

// Parametres tilt (MG995 180)
#define TILT_CENTER  90
#define TILT_MIN     10
#define TILT_MAX    170

// Watchdog pan : stoppe si aucune commande recue pendant X ms
#define WATCHDOG_MS       500
// Watchdog tilt : va a TILT_CENTER puis detach apres que le servo ait atteint la position
#define TILT_WATCHDOG_MS      0   // ms sans commande avant de parker
#define TILT_PARK_DELAY        0   // ms avant detach (immediat)

Servo panServo;
Servo tiltServo;

int   currentTilt      = TILT_CENTER;
int   currentPanSpd    = 0;
float panAngle         = 0.0f;
unsigned long lastCmdMs  = 0;
unsigned long lastLoopMs = 0;
unsigned long tiltParkMs = 0;
bool          tiltParked = false;

void applyPan(int speed) {
  speed = constrain(speed, -100, 100);
  bool blocked = false;

  if (speed > 0 && panAngle >=  PAN_LIMIT_DEG) { speed = 0; blocked = true; }
  if (speed < 0 && panAngle <= -PAN_LIMIT_DEG) { speed = 0; blocked = true; }

  currentPanSpd = speed;
  int us = PAN_STOP_US + (int)(speed * PAN_RANGE_US / 100.0);
  panServo.writeMicroseconds(us);

  if (blocked) {
    Serial.println("PAN_LIMIT");
  }
}

void applyTilt(int angle) {
  currentTilt = constrain(angle, TILT_MIN, TILT_MAX);
  tiltServo.write(currentTilt);
}

void setup() {
  Serial.begin(115200);

  panServo.attach(PIN_PAN,  600, 2400);
  tiltServo.attach(PIN_TILT, 600, 2400);

  panServo.writeMicroseconds(PAN_STOP_US);
  tiltServo.write(TILT_CENTER);

  lastCmdMs  = millis();  // evite le watchdog tilt au boot
  lastLoopMs = millis();
  Serial.println("READY");
}

void loop() {
  unsigned long now = millis();
  float dt = (now - lastLoopMs) / 1000.0f;
  lastLoopMs = now;

  // Integration de l'angle pan estime
  if (currentPanSpd != 0) {
    panAngle += currentPanSpd * (PAN_DEG_PER_SEC / 100.0f) * dt;
    panAngle = constrain(panAngle, -PAN_LIMIT_DEG, PAN_LIMIT_DEG);

    if (panAngle >= PAN_LIMIT_DEG || panAngle <= -PAN_LIMIT_DEG) {
      currentPanSpd = 0;
      panServo.writeMicroseconds(PAN_STOP_US);
      Serial.println("PAN_LIMIT");
    }
  }

  // Watchdog pan
  if (now - lastCmdMs > WATCHDOG_MS) {
    currentPanSpd = 0;
    panServo.writeMicroseconds(PAN_STOP_US);
  }

  // Watchdog tilt : va a 90 deg (droit), attend 800ms, puis detach
  if (now - lastCmdMs > TILT_WATCHDOG_MS) {
    if (!tiltParked) {
      applyTilt(TILT_CENTER);
      tiltParkMs = now;
      tiltParked = true;
    } else if (tiltServo.attached() && (now - tiltParkMs > TILT_PARK_DELAY)) {
      tiltServo.detach();
    }
  }

  // Lecture serie
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line.length() == 0) return;

    // Reset angle pan
    if (line == "R") {
      panAngle = 0.0f;
      Serial.println("PAN_RESET");
      return;
    }

    // Parseur : "P<speed>T<angle>"
    int pIdx = line.indexOf('P');
    int tIdx = line.indexOf('T');

    if (pIdx == -1 || tIdx == -1 || tIdx <= pIdx) return;

    int panSpeed  = line.substring(pIdx + 1, tIdx).toInt();
    int tiltAngle = line.substring(tIdx + 1).toInt();

    // Re-attacher le servo tilt si il avait ete detache
    if (!tiltServo.attached()) {
      tiltServo.attach(PIN_TILT, 600, 2400);
    }
    tiltParked = false;

    applyPan(panSpeed);
    applyTilt(tiltAngle);
    lastCmdMs = now;
  }
}
