/*
 * rc_test.ino – Wizard identification RC + test moteurs/servos
 *
 * Câblage récepteur :
 *   CH1 → D2  |  CH2 → D3  |  CH3 → D6  |  CH4 → D7  |  CH5 → D8
 *   GND → GND
 *
 * Serial Monitor 115200 baud.
 * Le sketch guide étape par étape : bouge tel stick, il détecte quel CH bouge.
 * Ensuite commandes manuelles : 1/2/3/4 = moteur, p = pan, t = tilt, s = stop
 */

#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include <Servo.h>

// ── RC : tous les channels sur interrupts ────────────────────────────────────
volatile uint16_t _ch1=1500, _ch2=1500, _ch3=1500, _ch4=1500;
volatile uint32_t _t1=0, _t2=0, _t3=0, _t4=0;
volatile uint8_t  _prevD67=0;

void isr1(){ if(digitalRead(2)) _t1=micros(); else{ uint16_t w=(uint16_t)(micros()-_t1); if(w>=800&&w<=2200) _ch1=w; }}
void isr2(){ if(digitalRead(3)) _t2=micros(); else{ uint16_t w=(uint16_t)(micros()-_t2); if(w>=800&&w<=2200) _ch2=w; }}
ISR(PCINT2_vect){
    uint8_t pd=PIND; uint32_t now=micros(); uint8_t chg=pd^_prevD67; _prevD67=pd;
    if(chg&0x40){ if(pd&0x40) _t3=now; else{ uint16_t w=(uint16_t)(now-_t3); if(w>=800&&w<=2200) _ch3=w; }}
    if(chg&0x80){ if(pd&0x80) _t4=now; else{ uint16_t w=(uint16_t)(now-_t4); if(w>=800&&w<=2200) _ch4=w; }}
}
uint16_t readCh5(){ uint16_t v=pulseIn(8,HIGH,25000); return(v<1000||v>2000)?1500:v; }

// ── Moteurs + servos ─────────────────────────────────────────────────────────
Adafruit_MotorShield AFMS = Adafruit_MotorShield();
Adafruit_DCMotor *mot[4];
Servo panServo, tiltServo;

void stopAll(){ for(int i=0;i<4;i++) mot[i]->run(RELEASE); }

// ── Snapshot channels ────────────────────────────────────────────────────────
uint16_t snap[5];
void takeSnap(){
    noInterrupts(); snap[0]=_ch1; snap[1]=_ch2; snap[2]=_ch3; snap[3]=_ch4; interrupts();
    snap[4]=readCh5();
}

uint16_t cur[5];
void readAll(){
    noInterrupts(); cur[0]=_ch1; cur[1]=_ch2; cur[2]=_ch3; cur[3]=_ch4; interrupts();
    cur[4]=readCh5();
}

// ── Mapping résultat ─────────────────────────────────────────────────────────
#define N_STEPS 9
const char* labels[] = {
    "Stick DROIT vers le HAUT",
    "Stick DROIT vers le BAS",
    "Stick DROIT vers la DROITE",
    "Stick DROIT vers la GAUCHE",
    "Stick GAUCHE vers le HAUT",
    "Stick GAUCHE vers le BAS",
    "Stick GAUCHE vers la DROITE",
    "Stick GAUCHE vers la GAUCHE",
    "Switch SWA (bascule)"
};
int  mapCh[N_STEPS];    // channel détecté (0-4 = CH1-CH5)
int  mapVal[N_STEPS];   // valeur PWM détectée
int  mapDelta[N_STEPS]; // delta vs neutre (+/-)

