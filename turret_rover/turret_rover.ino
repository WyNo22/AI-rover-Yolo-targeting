/*
 * turret_rover.ino  –  Phase 4 avec PID live tuning
 *
 * Protocole série reçu (115200 baud) :
 *   "<error_x> <error_y>\n"           → tourelle seulement
 *   "<error_x> <error_y> <bbox_h>\n"  → tourelle + navigation
 *   "R\n"                             → reset position + stop
 *
 *   Commandes tuning PID (Serial Monitor) :
 *     pp <val>  → PAN  Kp          tp <val>  → TILT  Kp
 *     pi <val>  → PAN  Ki          ti <val>  → TILT  Ki
 *     pd <val>  → PAN  Kd          td <val>  → TILT  Kd
 *     mp <val>  → MOTOR Kp (dist)  mt <val>  → MOTOR Kp (virage)
 *     mi <val>  → MOTOR Ki         md <val>  → MOTOR Kd
 *     ?                            → affiche tous les PID
 *
 * ── Câblage servos ──────────────────────────────────────────────────────────
 *   Servo PAN  signal → Pin 9    (rotation continue)
 *   Servo TILT signal → Pin 10   (180°)
 *
 * ── Câblage moteurs (Motor Shield v2) ───────────────────────────────────────
 *   M1=avant-gauche  M2=avant-droit  M3=arrière-droit  M4=arrière-gauche
 *
 * ── Alimentation ────────────────────────────────────────────────────────────
 *   Piles AA ×4 série  → Vs shield   (moteurs TT)
 *   LiPo 2S 7.4 V      → VIN Arduino + servos
 */

#include <Servo.h>
#include <Wire.h>
#include <Adafruit_MotorShield.h>

// ── Lecture PWM RC – 100% interruptions (zéro blocage) ────────────────
// CH1(pan)→D2 INT0 | CH2(tilt)→D3 INT1 | CH3(throt)→D6 PCINT22 | CH4(steer)→D7 PCINT23 | CH5(mode)→D8 PCINT0
volatile uint16_t _iPan = 1500, _iTilt = 1500;
volatile uint32_t _tPan = 0,    _tTilt = 0;
volatile uint16_t _iThrot = 1500, _iSteer = 1500;
volatile uint32_t _tThrot = 0,    _tSteer = 0;
volatile uint8_t  _prevD67 = 0;
volatile uint16_t _iMode = 1500;
volatile uint32_t _tMode = 0;
volatile uint8_t  _prevB0 = 0;
uint16_t _throt_neutral = 1500, _steer_neutral = 1500, _tilt_neutral = 1500;
void isrPan()  { if (digitalRead(2)) _tPan  = micros(); else _iPan  = constrain((uint16_t)(micros()-_tPan),  800, 2200); }
void isrTilt() { if (digitalRead(3)) _tTilt = micros(); else _iTilt = constrain((uint16_t)(micros()-_tTilt), 800, 2200); }
ISR(PCINT2_vect) {
    uint8_t pd = PIND; uint32_t now = micros(); uint8_t chg = pd ^ _prevD67; _prevD67 = pd;
    if (chg & 0x40) { if (pd & 0x40) _tThrot=now; else { uint16_t w=(uint16_t)(now-_tThrot); if(w>=800&&w<=2200) _iThrot=w; } }
    if (chg & 0x80) { if (pd & 0x80) _tSteer=now; else { uint16_t w=(uint16_t)(now-_tSteer); if(w>=800&&w<=2200) _iSteer=w; } }
}
ISR(PCINT0_vect) {
    uint8_t pb = PINB; uint32_t now = micros();
    if ((pb ^ _prevB0) & 0x01) { if (pb & 0x01) _tMode=now; else { uint16_t w=(uint16_t)(now-_tMode); if(w>=800&&w<=2200) _iMode=w; } }
    _prevB0 = pb;
}

// ── Pins ──────────────────────────────────────────────────────────────────────
#define PIN_PAN          9
#define PIN_TILT        10
#define PAN_STANDARD_180 0   // 0 = rotation continue, 1 = 180°
#define PIN_RC_PAN       2   // CH1 FS-iA6B → D2 (INT0)   stick gauche ←→
#define PIN_RC_TILT      3   // CH2 FS-iA6B → D3 (INT1)   stick gauche ↑↓
#define PIN_RC_THROT     6   // CH3 FS-iA6B → D6 (PCINT)  stick droit ↑↓
#define PIN_RC_STEER     7   // CH4 FS-iA6B → D7 (PCINT)  stick droit ←→
#define PIN_RC_MODE      8   // CH5 FS-iA6B → D8 (PCINT0) SWA

