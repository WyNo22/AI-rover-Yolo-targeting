/*
 * turret_click.ino
 * Tourelle pan-tilt pilotée par erreurs pixel depuis tracker_click.py
 *
 * Protocole série reçu (115200 baud) :
 *   "<error_x> <error_y>\n"
 *   - error_x : décalage horizontal en pixels (+ = cible à droite du centre)
 *   - error_y : décalage vertical   en pixels (+ = cible en bas du centre)
 *   Exemple : "45 -30\n"
 *
 * Commande reset : "R\n" -> retour position repos
 *
 * Câblage :
 *   Servo PAN  signal -> Pin 9
 *   Servo TILT signal -> Pin 10
 *
 * ─── IMPORTANT : choisir votre type de servo PAN ────────────────────────────
 *   PAN_STANDARD_180 = 0  →  Servo à rotation CONTINUE (ex. MG996R modifié)
 *                            Compatible avec turret_control.ino existant
 *   PAN_STANDARD_180 = 1  →  Servo 180° standard (ex. SG90, MG995)
 * ────────────────────────────────────────────────────────────────────────────
 */

#include <Servo.h>

// ── Pins ──────────────────────────────────────────────────────────────────────
#define PIN_PAN   9
#define PIN_TILT  10

// ── Type servo PAN : 0 = continu, 1 = 180° standard ─────────────────────────
#define PAN_STANDARD_180  0

// ── Paramètres PAN – rotation continue ───────────────────────────────────────
#define PAN_STOP_US      1500     // impulsion µs à l'arrêt
#define PAN_RANGE_US      400     // ±400 µs pour ±100% vitesse
#define PAN_KP              0.15f // gain : pixels → % vitesse
#define PAN_DEAD_PX        30     // dead zone horizontale (pixels)
#define PAN_MAX_SPD       100     // vitesse max (0-100)

// ── Paramètres PAN – 180° standard ───────────────────────────────────────────
#define PAN180_CENTER      90
#define PAN180_MIN          5
#define PAN180_MAX        175
#define PAN180_KP           0.05f // gain : pixels → degrés par commande
#define PAN180_MAX_STEP     8     // correction max par commande (degrés)

// ── Paramètres TILT (servo 180°) ─────────────────────────────────────────────
#define TILT_CENTER        90
#define TILT_MIN           10
#define TILT_MAX          170
#define TILT_KP             0.06f // gain : pixels → degrés par commande
#define TILT_DEAD_PX       25     // dead zone verticale (pixels)
#define TILT_MAX_STEP       8     // correction max par commande (degrés)

// ── Watchdog ──────────────────────────────────────────────────────────────────
#define WATCHDOG_MS         500   // ms sans commande → stop pan
#define TILT_WATCHDOG_MS    300   // ms sans commande → retour centre tilt
#define TILT_PARK_DELAY     600   // ms après centrage avant détachement servo

// ─────────────────────────────────────────────────────────────────────────────
Servo panServo;
Servo tiltServo;

int   currentTilt    = TILT_CENTER;
float pan180Angle    = PAN180_CENTER;
unsigned long lastCmdMs  = 0;
unsigned long lastLoopMs = 0;
unsigned long tiltParkMs = 0;
bool          tiltParked = false;


// ── Fonctions servo ───────────────────────────────────────────────────────────

void stopPan() {
#if PAN_STANDARD_180
    panServo.write((int)pan180Angle);   // maintenir angle courant
#else
    panServo.writeMicroseconds(PAN_STOP_US);
#endif
}

void applyPanContinuous(int errorX) {
    if (abs(errorX) <= PAN_DEAD_PX) {
        panServo.writeMicroseconds(PAN_STOP_US);
        return;
    }
    int speed = (int)(errorX * PAN_KP);
    speed = constrain(speed, -PAN_MAX_SPD, PAN_MAX_SPD);
    int us = PAN_STOP_US + (int)(speed * PAN_RANGE_US / 100.0f);
    panServo.writeMicroseconds(us);
}

void applyPan180(int errorX) {
    if (abs(errorX) <= PAN_DEAD_PX) return;
    float step = errorX * PAN180_KP;
    step = constrain(step, (float)-PAN180_MAX_STEP, (float)PAN180_MAX_STEP);
    pan180Angle += step;
    pan180Angle  = constrain(pan180Angle, (float)PAN180_MIN, (float)PAN180_MAX);
    panServo.write((int)pan180Angle);
}

void applyTilt(int errorY) {
    if (abs(errorY) <= TILT_DEAD_PX) return;
    // Inversion signe : errorY>0 = cible en bas → servo descend (angle diminue)
    float step = -errorY * TILT_KP;
    step = constrain(step, (float)-TILT_MAX_STEP, (float)TILT_MAX_STEP);
    float target = constrain((float)currentTilt + step, (float)TILT_MIN, (float)TILT_MAX);
    // EMA pour amortir les oscillations
    currentTilt = (int)(0.55f * target + 0.45f * currentTilt);
    tiltServo.write(currentTilt);
}

void resetPosition() {
    stopPan();
    currentTilt = TILT_CENTER;
    pan180Angle = PAN180_CENTER;
    tiltServo.write(TILT_CENTER);
    Serial.println("RESET");
}


// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);

    panServo.attach(PIN_PAN,   600, 2400);
    tiltServo.attach(PIN_TILT, 600, 2400);

    stopPan();
    tiltServo.write(TILT_CENTER);

    lastCmdMs  = millis();
    lastLoopMs = millis();
    Serial.println("READY");
}


// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    unsigned long now = millis();

    float dt = (now - lastLoopMs) / 1000.0f;
    lastLoopMs = now;

    // Watchdog pan
    if (now - lastCmdMs > WATCHDOG_MS) {
        stopPan();
    }

    // Watchdog tilt : centre puis détache (comme turret_control)
    if (now - lastCmdMs > TILT_WATCHDOG_MS) {
        if (!tiltParked) {
            currentTilt = TILT_CENTER;
            tiltServo.write(TILT_CENTER);
            tiltParkMs  = now;
            tiltParked  = true;
        } else if (tiltServo.attached() && (now - tiltParkMs > TILT_PARK_DELAY)) {
            tiltServo.detach();
        }
    }

    // Lecture série
    if (!Serial.available()) return;

    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    // Commande reset
    if (line.equalsIgnoreCase("R")) {
        resetPosition();
        lastCmdMs = now;
        return;
    }

    // Parseur : "<error_x> <error_y>"
    int spaceIdx = line.indexOf(' ');
    if (spaceIdx < 0) return;

    int errorX = line.substring(0, spaceIdx).toInt();
    int errorY = line.substring(spaceIdx + 1).toInt();

    // Re-attacher le servo tilt si détaché par le watchdog
    if (!tiltServo.attached()) {
        tiltServo.attach(PIN_TILT, 600, 2400);
    }
    tiltParked = false;

    // Application des corrections
#if PAN_STANDARD_180
    applyPan180(errorX);
#else
    applyPanContinuous(errorX);
#endif
    applyTilt(errorY);

    lastCmdMs  = now;
}
