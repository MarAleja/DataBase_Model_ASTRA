/*
  Diagnóstico de ruido EMG (Arduino UNO R4 WiFi) - lee A0 (JP3 puenteado)
  -----------------------------------------------------------------------
  Imprime 3 RMS (en voltios, a la salida EMG_Out) 10 veces por segundo:
    Bruto   : señal sin DC, sin filtrar

    Sin60   : quitando solo 60 Hz
    SinArm  : quitando 60, 120, 180, 240, 300, 360 y 420 Hz (armónicos de la red)

  Cómo leerlo (en reposo):
    Bruto mucho mayor que Sin60   -> hay mucho 60 Hz
    Sin60 mucho mayor que SinArm  -> los armónicos de la red dominan
    SinArm sigue alto (> ~0.05 V) -> ruido de banda ancha: electrodos, cables o la placa
  Al contraer el bíceps, SinArm debe subir claramente.

  NUEVO - Enlace al ESP32:
    Cada 100 ms manda por Serial1 (pin D1 -> optoacoplador) el RMS SinArm en
    milivoltios, como texto corto ("12\n"). Serial (USB) sigue igual que antes.
*/
#include <Arduino.h>
#include <math.h>

const int PIN_EMG = A1;
const float FS = 1000.0f;                    // Hz
const uint32_t TS_US = 1000;                 // 1/FS en microsegundos
const float V_REF = 5.0f, ADC_MAX = 16383.0f;

// ---- Notch biquad (forma directa II transpuesta) ----
struct Notch {
  float b0, b1, b2, a1, a2, z1 = 0, z2 = 0;
  void init(float f, float Q) {
    float w0 = 2.0f * PI * f / FS, c = cosf(w0), al = sinf(w0) / (2.0f * Q), a0 = 1.0f + al;
    b0 = 1.0f / a0; b1 = -2.0f * c / a0; b2 = 1.0f / a0; a1 = -2.0f * c / a0; a2 = (1.0f - al) / a0;
  }
  float run(float x) { float y = b0 * x + z1; z1 = b1 * x - a1 * y + z2; z2 = b2 * x - a2 * y; return y; }
};

const int N_ARM = 7;
Notch n60, arm[N_ARM];

float dc = 2.5f;
const float ALPHA_DC = 0.003f;               // quita DC (~0.5 Hz)

// RMS en bloques de 100 ms
const int N_BLOQUE = 100;
double s_bruto = 0, s_60 = 0, s_arm = 0;
int cuenta = 0;

void setup() {
  Serial.begin(250000);
  Serial1.begin(9600);                       // NUEVO: enlace al ESP32 por el opto (pin D1)
  analogReadResolution(14);
  n60.init(60.0f, 20.0f);
  for (int k = 0; k < N_ARM; k++) arm[k].init(60.0f * (k + 1), 20.0f);
}

void loop() {
  static uint32_t t_next = micros();
  while ((int32_t)(micros() - t_next) < 0);
  t_next += TS_US;

  float v = analogRead(PIN_EMG) * V_REF / ADC_MAX;
  dc += ALPHA_DC * (v - dc);
  float x = v - dc;

  float y60 = n60.run(x);
  float ya = x;
  for (int k = 0; k < N_ARM; k++) ya = arm[k].run(ya);

  s_bruto += (double)x * x;
  s_60 += (double)y60 * y60;
  s_arm += (double)ya * ya;

  if (++cuenta >= N_BLOQUE) {
    float rmsBruto = sqrt(s_bruto / N_BLOQUE);
    float rms60    = sqrt(s_60 / N_BLOQUE);
    float rmsArm   = sqrt(s_arm / N_BLOQUE);

    Serial.print("Bruto:");   Serial.print(rmsBruto, 3);
    Serial.print(",Sin60:");  Serial.print(rms60, 3);
    Serial.print(",SinArm:"); Serial.println(rmsArm, 3);

    // NUEVO: al ESP32 solo va SinArm en milivoltios. Mensaje corto para que,
    // a 9600 baudios, enviarlo no le robe tiempo al muestreo de 1 kHz.
    Serial1.println((int)(rmsArm * 1000.0f));

    s_bruto = s_60 = s_arm = 0;
    cuenta = 0;
  }
}