// ── RC PWM ────────────────────────────────────────────────────────────────────
#define RC_DEAD          50   // zone morte sticks (±µs autour de 1500)

// ── Servo PAN continu ─────────────────────────────────────────────────────────
#define PAN_STOP_US     1500
#define PAN_RANGE_US     400
#define PAN_DEAD_PX       30
#define PAN_MAX_SPD      100

// ── Servo PAN 180° ────────────────────────────────────────────────────────────
#define PAN180_CENTER     90
#define PAN180_MIN         5
#define PAN180_MAX       175
#define PAN180_MAX_STEP    8

// ── Servo TILT ────────────────────────────────────────────────────────────────
#define TILT_CENTER       90
#define TILT_MIN          10
#define TILT_MAX         170
#define TILT_DEAD_PX      25
#define TILT_MAX_STEP      8
#define TILT_RC_STEP       2   // degrés/cycle RC (20ms) à pleine course

// ── Watchdog ──────────────────────────────────────────────────────────────────
#define WATCHDOG_MS        500
#define TILT_WATCHDOG_MS   300
#define TILT_PARK_DELAY    600
#define PYTHON_TIMEOUT_MS  600   // sans données série > 600 ms → fallback RC

// ── Navigation ────────────────────────────────────────────────────────────────
#define DRIVE_DEAD_X       40
#define APPROACH_TARGET   280   // bbox_h bonne distance → stop
#define RETREAT_TARGET    420   // bbox_h trop proche → reculer
#define MOTOR_MAX_SPEED   255

// ═══════════════════════════════════════════════════════════════════════════════
// Struct PID générique avec anti-windup
// ═══════════════════════════════════════════════════════════════════════════════
struct PID {
    float kp, ki, kd;
    float integral;
    float prevError;
    float iLimit;     // anti-windup : clamp de l'intégrale

    PID(float kp, float ki, float kd, float iLimit)
        : kp(kp), ki(ki), kd(kd), integral(0), prevError(0), iLimit(iLimit) {}

    float compute(float error, float dt) {
        if (dt <= 0.0f) dt = 0.001f;
        integral  += error * dt;
        integral   = constrain(integral, -iLimit, iLimit);
        float deriv = (error - prevError) / dt;
        prevError  = error;
        return kp * error + ki * integral + kd * deriv;
    }

    void reset() { integral = 0; prevError = 0; }
};

// ── Instances PID ─────────────────────────────────────────────────────────────
//                       Kp     Ki     Kd    iLimit
PID pidPan  (0.15f, 0.00f, 0.008f, 500.0f);  // PAN  continu (sortie: vitesse %)
PID pidPan180(0.05f, 0.00f, 0.003f, 120.0f);  // PAN  180°   (sortie: step degrés)
PID pidTilt (0.06f, 0.00f, 0.004f, 120.0f);  // TILT 180°   (sortie: step degrés)
PID pidDrive(0.35f, 0.00f, 0.020f, 180.0f);  // DRIVE dist  (sortie: vitesse 0-255)
float motorTurnKp = 0.50f;                     // gain virage différentiel

// ── Objets ────────────────────────────────────────────────────────────────────
Servo panServo;
Servo tiltServo;

int           currentTilt  = TILT_CENTER;
float         pan180Angle  = PAN180_CENTER;
unsigned long lastCmdMs    = 0;
unsigned long lastCtrlMs   = 0;
unsigned long tiltParkMs   = 0;
unsigned long panParkMs    = 0;
bool          tiltParked   = false;

Adafruit_MotorShield AFMS = Adafruit_MotorShield();
Adafruit_DCMotor *motorFL = nullptr;
Adafruit_DCMotor *motorFR = nullptr;
Adafruit_DCMotor *motorBR = nullptr;
Adafruit_DCMotor *motorBL = nullptr;

uint16_t rcSteer=1500, rcThrot=1500, rcTilt=1500, rcPan=1500, rcMode5=1500;
bool     rcMode     = false;
bool     prevRcMode = false;