// ── Wizard ───────────────────────────────────────────────────────────
int detectChange(uint16_t* base, int* outDelta){
    unsigned long start = millis();
    unsigned long lm = 0;
    while(millis()-start < 15000){
        readAll();
        for(int i=0;i<5;i++){
            int d = (int)cur[i]-(int)base[i];
            if(abs(d) > 150){ *outDelta = d; return i; }
        }
        if(millis()-lm>500){
            lm=millis();
            Serial.print(F("  [live] "));
            for(int i=0;i<5;i++){
                Serial.print(F("CH")); Serial.print(i+1); Serial.print(F("="));
                Serial.print(cur[i]);
                int d=(int)cur[i]-(int)base[i];
                if(abs(d)>30){ Serial.print(F("(")); if(d>0) Serial.print(F("+")); Serial.print(d); Serial.print(F(")")); }
                Serial.print(F("  "));
            }
            Serial.println();
        }
    }
    return -1;
}

void runWizard(){
    Serial.println(F("\n===================================="));
    Serial.println(F("   WIZARD IDENTIFICATION RC"));
    Serial.println(F("===================================="));
    Serial.println(F("Laisse tous les sticks au NEUTRE (relaches)."));
    Serial.println(F("Stick droit gaz : mets-le AU MILIEU."));
    Serial.println(F("Appuie ENTRER quand pret..."));
    while(!Serial.available()) delay(10);
    while(Serial.available()) Serial.read();
    delay(500);

    takeSnap();
    Serial.print(F("\n[NEUTRE] "));
    for(int i=0;i<5;i++){
        Serial.print(F("CH")); Serial.print(i+1); Serial.print(F("=")); Serial.print(snap[i]); Serial.print(F("  "));
    }
    Serial.println(F("\n"));

    int pins[] = {2,3,6,7,8};

    for(int step=0; step<N_STEPS; step++){
        mapCh[step] = -1; mapVal[step] = 0; mapDelta[step] = 0;
        Serial.println(F("--------------------------------"));
        Serial.print(F(">> Pousse : ")); Serial.println(labels[step]);
        Serial.println(F("   (pousse a fond, 15s timeout)"));

        int delta = 0;
        int ch = detectChange(snap, &delta);

        if(ch >= 0){
            mapCh[step] = ch;
            mapVal[step] = cur[ch];
            mapDelta[step] = delta;
            Serial.print(F("   >>> CH")); Serial.print(ch+1);
            Serial.print(F(" (D")); Serial.print(pins[ch]); Serial.print(F(") = "));
            Serial.print(cur[ch]);
            Serial.print(F("  delta=")); if(delta>0) Serial.print(F("+"));
            Serial.print(delta);
            Serial.println(F("  OK !"));
        } else {
            Serial.println(F("   >>> TIMEOUT !"));
        }

        Serial.println(F("   Relache le stick..."));
        delay(1500);
        takeSnap();
    }

    // Résumé
    Serial.println(F("\n===================================="));
    Serial.println(F("   RESULTAT MAPPING COMPLET"));
    Serial.println(F("===================================="));
    for(int s=0;s<N_STEPS;s++){
        Serial.print(F("  ")); Serial.print(labels[s]); Serial.print(F(" -> "));
        if(mapCh[s]>=0){
            Serial.print(F("CH")); Serial.print(mapCh[s]+1);
            Serial.print(F(" D")); Serial.print(pins[mapCh[s]]);
            Serial.print(F(" val=")); Serial.print(mapVal[s]);
            Serial.print(F(" delta=")); if(mapDelta[s]>0) Serial.print(F("+"));
            Serial.println(mapDelta[s]);
        } else {
            Serial.println(F("NON DETECTE"));
        }
    }
    Serial.println(F("====================================\n"));
    Serial.println(F("Commandes manuelles :"));
    Serial.println(F("  1/2/3/4 = moteur M1/M2/M3/M4 (2s)"));
    Serial.println(F("  a = tous moteurs avant (2s)"));
    Serial.println(F("  p = test servo PAN (pin 9)"));
    Serial.println(F("  t = test servo TILT (pin 10)"));
    Serial.println(F("  m = affiche channels live"));
    Serial.println(F("  w = relancer le wizard"));
    Serial.println(F("  s = stop tout"));
}

