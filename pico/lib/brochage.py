# brochage.py – broches, adresses et réglages du Pico 2 de LEO-S (schéma électrique rév. J).
# Seul fichier à modifier quand un branchement ou une calibration change.
from machine import Pin, I2C, SoftI2C, UART

# ── Broches ───────────────────────────────────────────────────────────────────
# Un bus I²C par élément, chacun sur ses broches : (contrôleur, SDA, SCL). "soft" = bus logiciel.
BUS_I2C = {"imu": (0, 4, 5),                           # MPU6050 (et plus tard les ToF bas)
           "G": (1, 14, 15),                           # ADS1015 du pied gauche
           "D": ("soft", 16, 17)}                      # ADS1015 du pied droit
I2C_FREQ = 400000
UART_SERVOS, SERVO_TX, SERVO_RX = 1, 20, 21            # adaptateur bus servo, cavalier sur A
SERVO_BAUD = 1000000
UART_RADIO, RADIO_TX, RADIO_RX = 0, 0, 1               # FS-iA6B en iBUS (GP0 non branché)
ADC_BATTERIE = 26                                      # pont 100 k / 33 k de la 3S
DSHOT = (6, 7, 8, 9)                                   # ESC 4-en-1 (vague 4)
TOF_LPN = (10, 11)                                     # ToF bas (vague 3)

# ── Adresses I²C ──────────────────────────────────────────────────────────────
MPU = 0x68
PIEDS = {"G": 0x48, "D": 0x48}                         # ADS1015 : ADDR à GND sur les deux (bus séparés)
NOMS_I2C = {0x68: "MPU6050", 0x69: "MPU6050 (AD0 au 3V3 ?)", 0x48: "ADS1015",
            0x49: "ADS1015 (ADDR au 3V3)", 0x4A: "ADS1015 (ADDR sur SDA ?)", 0x4B: "ADS1015 (ADDR sur SCL ?)",
            0x29: "ToF (adresse d'usine)", 0x30: "ToF bas 1", 0x31: "ToF bas 2"}

# ── Capteurs de pied ──────────────────────────────────────────────────────────
FSR = {0: "talon", 1: "pointe int.", 2: "pointe ext."}  # entrées A0, A1, A2 de chaque ADS1015
R_FSR = 1000                                           # résistance du pont (Ω), à confirmer à l'étape 4
V_FSR = 3.3                                            # tension en haut des FSR (3V3 du Pico)

# ── Batterie ──────────────────────────────────────────────────────────────────
PONT_BATTERIE = (100000, 33000)                        # (haut, bas) en Ω
CAL_BATTERIE = 1.0                                     # correction après comparaison au multimètre (étape 6)
V_BASSE, V_CRITIQUE = 10.8, 10.2                       # 3S : 3,6 V et 3,4 V par élément

# ── Servos ────────────────────────────────────────────────────────────────────
IDS = (1, 2, 3, 4, 5, 6, 7, 8)
ARTICULATIONS = {1: "D S1 roulis", 2: "D S2 hanche", 3: "D S3 genou", 4: "D S4 cheville",
                 5: "G S1 roulis", 6: "G S2 hanche", 7: "G S3 genou", 8: "G S4 cheville"}

# ── Centrale inertielle ───────────────────────────────────────────────────────
GYRO_BIAIS = (0.0, 0.0, 0.0)                           # °/s, valeurs données par l'étape 2

# ── Radio ─────────────────────────────────────────────────────────────────────
VOIE_ARRET = 5                                         # CH5 = arrêt d'urgence
ARRET_SI_HAUT = True                                   # interrupteur vers le haut (> 1500) = ARRÊT
PERTE_RADIO_MS = 100                                   # plus de trame depuis 100 ms = ARRÊT


def bus_i2c(nom):
    ctrl, sda, scl = BUS_I2C[nom]
    if ctrl == "soft":
        return SoftI2C(sda=Pin(sda), scl=Pin(scl), freq=I2C_FREQ)
    return I2C(ctrl, sda=Pin(sda), scl=Pin(scl), freq=I2C_FREQ)


def i2c():
    return bus_i2c("imu")


def uart_servos():
    return UART(UART_SERVOS, baudrate=SERVO_BAUD, tx=Pin(SERVO_TX), rx=Pin(SERVO_RX), rxbuf=512, timeout=0)


def uart_radio():
    return UART(UART_RADIO, baudrate=115200, tx=Pin(RADIO_TX), rx=Pin(RADIO_RX), rxbuf=256, timeout=0)