// ── Helpers moteurs ───────────────────────────────────────────────────────────
void stopMotors() {
    motorFL->run(RELEASE); motorFR->run(RELEASE);
    motorBR->run(RELEASE); motorBL->run(RELEASE);
}

void setMotorLeft(int spd) {
    spd = constrain(spd, -255, 255);
    motorFL->setSpeed((uint8_t)abs(spd)); motorBL->setSpeed((uint8_t)abs(spd));
    motorFL->run(spd >= 0 ? FORWARD : BACKWARD);
    motorBL->run(spd >= 0 ? FORWARD : BACKWARD);
}

void setMotorRight(int spd) {
    spd = constrain(spd, -255, 255);
    motorFR->setSpeed((uint8_t)abs(spd)); motorBR->setSpeed((uint8_t)abs(spd));
    motorFR->run(spd >= 0 ? FORWARD : BACKWARD);
    motorBR->run(spd >= 0 ? FORWARD : BACKWARD);
}


// ── Contrôle PAN ─────────────────────────────────────────────────────────────
void stopPan() {
    if (!panServo.attached()) panServo.attach(PIN_PAN, 600, 2400);
#if PAN_STANDARD_180
    panServo.write((int)pan180Angle);
#else
    panServo.writeMicroseconds(PAN_STOP_US);
#endif
}

void applyPanContinuous(int errorX, float dt) {
    if (!panServo.attached()) panServo.attach(PIN_PAN, 600, 2400);
    if (abs(errorX) <= PAN_DEAD_PX) {
        pidPan.reset();
        panServo.writeMicroseconds(PAN_STOP_US);
        return;
    }
    float spd = pidPan.compute((float)errorX, dt);
    spd = constrain(spd, (float)-PAN_MAX_SPD, (float)PAN_MAX_SPD);
    int us = PAN_STOP_US + (int)(spd * PAN_RANGE_US / 100.0f);
    panServo.writeMicroseconds(us);
}

void applyPan180(int errorX, float dt) {
    if (!panServo.attached()) panServo.attach(PIN_PAN, 600, 2400);
    if (abs(errorX) <= PAN_DEAD_PX) { pidPan180.reset(); return; }
    float step = pidPan180.compute((float)errorX, dt);
    step = constrain(step, (float)-PAN180_MAX_STEP, (float)PAN180_MAX_STEP);
    pan180Angle = constrain(pan180Angle + step, (float)PAN180_MIN, (float)PAN180_MAX);
    panServo.write((int)pan180Angle);
}


// ── Contrôle TILT ────────────────────────────────────────────────────────────
void applyTilt(int errorY, float dt) {
    if (abs(errorY) <= TILT_DEAD_PX) { pidTilt.reset(); return; }
    float step = -pidTilt.compute((float)errorY, dt);
    step = constrain(step, (float)-TILT_MAX_STEP, (float)TILT_MAX_STEP);
    float target = constrain((float)currentTilt + step, (float)TILT_MIN, (float)TILT_MAX);
    currentTilt = (int)(0.55f * target + 0.45f * (float)currentTilt);
    tiltServo.write(currentTilt);
}


// ── Contrôle Drive ───────────────────────────────────────────────────────────
void applyDrive(int errorX, int bboxH, float dt) {
    if (bboxH == 0) { stopMotors(); pidDrive.reset(); return; }

    // Erreur distance : positif = trop loin (avancer), négatif = trop proche (reculer)
    float distError = 0;
    if (bboxH < APPROACH_TARGET)       distError = (float)(APPROACH_TARGET - bboxH);
    else if (bboxH > RETREAT_TARGET)   distError = (float)(RETREAT_TARGET  - bboxH);
    else                               { stopMotors(); pidDrive.reset(); return; }

    float baseSpd = pidDrive.compute(distError, dt);
    baseSpd = constrain(baseSpd, (float)-MOTOR_MAX_SPEED, (float)MOTOR_MAX_SPEED);

    int leftSpd  = (int)baseSpd;
    int rightSpd = (int)baseSpd;

    if (abs(errorX) > DRIVE_DEAD_X) {
        int turn = constrain((int)(errorX * motorTurnKp), -MOTOR_MAX_SPEED, MOTOR_MAX_SPEED);
        leftSpd  = constrain(leftSpd  + turn, -255, 255);
        rightSpd = constrain(rightSpd - turn, -255, 255);
    }

    setMotorLeft(leftSpd);
    setMotorRight(rightSpd);
}