// ── Setup ────────────────────────────────────────────────────────────────────
void setup(){
    Serial.begin(115200);

    // RC pins
    pinMode(2, INPUT_PULLUP);
    pinMode(3, INPUT_PULLUP);
    pinMode(6, INPUT_PULLUP);
    pinMode(7, INPUT_PULLUP);
    pinMode(8, INPUT);
    attachInterrupt(digitalPinToInterrupt(2), isr1, CHANGE);
    attachInterrupt(digitalPinToInterrupt(3), isr2, CHANGE);
    _prevD67 = PIND & 0xC0;
    PCICR  |= (1 << PCIE2);
    PCMSK2 |= (1 << PCINT22) | (1 << PCINT23);

    // Moteurs
    AFMS.begin();
    for(int i=0;i<4;i++){ mot[i]=AFMS.getMotor(i+1); mot[i]->run(RELEASE); }

    // Servos
    panServo.attach(9, 600, 2400);
    tiltServo.attach(10, 600, 2400);
    panServo.writeMicroseconds(1500);
    tiltServo.write(90);
    delay(300);
    tiltServo.detach();

    delay(800);  // attend le récepteur
    runWizard();
}

// ── Loop ─────────────────────────────────────────────────────────────────────
bool liveMode = false;
void loop(){
    // live display
    if(liveMode){
        static unsigned long lm=0;
        if(millis()-lm>500){
            lm=millis();
            readAll();
            Serial.print(F("[LIVE] "));
            for(int i=0;i<5;i++){
                Serial.print(F("CH")); Serial.print(i+1); Serial.print(F("="));
                Serial.print(cur[i]); Serial.print(F("  "));
            }
            Serial.println();
        }
    }

    if(!Serial.available()) return;
    char c = (char)Serial.read();
    if(c=='\n'||c=='\r') return;

    switch(c){
        case '1': case '2': case '3': case '4': {
            int idx = c - '1';
            Serial.print(F(">> Moteur M")); Serial.print(idx+1); Serial.println(F(" AVANT 2s"));
            mot[idx]->setSpeed(180);
            mot[idx]->run(FORWARD);
            delay(2000);
            mot[idx]->run(RELEASE);
            Serial.println(F(">> Stop"));
            break;
        }
        case 'a': case 'A':
            Serial.println(F(">> Tous moteurs AVANT 2s"));
            for(int i=0;i<4;i++){ mot[i]->setSpeed(180); mot[i]->run(FORWARD); }
            delay(2000);
            stopAll();
            Serial.println(F(">> Stop"));
            break;
        case 'p': case 'P':
            Serial.println(F(">> Test PAN (pin 9) : gauche-centre-droite"));
            panServo.writeMicroseconds(1200); delay(1000);
            panServo.writeMicroseconds(1500); delay(1000);
            panServo.writeMicroseconds(1800); delay(1000);
            panServo.writeMicroseconds(1500);
            Serial.println(F(">> PAN stop"));
            break;
        case 't': case 'T':
            Serial.println(F(">> Test TILT (pin 10) : bas-centre-haut"));
            if(!tiltServo.attached()) tiltServo.attach(10, 600, 2400);
            tiltServo.write(45);  delay(1000);
            tiltServo.write(90);  delay(1000);
            tiltServo.write(135); delay(1000);
            tiltServo.write(90);
            Serial.println(F(">> TILT centre"));
            break;
        case 'm': case 'M':
            liveMode = !liveMode;
            Serial.print(F(">> Live mode ")); Serial.println(liveMode ? F("ON") : F("OFF"));
            break;
        case 'w': case 'W':
            liveMode = false;
            runWizard();
            break;
        case 's': case 'S':
            stopAll();
            panServo.writeMicroseconds(1500);
            Serial.println(F(">> STOP tout"));
            break;
        default: break;
    }
}
