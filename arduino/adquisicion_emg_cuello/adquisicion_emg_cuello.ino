/*
  adquisicion_emg_cuello.ino  (Arduino UNO R4 WiFi)  -  version adq-v1
  ------------------------------------------------------------------
  Graba el EMG CRUDO a 1000 Hz para la base de datos del esplenio de la cabeza.
  Se basa en diagnostico_emg_enlace.ino del equipo: mismo pin, mismo muestreo,
  mismo ADC de 14 bits y el mismo filtro SinArm para el ESP32.
  Escrito por el equipo con ayuda de Claude (IA). Lo explica cualquier miembro.

  Que hace
    1. Lee A1 cada 1000 us (1000 Hz), igual que el sketch de diagnostico.
    2. Por USB (Serial, 250000 baudios):
       - En espera: imprime "Bruto:..,Sin60:..,SinArm:.." 10 veces por segundo,
         igual que antes, para revisar los electrodos en el Serial Plotter.
       - Al recibir 's': reinicia el contador y manda CADA muestra cruda como
         "n,adc" (n = numero de muestra desde 0, adc = cuenta de 0 a 16383).
         Cada 1000 muestras manda "#T,n,micros,atrasos" para medir la Fs real.
       - Al recibir 'x': deja de mandar y responde "#FIN,<muestras enviadas>".
       - Al recibir '?': responde "#LISTO,..." con la configuracion.
    3. Por Serial1 (pin D1 -> optoacoplador -> ESP32): igual que antes,
       cada 100 ms el RMS SinArm en milivoltios ("12\n").

  El dato que se guarda NO va filtrado (data/raw debe quedar intacto).
  El filtro SinArm se aplica despues en Python con las mismas formulas.

  Ojo: el comentario del sketch original dice "lee A0", pero su codigo usa A1.
  Aqui se usa A1, como en su codigo. Si su cable esta en A0, cambien PIN_EMG.
*/
#include <Arduino.h>
#include <math.h>

const char *VERSION = "adq-v1";
const int PIN_EMG = A0;
const float FS = 1000.0f;                    // Hz
const uint32_t TS_US = 1000;                 // 1/FS en microsegundos
const float V_REF = 5.0f, ADC_MAX = 16383.0f;
const int ADC_BITS = 14;

// ---- Notch biquad (forma directa II transpuesta), igual al original ----
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

// RMS en bloques de 100 ms (para el Serial Plotter en espera y para el ESP32)
const int N_BLOQUE = 100;
double s_bruto = 0, s_60 = 0, s_arm = 0;
int cuenta = 0;

// Estado de la transmision cruda
bool transmitiendo = false;
uint32_t n = 0;                              // muestras enviadas desde 's'
uint32_t atrasos = 0;                        // muestras tomadas mas de 500 us tarde

void responderListo() {
  Serial.print("#LISTO,version="); Serial.print(VERSION);
  Serial.print(",fs="); Serial.print((int)FS);
  Serial.print(",bits="); Serial.print(ADC_BITS);
  Serial.print(",vref="); Serial.print(V_REF, 1);
  Serial.println(",pin=A1");
}

void leerComandos() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == 's') {                          // empezar a mandar crudo
      n = 0; atrasos = 0; transmitiendo = true;
      Serial.println("#INICIO");
    } else if (c == 'x') {                   // parar
      transmitiendo = false;
      Serial.print("#FIN,"); Serial.println(n);
    } else if (c == '?') {
      responderListo();
    }
  }
}

void setup() {
  Serial.begin(250000);
  Serial1.begin(9600);                       // enlace al ESP32 por el opto (pin D1)
  analogReadResolution(14);
  n60.init(60.0f, 20.0f);
  for (int k = 0; k < N_ARM; k++) arm[k].init(60.0f * (k + 1), 20.0f);
}

void loop() {
  static uint32_t t_next = micros();
  while ((int32_t)(micros() - t_next) < 0);
  uint32_t t_muestra = micros();
  if ((int32_t)(t_muestra - t_next) > 500) atrasos++;
  t_next += TS_US;

  int adc = analogRead(PIN_EMG);

  if (transmitiendo) {
    Serial.print(n); Serial.print(','); Serial.println(adc);
    if (n % 1000 == 0) {
      Serial.print("#T,"); Serial.print(n); Serial.print(',');
      Serial.print(t_muestra); Serial.print(','); Serial.println(atrasos);
    }
    n++;
  }

  // ---- Filtro SinArm, igual que el sketch de diagnostico ----
  float v = adc * V_REF / ADC_MAX;
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

    if (!transmitiendo) {                    // en espera: igual que el diagnostico
      Serial.print("Bruto:");   Serial.print(rmsBruto, 3);
      Serial.print(",Sin60:");  Serial.print(rms60, 3);
      Serial.print(",SinArm:"); Serial.println(rmsArm, 3);
    }
    Serial1.println((int)(rmsArm * 1000.0f)); // al ESP32, como antes

    s_bruto = s_60 = s_arm = 0;
    cuenta = 0;
  }

  leerComandos();
}
