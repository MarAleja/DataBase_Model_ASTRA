"""Nombres de archivo, lectura y escritura de registros y de data/metadata.csv."""
import csv
from pathlib import Path

import numpy as np
import pandas as pd

from .config import RAIZ

# Una fila de metadata.csv = una grabacion. Las 14 columnas que pide el PDF estan
# todas: session, date, rest_s, warning_s, move_s, between_s, electrode_type,
# electrode_distance_cm, skin_preparation, sensor_model, gain, fs_hz, adc_bits, set.
COLUMNAS_METADATA = [
    "file_name", "participant", "session", "date", "time_start", "recording", "trials",
    "task", "muscle", "side", "posture",
    "rest_s", "warning_s", "move_s", "between_s",
    "fs_hz", "adc_bits", "vref_v", "gain", "sensor_model", "sensor_analog_filter",
    "electrode_type", "electrode_distance_cm", "ground_site", "skin_preparation",
    "electrodes", "cue", "firmware", "set",
    "n_samples", "fs_measured_hz", "missing_pct", "late_samples", "clipped_samples",
    "operator_ok", "operator_note", "trials_rejected", "notes",
]

COLUMNAS_REGISTRO = ["sample", "time_ms", "emg_adc", "phase"]

RUTA_METADATA = RAIZ / "data" / "metadata.csv"


def nombre_archivo(participante, sesion, grabacion):
    """P01, S03, 7 -> 'P01_S03_R07.csv'"""
    return f"{participante}_{sesion}_R{int(grabacion):02d}.csv"


def leer_metadata(ruta=RUTA_METADATA):
    """Lee metadata.csv; si no existe regresa una tabla vacia con las columnas."""
    ruta = Path(ruta)
    if not ruta.exists() or ruta.stat().st_size == 0:
        return pd.DataFrame(columns=COLUMNAS_METADATA)
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


def escribir_metadata(df, ruta=RUTA_METADATA):
    """Escribe la tabla completa con las columnas en el orden oficial."""
    df = df.copy()
    for c in COLUMNAS_METADATA:
        if c not in df.columns:
            df[c] = ""
    df[COLUMNAS_METADATA].to_csv(ruta, index=False, quoting=csv.QUOTE_MINIMAL)


def agregar_fila_metadata(fila, ruta=RUTA_METADATA):
    """Agrega una fila (dict) al final de metadata.csv sin tocar las demas."""
    ruta = Path(ruta)
    nuevo = not ruta.exists() or ruta.stat().st_size == 0
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_METADATA, extrasaction="ignore")
        if nuevo:
            w.writeheader()
        w.writerow({c: fila.get(c, "") for c in COLUMNAS_METADATA})


def escribir_registro(ruta, n, adc, fases, fs):
    """Guarda un registro crudo: sample, time_ms, emg_adc, phase.

    time_ms = sample * 1000 / fs (el reloj es el contador del Arduino;
    la Fs real medida con micros() va en metadata, columna fs_measured_hz).
    """
    n = np.asarray(n, dtype=np.int64)
    df = pd.DataFrame({
        "sample": n,
        "time_ms": n * 1000.0 / fs,
        "emg_adc": np.asarray(adc, dtype=np.int64),
        "phase": list(fases),
    })
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)


def leer_registro(ruta):
    """Lee un registro crudo como DataFrame."""
    return pd.read_csv(ruta, dtype={"sample": np.int64, "emg_adc": np.int64, "phase": str})


def ruta_de_fila(cfg, fila):
    """Donde vive el archivo de una fila de metadata (train en el repo, test fuera)."""
    carpeta = cfg["folders"]["test"] if fila["set"] == "test" else cfg["folders"]["train"]
    return RAIZ / carpeta / fila["file_name"]
