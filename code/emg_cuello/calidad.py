"""Revisiones de calidad de un registro, escritas antes de ver cualquier score.

Las tres revisiones del curso (diapositiva 15) mas los huecos (PDF, parte 5):
  1. Nivel cero: el promedio en reposo es el offset del sensor (solo se reporta).
  2. Saturacion: ninguna muestra en 0 ni en 2^bits - 1 (16383 con 14 bits).
  3. Longitud: N dentro de +-2 % de (duracion planeada x Fs).
  4. Huecos: muestras que faltan segun el contador del Arduino, maximo 1 %.
  5. Fs medida con micros() dentro de +-2 % de 1000 Hz.
  6. La persona que opera puede rechazar un intento (movio a destiempo,
     se despego un electrodo); se anota al grabar.
"""
import numpy as np


def contar_huecos(n):
    """Muestras que faltan segun el contador n (que deberia ir 0, 1, 2, ...)."""
    n = np.asarray(n, dtype=np.int64)
    if len(n) == 0:
        return 0
    esperadas = int(n.max()) + 1
    return esperadas - len(np.unique(n))


def fs_medida(marcas):
    """Fs real a partir de las lineas '#T,n,micros'. marcas = [(n, micros), ...]."""
    if len(marcas) < 2:
        return float("nan")
    n0, t0 = marcas[0]
    n1, t1 = marcas[-1]
    dt_us = (t1 - t0) % (2 ** 32)          # micros() da la vuelta cada ~71 min
    return (n1 - n0) / (dt_us / 1e6) if dt_us > 0 else float("nan")


def revisar(n, adc, n_plan, adc_bits, fs_real=float("nan"), fs=1000):
    """Calcula los numeros de calidad de un registro. No decide nada."""
    adc = np.asarray(adc, dtype=np.int64)
    tope = 2 ** adc_bits - 1
    return {
        "n_samples": int(len(adc)),
        "n_plan": int(n_plan),
        "length_off_pct": 100.0 * abs(len(adc) - n_plan) / n_plan,
        "missing": int(contar_huecos(n)),
        "missing_pct": 100.0 * contar_huecos(n) / n_plan,
        "clipped_samples": int(np.sum((adc <= 0) | (adc >= tope))),
        "fs_measured_hz": float(fs_real),
        "fs_off_pct": 100.0 * abs(fs_real - fs) / fs if np.isfinite(fs_real) else float("nan"),
    }


def decidir(rev, reglas, operador_ok=True, nota_operador=""):
    """Aplica las reglas. Regresa (rechazado: bool, razones: list[str])."""
    razones = []
    if rev["clipped_samples"] > 0:
        razones.append(f"{rev['clipped_samples']} samples at the limit of the converter")
    if rev["missing_pct"] > reglas["max_missing_pct"]:
        razones.append(f"{rev['missing_pct']:.1f} % of the samples missing")
    if rev["length_off_pct"] > reglas["length_tolerance_pct"]:
        razones.append(f"length off by {rev['length_off_pct']:.1f} % "
                       f"({rev['n_samples']} of {rev['n_plan']} samples)")
    if np.isfinite(rev["fs_off_pct"]) and rev["fs_off_pct"] > reglas["fs_tolerance_pct"]:
        razones.append(f"measured Fs {rev['fs_measured_hz']:.1f} Hz")
    if not operador_ok:
        razones.append("operator: " + (nota_operador or "rejected while recording"))
    return (len(razones) > 0, razones)
