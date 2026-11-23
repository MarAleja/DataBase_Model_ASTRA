"""Filtro SinArm: la misma cadena del sketch del Arduino, aplicada en Python.

Orden, igual que en diagnostico_emg_enlace.ino:
  1. Cuentas del ADC a voltios: v = adc * 5.0 / 16383
  2. Quitar DC: promedio exponencial dc += 0.003 * (v - dc), y x = v - dc
     (paso alto de primer orden, corte cerca de 0.48 Hz a 1000 Hz)
  3. Siete notch en cascada en 60, 120, 180, 240, 300, 360 y 420 Hz, Q = 20.
     Cada uno es un biquad de 2.o orden con las formulas del "Audio EQ Cookbook"
     de R. Bristow-Johnson, en forma directa II transpuesta (scipy.lfilter usa
     la misma forma).

Unica diferencia con el Arduino: el Arduino empieza con dc = 2.5 V y lleva
horas corriendo, asi que su dc ya esta asentado. Aqui cada archivo empieza de
cero, por eso dc arranca en el promedio de las primeras 200 muestras. Con
dc0=2.5 se obtiene exactamente el arranque del Arduino.
"""
import numpy as np
from scipy.signal import freqz, lfilter


def adc_a_voltios(adc, vref=5.0, bits=14):
    """Cuentas del ADC a voltios a la salida del sensor."""
    return np.asarray(adc, dtype=float) * vref / (2 ** bits - 1)


def coef_notch(f0, q, fs):
    """Coeficientes (b, a) de un notch biquad, igual que Notch::init del Arduino."""
    w0 = 2.0 * np.pi * f0 / fs
    c, al = np.cos(w0), np.sin(w0) / (2.0 * q)
    a0 = 1.0 + al
    b = np.array([1.0, -2.0 * c, 1.0]) / a0
    a = np.array([1.0, -2.0 * c / a0, (1.0 - al) / a0])
    return b, a


def quitar_dc(v, alpha, dc0):
    """dc[n] = dc[n-1] + alpha * (v[n] - dc[n-1]); regresa v - dc."""
    v = np.asarray(v, dtype=float)
    dc, _ = lfilter([alpha], [1.0, -(1.0 - alpha)], v, zi=[(1.0 - alpha) * dc0])
    return v - dc


def sinarm(v, fs=1000, alpha_dc=0.003, mains_hz=60, harmonics=7, q=20,
           dc0=None, dc_init_samples=200):
    """Senal en voltios -> senal SinArm en voltios (sin DC, sin 60 Hz ni armonicos)."""
    v = np.asarray(v, dtype=float)
    if dc0 is None:
        dc0 = float(np.mean(v[:dc_init_samples]))
    y = quitar_dc(v, alpha_dc, dc0)
    for k in range(1, harmonics + 1):
        b, a = coef_notch(mains_hz * k, q, fs)
        y = lfilter(b, a, y)
    return y


def sinarm_desde_config(v, cfg):
    """sinarm() con los parametros de config['sinarm']."""
    p = cfg["sinarm"]
    return sinarm(v, fs=cfg["fs_hz"], alpha_dc=p["alpha_dc"], mains_hz=p["mains_hz"],
                  harmonics=p["harmonics"], q=p["q"], dc_init_samples=p["dc_init_samples"])


def sinarm_como_arduino(v, fs=1000.0, alpha_dc=0.003, mains_hz=60.0, harmonics=7,
                        q=20.0, dc0=2.5):
    """Copia linea por linea del loop del Arduino, en float32. Solo para pruebas."""
    f32 = np.float32
    notches = []
    for k in range(1, harmonics + 1):
        w0 = f32(2.0) * f32(np.pi) * f32(mains_hz * k) / f32(fs)
        c, al = f32(np.cos(w0)), f32(np.sin(w0)) / (f32(2.0) * f32(q))
        a0 = f32(1.0) + al
        notches.append([f32(1.0) / a0, f32(-2.0) * c / a0, f32(1.0) / a0,
                        f32(-2.0) * c / a0, (f32(1.0) - al) / a0, f32(0), f32(0)])
    dc, alpha = f32(dc0), f32(alpha_dc)
    salida = np.empty(len(v), dtype=np.float32)
    for i, vi in enumerate(np.asarray(v, dtype=np.float32)):
        dc = dc + alpha * (vi - dc)
        y = vi - dc
        for nt in notches:
            b0, b1, b2, a1, a2, z1, z2 = nt
            x = y
            y = b0 * x + z1
            nt[5] = b1 * x - a1 * y + z2
            nt[6] = b2 * x - a2 * y
        salida[i] = y
    return salida


def corte_paso_alto_hz(alpha=0.003, fs=1000.0):
    """Frecuencia de -3 dB del paso alto que forma quitar_dc (para PROTOCOL.md)."""
    b = np.array([1.0 - alpha, -(1.0 - alpha)])
    a = np.array([1.0, -(1.0 - alpha)])
    f, h = freqz(b, a, worN=200000, fs=fs)
    mag = np.abs(h)
    return float(f[np.argmax(mag >= 1 / np.sqrt(2))])