// ── Reset ────────────────────────────────────────────────────────────────────
void resetAll() {
    stopPan(); stopMotors();
    pidPan.reset(); pidPan180.reset(); pidTilt.reset(); pidDrive.reset();
    currentTilt = TILT_CENTER;
    pan180Angle = PAN180_CENTER;
    tiltServo.write(TILT_CENTER);
    Serial.println("RESET");
}


// ── Affichage PID ─────────────────────────────────────────────────────────────
void printPID() {
    Serial.println(F("=== PID actuel ==="));
    Serial.print(F("PAN  : Kp=")); Serial.print(pidPan.kp,4);
    Serial.print(F("  Ki=")); Serial.print(pidPan.ki,4);
    Serial.print(F("  Kd=")); Serial.println(pidPan.kd,4);
    Serial.print(F("TILT : Kp=")); Serial.print(pidTilt.kp,4);
    Serial.print(F("  Ki=")); Serial.print(pidTilt.ki,4);
    Serial.print(F("  Kd=")); Serial.println(pidTilt.kd,4);
    Serial.print(F("DRIV : Kp=")); Serial.print(pidDrive.kp,4);
    Serial.print(F("  Ki=")); Serial.print(pidDrive.ki,4);
    Serial.print(F("  Kd=")); Serial.print(pidDrive.kd,4);
    Serial.print(F("  TurnKp=")); Serial.println(motorTurnKp,4);
    Serial.println(F("Cmds: pp pi pd  tp ti td  mp mi md mt  ?  R"));
}


// ── Parser tuning ────────────────────────────────────────────────────────────
bool parseTuning(const String &line) {
    if (line.length() < 3) return false;
    String cmd = line.substring(0, 2);
    cmd.toLowerCase();
    float val = line.substring(3).toFloat();

    if      (cmd == "pp") { pidPan.kp    = val; }
    else if (cmd == "pi") { pidPan.ki    = val; }
    else if (cmd == "pd") { pidPan.kd    = val; }
    else if (cmd == "tp") { pidTilt.kp   = val; }
    else if (cmd == "ti") { pidTilt.ki   = val; }
    else if (cmd == "td") { pidTilt.kd   = val; }
    else if (cmd == "mp") { pidDrive.kp  = val; }
    else if (cmd == "mi") { pidDrive.ki  = val; }
    else if (cmd == "md") { pidDrive.kd  = val; }
    else if (cmd == "mt") { motorTurnKp  = val; }
    else return false;

    Serial.print(F("[PID] ")); Serial.print(cmd);
    Serial.print(F(" = ")); Serial.println(val, 4);
    return true;
}


// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);

    tiltServo.attach(PIN_TILT, 600, 2400);
    tiltServo.write(TILT_CENTER);
    delay(300);
    tiltServo.detach();           // détache : pas d'effort contre le poids
    // pan non attaché au boot → détaché par défaut (pas de chauffe)

    AFMS.begin();
    motorFL = AFMS.getMotor(1);
    motorFR = AFMS.getMotor(2);
    motorBR = AFMS.getMotor(3);
    motorBL = AFMS.getMotor(4);
    stopMotors();

    pinMode(PIN_RC_PAN,   INPUT_PULLUP);
    pinMode(PIN_RC_TILT,  INPUT_PULLUP);
    pinMode(PIN_RC_THROT, INPUT_PULLUP);
    pinMode(PIN_RC_STEER, INPUT_PULLUP);
    pinMode(PIN_RC_MODE,  INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_RC_PAN),  isrPan,  CHANGE);  // D2
    attachInterrupt(digitalPinToInterrupt(PIN_RC_TILT), isrTilt, CHANGE);  // D3
    _prevD67 = PIND & 0xC0;
    PCICR  |= (1 << PCIE2);                          // PCINT port D
    PCMSK2 |= (1 << PCINT22) | (1 << PCINT23);       // D6 + D7
    _prevB0 = PINB & 0x01;
    PCICR  |= (1 << PCIE0);                           // PCINT port B
    PCMSK0 |= (1 << PCINT0);                          // D8
    delay(800);   // attend le récepteur
    lastCmdMs  = millis();   // après le délai → pas de faux timeout Python au boot
    lastCtrlMs = millis();
    noInterrupts();
    if (abs((int)_iThrot-1500)<300) _throt_neutral=_iThrot;
    if (abs((int)_iSteer-1500)<300) _steer_neutral=_iSteer;
    if (abs((int)_iTilt -1500)<300) _tilt_neutral =_iTilt;
    interrupts();
    Serial.print(F("[CAL] TH_n=")); Serial.print(_throt_neutral);
    Serial.print(F(" ST_n="));      Serial.print(_steer_neutral);
    Serial.print(F(" TL_n="));      Serial.println(_tilt_neutral);

    Serial.println(F("READY  –  '?' PID  |  SWD haut=RC  /  SWD bas=AUTO"));
}


// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    unsigned long now = millis();

    // ── Lecture RC PWM ───────────────────────────────────────────────────────
    // 100% interrupts – zéro blocage
    noInterrupts();
    rcPan = _iPan; rcTilt = _iTilt; rcThrot = _iThrot; rcSteer = _iSteer; rcMode5 = _iMode;
    interrupts();

    // ── DEBUG RC (toutes les secondes) ──────────────────────────────────
    static unsigned long dbgMs = 0;
    if (now - dbgMs >= 1000) {
        dbgMs = now;
        Serial.print(F("[RC] ST=")); Serial.print(rcSteer);
        Serial.print(F(" TH="));    Serial.print(rcThrot);
        Serial.print(F(" TL="));    Serial.print(rcTilt);
        Serial.print(F(" PN="));    Serial.print(rcPan);
        Serial.print(F(" MD="));    Serial.print(rcMode5);
        Serial.print(F(" mode="));  Serial.print(rcMode ? F("RC") : F("AUTO"));
        // debug moteurs + pan
        int _dt = (int)rcThrot-(int)_throt_neutral, _ds = (int)rcSteer-(int)_steer_neutral;
        Serial.print(F(" dT=")); Serial.print(_dt);
        Serial.print(F(" dS=")); Serial.print(_ds);
        Serial.print(F(" pnV=")); Serial.println((int)rcPan-1500);
    }
    // Hystérésis switch : RC si MD<1200 (~1000) | AUTO si MD>1400 (~1472) | sinon état précédent
    if      (rcMode5 < 1200) rcMode = true;
    else if (rcMode5 > 1400) rcMode = false;
    // entre 1200-1400 : on garde rcMode inchangé (pas d'oscillation)

    if (rcMode != prevRcMode) {
        prevRcMode = rcMode;
        if (rcMode) {
            pidPan.reset(); pidPan180.reset(); pidTilt.reset(); pidDrive.reset();
            stopMotors();
            Serial.println(F("[MODE] RC"));
        } else {
            stopMotors(); stopPan();
            pidPan.reset(); pidPan180.reset(); pidTilt.reset(); pidDrive.reset();
            Serial.println(F("[MODE] AUTO"));
        }
    }

    // ── Mode RC : commande directe radio (rate-limited 50Hz) ──────────────────
    if (rcMode) {
        lastCmdMs = now;

        static unsigned long rcCtrlMs = 0;
        if (now - rcCtrlMs < 20) goto skipRcCtrl;   // 50 Hz max
        rcCtrlMs = now;

        if (!tiltServo.attached()) tiltServo.attach(PIN_TILT, 600, 2400);
        tiltParked = false;

        // Throttle (CH3 stick droit ↑↓) + Steering (CH4 stick droit ←→)
        {
            int iThrot = (int)_throt_neutral - (int)rcThrot;   // UP=avancer, DOWN=reculer
            int iSteer = (int)_steer_neutral - (int)rcSteer;   // droite=tourner droite
            if (abs(iThrot) < RC_DEAD) iThrot = 0;
            if (abs(iSteer) < RC_DEAD) iSteer = 0;
            if (iThrot == 0 && iSteer == 0) {
                stopMotors();
            } else {
                int throt = (int)((long)iThrot * MOTOR_MAX_SPEED / 500);
                int steer = (int)((long)iSteer * MOTOR_MAX_SPEED / 400);  // /400 → plein régime rotation
                int lSpd = constrain(throt + steer, -255, 255);
                int rSpd = constrain(throt - steer, -255, 255);
                setMotorLeft(lSpd);
                setMotorRight(rSpd);
                // debug moteur (seulement quand actif)
                static unsigned long mDbg = 0;
                if (now - mDbg >= 500) {
                    mDbg = now;
                    Serial.print(F("[MOT] L=")); Serial.print(lSpd);
                    Serial.print(F(" R=")); Serial.println(rSpd);
                }
            }
        }

        // PAN tourelle (CH1 stick gauche ←→) – détach si neutre
        {
            int rcPanVal = (int)rcPan - 1500;
            if (abs(rcPanVal) < RC_DEAD) rcPanVal = 0;
            if (rcPanVal != 0) {
                if (!panServo.attached()) panServo.attach(PIN_PAN, 600, 2400);
#if PAN_STANDARD_180
                float panStep = rcPanVal * (float)PAN180_MAX_STEP / 500.0f;
                pan180Angle = constrain(pan180Angle + panStep, (float)PAN180_MIN, (float)PAN180_MAX);
                panServo.write((int)pan180Angle);
#else
                panServo.writeMicroseconds(PAN_STOP_US + (int)((long)rcPanVal * PAN_RANGE_US / 500));
#endif
                panParkMs = now;
            } else if (panServo.attached() && (now - panParkMs > 300)) {
                panServo.detach();   // coupe le PWM → plus de chauffe
            }
        }

        // TILT tourelle (CH2 stick gauche ↑↓) – rate control + détach si neutre
        {
            int iTilt = (int)_tilt_neutral - (int)rcTilt;
            if (abs(iTilt) < RC_DEAD) iTilt = 0;
            if (iTilt != 0) {
                if (!tiltServo.attached()) tiltServo.attach(PIN_TILT, 600, 2400);
                int step = (int)((long)iTilt * TILT_RC_STEP / 500);
                if (step == 0) step = (iTilt > 0) ? 1 : -1;  // au moins 1° si non nul
                currentTilt = constrain(currentTilt + step, TILT_MIN, TILT_MAX);
                tiltServo.write(currentTilt);
                tiltParkMs = now;
            } else if (tiltServo.attached() && (now - tiltParkMs > 300)) {
                tiltServo.detach();   // hors tension quand inutilisé
            }
        }
    }
    skipRcCtrl:

    // ── Watchdog (AUTO uniquement) ────────────────────────────────────────────
    if (!rcMode) {
        if (now - lastCmdMs > WATCHDOG_MS) {
            stopPan(); stopMotors();
            pidDrive.reset();
        }
        if (now - lastCmdMs > TILT_WATCHDOG_MS) {
            if (!tiltParked) {
                currentTilt = TILT_CENTER;
                tiltServo.write(TILT_CENTER);
                pidTilt.reset();
                tiltParkMs = now;
                tiltParked = true;
            } else if (tiltServo.attached() && (now - tiltParkMs > TILT_PARK_DELAY)) {
                tiltServo.detach();
            }
        }
    }

    // ── Série : tuning PID toujours actif, contrôle seulement en AUTO ─────────
    if (!Serial.available()) return;

    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    if (line == "?") { printPID(); return; }
    if (line.equalsIgnoreCase("R")) { resetAll(); lastCmdMs = now; return; }
    if (isAlpha(line[0])) { parseTuning(line); return; }   // tuning toujours actif

    if (rcMode) return;   // ignorer les commandes de contrôle en mode RC

    // ── Commande contrôle "<error_x> <error_y> [bbox_h]" (AUTO) ──────────────
    int sp1 = line.indexOf(' ');
    if (sp1 < 0) return;
    int sp2 = line.indexOf(' ', sp1 + 1);

    int errorX = line.substring(0, sp1).toInt();
    int errorY = line.substring(sp1 + 1, (sp2 > 0) ? sp2 : (int)line.length()).toInt();
    int bboxH  = (sp2 > 0) ? line.substring(sp2 + 1).toInt() : 0;

    float dt = (float)(now - lastCtrlMs) / 1000.0f;
    if (dt > 0.5f) dt = 0.5f;
    lastCtrlMs = now;

    if (!tiltServo.attached()) tiltServo.attach(PIN_TILT, 600, 2400);
    tiltParked = false;

#if PAN_STANDARD_180
    applyPan180(errorX, dt);
#else
    applyPanContinuous(errorX, dt);
#endif
    applyTilt(errorY, dt);
    applyDrive(errorX, bboxH, dt);

    lastCmdMs = now;
}
